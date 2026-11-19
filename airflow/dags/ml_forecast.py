"""DAG ml_forecast: treino, backtest, previsão e gravação em gold.ml_* (Fase 5, passo 7).

    planejar ──> executar ──> conferir

Disparada pelo Asset `gold_demanda` (spec, Seção 7): quando a dbt_build reconstrói algum mês da Gold
de produção, a previsão é refeita com o dado novo.

POR QUE O TRABALHO PESADO FICA NUMA TASK SÓ:
O que passa entre tasks do Airflow vai pelo XCom, que é feito para valores pequenos — um nome, um
número, uma lista de meses. A tabela de features tem 415 MB em memória e NÃO cabe lá. Então ou cada
task relê do Athena (27 s e uma varredura a cada vez), ou o pesado fica junto. Ficou junto, e a
visibilidade vem das tasks de antes e de depois: `planejar` mostra o que VAI rodar antes de gastar
oito minutos, e `conferir` prova que o que foi gravado é o que se esperava.

Melhoria possível, registrada e não feita: uma task por rodada, com dynamic task mapping, daria
retry e visibilidade por rodada — ao custo de reler as features em cada uma.

LIMITAÇÃO HONESTA (spec 9.1): a previsão não é operacional. Os dados da TLC saem com ~2 meses de
atraso, então o mês previsto já passou quando a previsão fica pronta. O enquadramento é "validado em
backtest; em produção seria alimentado por streaming".
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from airflow.sdk import Param, dag, task

from include.ingestao.assets import GOLD_DEMANDA

log = logging.getLogger(__name__)


@dag(
    dag_id="ml_forecast",
    schedule=[GOLD_DEMANDA],  # dependência por DADO, não por horário (spec, Seção 7)
    start_date=datetime(2026, 11, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,  # dois treinos ao mesmo tempo brigariam por CPU e pelo append na tabela
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    params={
        "ambiente": Param("prod", enum=["dev", "prod"]),
        "rodadas": Param(6, type="integer", description="Rodadas de backtest (spec 9.1: 6)"),
        "arvores": Param(500, type="integer", description="Árvores do LightGBM"),
        "incluir_producao": Param(True, type="boolean", description="Prever o mês sem gabarito"),
        "gravar": Param(True, type="boolean", description="Gravar em gold.ml_*"),
        "salvar_modelo": Param(True, type="boolean", description="Gravar o binário no S3"),
    },
    tags=["ml", "forecast", "fase-5"],
    doc_md=__doc__,
)
def ml_forecast():

    @task
    def planejar(**contexto) -> dict:
        """Monta as rodadas e devolve o plano, SEM ler a tabela de features.

        Consulta só a lista de cortes (uma agregação de poucas linhas), para o plano aparecer no
        XCom antes de a execução gastar oito minutos. Se a regra das rodadas estiver errada, isso
        fica visível aqui — e a regra em si é testada em tests/test_ml_janelas.py, sem nuvem.
        """
        from include.ml import config, dados, janelas

        p = contexto["params"]
        sessao = dados.sessao_airflow()

        cortes = dados.consultar(
            f"select mes_corte, max(tem_alvo) as tem_alvo "
            f"from {config.TABELA_FEATURES} group by mes_corte order by mes_corte",
            p["ambiente"],
            sessao,
        )

        avaliaveis = cortes.loc[cortes["tem_alvo"], "mes_corte"].tolist()
        sem_alvo = cortes.loc[~cortes["tem_alvo"], "mes_corte"].tolist()
        producao = sem_alvo[-1] if (p["incluir_producao"] and sem_alvo) else None

        planejadas = janelas.planejar_rodadas(avaliaveis, producao, rodadas=p["rodadas"])
        if not planejadas:
            from airflow.sdk.exceptions import AirflowFailException

            raise AirflowFailException(
                f"nenhuma rodada planejada: {len(avaliaveis)} cortes com gabarito"
            )

        for r in planejadas:
            log.info(
                "rodada %s: corte %s -> alvo %s, treinando com %d cortes",
                r.tipo, r.corte, r.mes_alvo, len(r.cortes_treino),
            )

        return {
            "cortes_avaliaveis": len(avaliaveis),
            "corte_producao": producao,
            "rodadas": [
                {"tipo": r.tipo, "corte": r.corte, "mes_alvo": r.mes_alvo,
                 "cortes_treino": len(r.cortes_treino)}
                for r in planejadas
            ],
        }

    @task
    def executar(plano: dict, **contexto) -> dict:
        """Lê, treina, prevê e grava. O pesado, numa task só (ver o doc da DAG)."""
        from include.ml import backtest, dados, persistencia

        p = contexto["params"]
        sessao = dados.sessao_airflow()

        tabela, resultados = backtest.rodar(
            p["ambiente"],
            sessao,
            rodadas=p["rodadas"],
            incluir_producao=p["incluir_producao"],
            n_arvores=p["arvores"],
            salvar_modelo=p["salvar_modelo"],
        )

        if len(tabela) != len(plano["rodadas"]):
            from airflow.sdk.exceptions import AirflowFailException

            raise AirflowFailException(
                f"executou {len(tabela)} rodadas, o plano previa {len(plano['rodadas'])}"
            )

        avaliadas = tabela.dropna(subset=["wape_modelo"])
        for linha in avaliadas.itertuples():
            log.info(
                "%s: modelo %.2f%% x baseline %.2f%% (ganho %+.2f pp)",
                linha.mes_alvo, linha.wape_modelo, linha.wape_baseline, linha.ganho_pp,
            )

        execucao = None
        if p["gravar"]:
            escrito = persistencia.gravar(resultados, tabela, p["ambiente"], sessao)
            execucao = escrito["execucao"]
            log.info("gravado na execução %s: %s", execucao, escrito)

        return {
            "execucao": execucao,
            "rodadas_avaliadas": len(avaliadas),
            "wape_modelo_medio": float(avaliadas["wape_modelo"].mean()),
            "wape_baseline_medio": float(avaliadas["wape_baseline"].mean()),
            "venceu": int((avaliadas["ganho_pp"] > 0).sum()),
        }

    @task
    def conferir(resumo: dict, **contexto) -> dict:
        """Relê a tabela gravada e confirma que ela bate com o que a execução reportou.

        Não é cerimônia: gravação que "deu certo" sem ninguém reler é gravação não verificada. O
        mesmo princípio do teste de reconciliação do dbt.

        Este passo NÃO reprova por o modelo perder do baseline. Perder é um resultado legítimo da
        fase (spec, Seção 12: "um modelo que vença o baseline, OU um relatório honesto de que não
        venceu"). Reprovar por isso empurraria para esconder resultado ruim.
        """
        from include.ml import dados, persistencia

        if not resumo["execucao"]:
            log.info("execução sem gravação (gravar=False): nada a conferir")
            return resumo

        p = contexto["params"]
        gravado = dados.consultar(
            f"select count(*) as linhas, "
            f"sum(case when venceu_baseline then 1 else 0 end) as venceu, "
            f"avg(wape_modelo) as wape_modelo, avg(wape_baseline) as wape_baseline "
            f"from {persistencia.TABELA_METRICAS} where execucao = '{resumo['execucao']}'",
            p["ambiente"],
            dados.sessao_airflow(),
        ).iloc[0]

        if int(gravado["venceu"]) != resumo["venceu"]:
            from airflow.sdk.exceptions import AirflowFailException

            raise AirflowFailException(
                f"a tabela diz {int(gravado['venceu'])} vitórias, a execução reportou "
                f"{resumo['venceu']}"
            )

        log.info(
            "conferido: %d linhas gravadas, modelo %.2f%% x baseline %.2f%%, venceu em %d de %d",
            int(gravado["linhas"]), resumo["wape_modelo_medio"], resumo["wape_baseline_medio"],
            resumo["venceu"], resumo["rodadas_avaliadas"],
        )
        return resumo

    conferir(executar(planejar()))


ml_forecast()
