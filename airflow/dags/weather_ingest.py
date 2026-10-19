"""DAG weather_ingest: clima horário do Open-Meteo na Bronze (Fase 2, etapa 9; decisões W1 a W4).

Disparada pelo Asset bronze_tlc (Aula 5): quando a TLC ganha versão nova, o clima acompanha.
Para cada mês com versão VIGENTE da TLC, pede o clima à API e compara o SHA-256 do JSON canônico
com o da última versão (W1, W2). Igual: nada a fazer. Diferente: versão nova na Bronze.

    planejar_clima ──> ingerir_clima_mes (um por mês, até 4 ao mesmo tempo) ──> publicar_clima (Asset)
                                                                           └──> tudo_certo
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from airflow.exceptions import AirflowFailException, AirflowSkipException
from airflow.sdk import Param, dag, task

from include.ingestao.ambientes import AMBIENTES, clientes_aws
from include.ingestao.assets import BRONZE_CLIMA, BRONZE_TLC
from include.ingestao.bronze import BUCKET_LAKE, chave_bronze, gravar_sem_sobrescrever, novo_ingest_ts
from include.ingestao.contrato import carregar_contrato, validar_clima
from include.ingestao.decisao import LinhaManifesto, classificar_download, ultima_versao
from include.ingestao.fonte_open_meteo import URL_API, baixar_clima, janela_do_mes, url_do_mes
from include.ingestao.manifesto import RegistroManifesto, ler_historico, registrar

log = logging.getLogger(__name__)

FONTE = "open_meteo"
FONTE_TLC = "tlc_hvfhv"

# O arquivo histórico do Open-Meteo (ERA5) chega com ~5 dias de atraso (documentação da API)
ATRASO_DO_ARQUIVO = timedelta(days=5)


@dag(
    dag_id="weather_ingest",
    schedule=[BRONZE_TLC],  # roda quando a tlc_ingest publica versão nova aceita
    start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=2),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=30),
    },
    params={
        "ambiente": Param("prod", enum=list(AMBIENTES), description="prod ou teste"),
        "base_url": Param(URL_API, type="string", description="Endereço da API histórica do Open-Meteo"),
    },
    tags=["ingestao", "bronze", "fase-2"],
    doc_md=__doc__,
)
def weather_ingest():

    @task
    def planejar_clima(**contexto) -> list[dict]:
        """Meses com TLC vigente -> lista de meses a conferir. Nada é baixado aqui."""
        ambiente = AMBIENTES[contexto["params"]["ambiente"]]
        _, athena = clientes_aws()

        historico_tlc = ler_historico(athena, ambiente["banco_controle"], FONTE_TLC)
        historico_clima = ler_historico(athena, ambiente["banco_controle"], FONTE)
        meses_tlc = sorted(m for m, linhas in historico_tlc.items() if any(l.status == "aceito" for l in linhas))

        limite = date.today() - ATRASO_DO_ARQUIVO
        trabalho, aguardando = [], []
        for mes in meses_tlc:
            fim_da_janela = date.fromisoformat(janela_do_mes(mes)[1])
            if fim_da_janela > limite:
                aguardando.append(mes)  # o arquivo histórico ainda não cobre o dia 1 seguinte (W3)
                continue
            trabalho.append({
                "mes": mes,
                "ingest_ts": novo_ingest_ts(),  # decidido uma vez, antes do download (D3, peça 1)
                "historico": [[l.ingest_ts, l.etag, l.file_sha256, l.status]
                              for l in historico_clima.get(mes, [])],
            })

        log.info("Meses com TLC vigente: %d | a conferir: %d | aguardando o arquivo histórico: %s",
                 len(meses_tlc), len(trabalho), ", ".join(aguardando) or "nenhum")
        return trabalho

    @task(max_active_tis_per_dag=4, map_index_template="{{ task.op_kwargs['item']['mes'] }}")
    def ingerir_clima_mes(item: dict, **contexto) -> dict:
        """Pede o mês, compara com a última versão e, se mudou, grava na Bronze e no manifesto."""
        params = contexto["params"]
        ambiente = AMBIENTES[params["ambiente"]]
        s3, athena = clientes_aws()
        mes = item["mes"]
        historico = [LinhaManifesto(*linha) for linha in item["historico"]]

        clima = baixar_clima(mes, params["base_url"])
        try:
            if classificar_download(clima.sha256, historico) == "mesmo_conteudo":
                if ultima_versao(historico).status == "rejeitado":
                    # O mesmo conteúdo que o contrato rejeitou: só uma pessoa destrava (cenário 8)
                    raise AirflowFailException(f"{mes}: o clima continua fora do contrato")
                log.info("%s: sem mudança (mesmo SHA-256 da versão vigente)", mes)
                return {"mes": mes, "status": "sem_mudanca"}

            contrato = validar_clima(clima.dados, carregar_contrato(FONTE), mes)
            for alerta in contrato.alertas:
                log.warning("%s: %s", mes, alerta)

            chave = chave_bronze(ambiente["prefixo_bronze"], FONTE, mes, item["ingest_ts"], f"{FONTE}_{mes}.json")
            gravacao = gravar_sem_sobrescrever(s3, chave, clima.caminho, clima.sha256)
            log.info("%s: arquivo %s (versão %s)", mes, gravacao, item["ingest_ts"])

            # O manifesto é o último passo (D3, peça 4)
            registrar(athena, ambiente["banco_controle"], RegistroManifesto(
                source=FONTE,
                source_month=mes,
                source_url=url_do_mes(mes, params["base_url"]),
                etag=None,  # a API não tem ETag (W1)
                last_modified=None,
                content_length=clima.tamanho,
                file_sha256=clima.sha256,
                row_count=len(clima.dados.get("hourly", {}).get("time", [])),  # horas no arquivo
                schema_hash=contrato.schema_hash,
                s3_path=f"s3://{BUCKET_LAKE}/{chave}",
                ingest_ts=item["ingest_ts"],
                status=contrato.status,
                motivo=contrato.motivo,
                registrado_em=datetime.now(timezone.utc),
                dag_run_id=contexto["run_id"],
            ))
            log.info("%s: manifesto registrado como %s", mes, contrato.status)
        finally:
            clima.caminho.unlink(missing_ok=True)

        if contrato.status == "rejeitado":
            raise AirflowFailException(f"{mes} em QUARENTENA, fora do contrato: {contrato.motivo}")
        return {"mes": mes, "status": contrato.status}

    @task(outlets=[BRONZE_CLIMA], trigger_rule="all_done")
    def publicar_clima(resultados, **contexto):
        """Publica o Asset do clima se algum mês ganhou versão aceita (só em produção)."""
        aceitos = [r["mes"] for r in resultados if r and r["status"] == "aceito"]
        if contexto["params"]["ambiente"] != "prod":
            raise AirflowSkipException("Ambiente de teste: não dispara as DAGs de produção")
        if not aceitos:
            raise AirflowSkipException("Nenhuma versão nova aceita: nada a publicar")
        log.info("Clima atualizado: %s", ", ".join(aceitos))

    @task
    def tudo_certo():
        """Só roda se todos os meses deram certo (mesma ideia da tlc_ingest)."""
        log.info("Todos os meses do clima terminaram bem.")

    resultados = ingerir_clima_mes.expand(item=planejar_clima())
    publicar_clima(resultados)
    resultados >> tudo_certo()


weather_ingest()
