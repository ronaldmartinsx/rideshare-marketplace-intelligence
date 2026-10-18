"""DAG tlc_ingest: Bronze da TLC guiada pelo manifesto (Fase 2, etapa 7; decisões D1 a D3).

Todo dia: lista os meses do recorte, pergunta à TLC (HEAD) e ao manifesto o que mudou, e só
baixa o que precisa. O histórico (backfill) e o dia a dia passam pelo mesmo código (D1).

    planejar ──> ingerir_mes (uma task por mês com ação, até 3 ao mesmo tempo) ──> publicar (Asset)
                                                                              └──> tudo_certo

Um mês com problema (erro no plano ou arquivo em quarentena) fica VERMELHO na grade, com o
próprio nome, sem retry. A task tudo_certo então não roda, e o run inteiro termina como falho:
alguém fica sabendo. Os outros meses seguem normalmente.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from airflow.exceptions import AirflowFailException, AirflowSkipException
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook
from airflow.sdk import Asset, Param, dag, task

from include.ingestao.bronze import BUCKET_LAKE, chave_bronze, gravar_sem_sobrescrever, novo_ingest_ts
from include.ingestao.contrato import carregar_contrato, contar_linhas, ler_colunas, validar
from include.ingestao.decisao import LinhaManifesto, RespostaHead, classificar_download, decidir_acao
from include.ingestao.fonte_http import BASE_URL_TLC, baixar, consultar_head, url_do_mes
from include.ingestao.manifesto import RegistroManifesto, ler_historico, proximo_mes_esperado, registrar

log = logging.getLogger(__name__)

FONTE = "tlc_hvfhv"

# Produção e teste usam o MESMO código; só muda para onde ele grava (etapa 8)
AMBIENTES = {
    "prod": {"prefixo_bronze": "bronze", "banco_controle": "controle"},
    "teste": {"prefixo_bronze": "teste_bronze", "banco_controle": "teste_controle"},
}

# O dado que esta DAG produz. Outras DAGs (weather_ingest, dbt_build) são disparadas por ele (Aula 5)
BRONZE_TLC = Asset(f"s3://{BUCKET_LAKE}/bronze/{FONTE}")


def _clientes_aws():
    """Clientes criados DENTRO de cada task: cada uma ganha a sua credencial de 1 hora (D8)."""
    sessao = AwsBaseHook(aws_conn_id="aws_default").get_session()
    return sessao.client("s3"), sessao.client("athena")


def _meses_do_recorte(primeiro_mes: str, hoje: datetime) -> list[str]:
    """Do primeiro mês até o mês passado (o mês corrente nunca está publicado)."""
    ano, mes = map(int, primeiro_mes.split("-"))
    ultimo = (hoje.year, hoje.month - 1) if hoje.month > 1 else (hoje.year - 1, 12)
    meses = []
    while (ano, mes) <= ultimo:
        meses.append(f"{ano:04d}-{mes:02d}")
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    return meses


@dag(
    dag_id="tlc_ingest",
    schedule="0 9 * * *",  # todo dia às 9h UTC (5h ou 6h em Nova York)
    start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    catchup=False,  # o histórico vem pelo manifesto, não por runs atrasados (D1)
    max_active_runs=1,  # dois runs juntos gravariam o mesmo mês em ingest_ts diferentes
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=2),
        "retry_exponential_backoff": True,  # 2, ~4, ~8 minutos
        "max_retry_delay": timedelta(minutes=30),
    },
    params={
        "ambiente": Param("prod", enum=list(AMBIENTES), description="prod ou teste (TLC de mentira)"),
        "base_url": Param(BASE_URL_TLC, type="string", description="Endereço da pasta de arquivos da TLC"),
        "primeiro_mes": Param("2024-01", type="string", description="Início do recorte (spec 3.5)"),
        "reprocessar_meses": Param(
            [], type="array",
            description="Meses a reprocessar à força, como 2025-01 (ex.: depois de corrigir o contrato)",
        ),
    },
    tags=["ingestao", "bronze", "fase-2"],
    doc_md=__doc__,
)
def tlc_ingest():

    @task
    def planejar(**contexto) -> list[dict]:
        """HEAD de cada mês + histórico do manifesto -> decidir_acao. Nada é baixado aqui.

        Devolve só os meses que precisam de alguém: os que vão ser baixados e os que deram erro.
        Os de "ignorar" e "aguardar" aparecem só no log.
        """
        params = contexto["params"]
        ambiente = AMBIENTES[params["ambiente"]]
        _, athena = _clientes_aws()

        historico = ler_historico(athena, ambiente["banco_controle"], FONTE)
        proximo = proximo_mes_esperado(historico, params["primeiro_mes"])
        forcados = set(params["reprocessar_meses"])

        trabalho, resumo = [], {}
        for mes in _meses_do_recorte(params["primeiro_mes"], datetime.now(timezone.utc)):
            linhas = historico.get(mes, [])
            resposta = consultar_head(url_do_mes(mes, params["base_url"]))
            acao = decidir_acao(mes, resposta, linhas, proximo)
            if mes in forcados and resposta.status == 200:
                acao = "reprocessar_forcado"
            resumo.setdefault(acao, []).append(mes)

            if acao == "erro":
                trabalho.append({
                    "mes": mes,
                    "acao": "erro",
                    "motivo": f"HEAD {resposta.status}; histórico do mês: {[l.status for l in linhas] or 'vazio'}",
                })
            elif acao in ("baixar", "reprocessar", "reprocessar_forcado"):
                trabalho.append({
                    "mes": mes,
                    "acao": acao,
                    # Peça 1 do D3: a versão é decidida AQUI, uma vez. O retry de ingerir_mes reusa.
                    "ingest_ts": novo_ingest_ts(),
                    "etag": resposta.etag,
                    "last_modified": resposta.last_modified.isoformat() if resposta.last_modified else None,
                    "content_length": resposta.content_length,
                    "historico": [[l.ingest_ts, l.etag, l.file_sha256, l.status] for l in linhas],
                })

        log.info("Próximo mês esperado: %s", proximo)
        for acao, meses in sorted(resumo.items()):
            log.info("%-20s %3d mês(es): %s", acao, len(meses), ", ".join(meses))
        return trabalho

    @task(
        max_active_tis_per_dag=3,  # no máximo 3 downloads de ~480 MB ao mesmo tempo
        map_index_template="{{ task.op_kwargs['item']['mes'] }}",  # a grade mostra o mês, não 0, 1, 2...
    )
    def ingerir_mes(item: dict, **contexto) -> dict:
        """Baixa um mês, confere, grava na Bronze (se for versão nova) e registra no manifesto."""
        if item["acao"] == "erro":
            # Erro determinístico (decidir_acao): tentar de novo não resolve. Vermelho, sem retry.
            raise AirflowFailException(f"{item['mes']} precisa de uma pessoa: {item['motivo']}")

        params = contexto["params"]
        ambiente = AMBIENTES[params["ambiente"]]
        s3, athena = _clientes_aws()
        mes = item["mes"]
        url = url_do_mes(mes, params["base_url"])
        historico = [LinhaManifesto(*linha) for linha in item["historico"]]
        nome_arquivo = url.rsplit("/", 1)[1]

        arquivo = baixar(url, item["content_length"])
        try:
            if item["acao"] == "reprocessar_forcado":
                tipo = "nova_versao"  # conferir de novo contra o contrato, mesmo com o conteúdo igual
            else:
                tipo = classificar_download(arquivo.sha256, historico)

            colunas = ler_colunas(arquivo.caminho)
            contrato = validar(colunas, carregar_contrato(FONTE), mes)
            for alerta in contrato.alertas:
                log.warning("%s: %s", mes, alerta)

            if tipo == "mesmo_conteudo":
                # Conferência: nenhum arquivo novo. Aponta para a versão que já existe (etapa 5)
                ultima = max((l for l in historico if l.status in ("aceito", "rejeitado")),
                             key=lambda l: l.ingest_ts)
                ingest_ts, status = ultima.ingest_ts, "mesmo_conteudo"
                motivo = f"ETag novo sem mudança de conteúdo; mesmo arquivo da versão {ingest_ts}"
            else:
                ingest_ts, status, motivo = item["ingest_ts"], contrato.status, contrato.motivo
                # Arquivo novo (aceito ou rejeitado) entra na Bronze; rejeitado fica em quarentena (D7)
                gravacao = gravar_sem_sobrescrever(
                    s3,
                    chave_bronze(ambiente["prefixo_bronze"], FONTE, mes, ingest_ts, nome_arquivo),
                    arquivo.caminho,
                    arquivo.sha256,
                )
                log.info("%s: arquivo %s (versão %s)", mes, gravacao, ingest_ts)

            chave = chave_bronze(ambiente["prefixo_bronze"], FONTE, mes, ingest_ts, nome_arquivo)
            # Peça 4 do D3: o manifesto é o último passo. Se a task cair antes, nada "conta".
            registrar(athena, ambiente["banco_controle"], RegistroManifesto(
                source=FONTE,
                source_month=mes,
                source_url=url,
                etag=item["etag"],
                last_modified=datetime.fromisoformat(item["last_modified"]) if item["last_modified"] else None,
                content_length=arquivo.tamanho,
                file_sha256=arquivo.sha256,
                row_count=contar_linhas(arquivo.caminho),
                schema_hash=contrato.schema_hash,
                s3_path=f"s3://{BUCKET_LAKE}/{chave}",
                ingest_ts=ingest_ts,
                status=status,
                motivo=motivo,
                registrado_em=datetime.now(timezone.utc),
                dag_run_id=contexto["run_id"],
            ))
            log.info("%s: manifesto registrado como %s", mes, status)
        finally:
            arquivo.caminho.unlink(missing_ok=True)  # o arquivo temporário de ~480 MB não fica no disco

        if status == "rejeitado":
            # Já está na Bronze (quarentena) e no manifesto. Retry baixaria 480 MB à toa: sem retry.
            raise AirflowFailException(f"{mes} em QUARENTENA, fora do contrato: {motivo}")
        return {"mes": mes, "status": status}

    @task(outlets=[BRONZE_TLC], trigger_rule="all_done")
    def publicar(resultados, **contexto):
        """Publica o Asset bronze_tlc se ALGUM mês ganhou versão aceita. Senão, pula (sem evento).

        all_done: roda mesmo que algum mês tenha falhado; os meses aceitos seguem adiante.
        """
        aceitos = [r["mes"] for r in resultados if r and r["status"] == "aceito"]
        if contexto["params"]["ambiente"] != "prod":
            raise AirflowSkipException("Ambiente de teste: não dispara as DAGs de produção")
        if not aceitos:
            raise AirflowSkipException("Nenhuma versão nova aceita: nada a publicar")
        log.info("Bronze atualizada: %s", ", ".join(aceitos))

    @task
    def tudo_certo():
        """Só roda se TODOS os meses deram certo. Se algum falhou, fica 'upstream_failed' e o
        run inteiro termina como falho: o problema não se esconde atrás de um run "verde"."""
        log.info("Todos os meses com ação terminaram bem.")

    resultados = ingerir_mes.expand(item=planejar())
    publicar(resultados)
    resultados >> tudo_certo()


tlc_ingest()
