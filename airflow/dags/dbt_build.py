"""DAGs dbt_build_dev e dbt_build_prod: quais meses construir, e construí-los em ordem (Fase 3, F5).

Quando chega dado novo na Bronze (Assets), compara o manifesto com o registro de construção, decide
mês a mês pela regra do Ronald (include/dbt_construcao.py) e dispara a dbt_mes de cada mês pendente,
um por vez, do mais antigo para o mais novo (o gate de um mês compara com os 3 anteriores).

    seeds ──> freshness (só alarme)
      └──> planejar ──> construir_mes (uma task por mês, uma de cada vez) ──> publicar (Asset)
                                                                         └──> tudo_certo

- Quem grava o registro é a dbt_mes, na última task, só se o mês inteiro ficar verde.
- Um mês que falha fica vermelho com o próprio nome; os seguintes continuam (B3). Ele não ganha
  linha no registro, então continua pendente e é tentado de novo no próximo run.
- Um mês pedido em forcar_meses que não pode ser construído deixa o run vermelho no fim.

Duas DAGs, uma por ambiente, como a dbt_mes: prod é disparada pelos Assets; dev, só à mão.
Dev é uma amostra: só cuida dos meses que já estão no registro de dev e dos forçados (um mês entra
em dev quando é forçado uma vez; depois acompanha o manifesto sozinho).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from airflow.sdk.exceptions import AirflowFailException, AirflowSkipException
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import Param, dag, task
from cosmos.operators.local import DbtSeedLocalOperator, DbtSourceLocalOperator

from include.dbt_construcao import planejar_construcao
from include.dbt_perfil import DBT_EXECUTAVEL, PROJETO_DBT, perfil
from include.dbt_registro import ler_construidos, ler_vigentes, meses_registrados_desde
from include.ingestao.ambientes import clientes_aws
from include.ingestao.assets import BRONZE_CLIMA, BRONZE_TLC, GOLD_DEMANDA

log = logging.getLogger(__name__)


def _dbt_build(ambiente: str):
    producao = ambiente == "prod"

    @dag(
        dag_id=f"dbt_build_{ambiente}",
        # Qualquer um dos dois Assets dispara. O mês novo da TLC dispara antes do clima chegar;
        # ele espera (linha 2 da tabela) e entra no run disparado pelo clima (B2).
        schedule=(BRONZE_TLC | BRONZE_CLIMA) if producao else None,
        start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
        catchup=False,
        max_active_runs=1,  # dois runs juntos decidiriam e disparariam os mesmos meses
        default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},  # rede e Athena
        params={
            "forcar_meses": Param(
                [], type="array",
                description="Meses a reconstruir à força, como 2025-01 (ex.: depois de mudar o código do dbt)",
            ),
        },
        tags=["dbt", "fase-3", ambiente],
        doc_md=__doc__,
    )
    def dbt_build():
        argumentos_dbt = {
            "project_dir": PROJETO_DBT,
            "profile_config": perfil(ambiente),
            "dbt_executable_path": DBT_EXECUTAVEL,
            "install_deps": False,  # o dbt_packages já está no projeto montado
        }

        # Seeds (zonas, CBD, operadoras, feriados) antes de qualquer mês: as stagings e a Gold leem
        seeds = DbtSeedLocalOperator(task_id="seeds", **argumentos_dbt)

        # Freshness do manifesto (warn 45 d, erro 75 d): vermelho avisa, mas não impede os meses (B4)
        freshness = DbtSourceLocalOperator(
            task_id="freshness", retries=0, **argumentos_dbt  # manifesto velho não melhora em 2 minutos
        )

        @task
        def planejar(**contexto) -> list[dict]:
            """Decide todos os meses e devolve só os que serão construídos (no formato do conf)."""
            _, athena = clientes_aws()
            tlc, clima = ler_vigentes(athena)
            decisoes = planejar_construcao(
                tlc, clima, ler_construidos(athena, ambiente), contexto["params"]["forcar_meses"],
                somente_meses_conhecidos=not producao,  # dev é amostra, prod é tudo
            )
            for decisao in decisoes:
                if decisao.construir or decisao.pedido_nao_atendido:
                    acao = "CONSTRUIR" if decisao.construir else "PEDIDO NÃO ATENDIDO"
                    log.info("%s: %s (%s)", decisao.mes, acao, decisao.motivo)
            em_dia = sum(1 for d in decisoes if not d.construir and not d.pedido_nao_atendido)
            log.info("%d meses em dia ou aguardando versão (sem ação)", em_dia)

            contexto["ti"].xcom_push(
                key="pedidos_nao_atendidos",
                value=[f"{d.mes} ({d.motivo})" for d in decisoes if d.pedido_nao_atendido],
            )
            return [{"source_month": d.mes, "motivo": d.motivo} for d in decisoes if d.construir]

        # Uma task por mês, uma de cada vez, na ordem da lista (o scheduler ordena pelo map_index).
        # Cada uma dispara a dbt_mes do mês e espera ela terminar; se a dbt_mes falha, esta falha.
        construir_mes = TriggerDagRunOperator.partial(
            task_id="construir_mes",
            trigger_dag_id=f"dbt_mes_{ambiente}",
            wait_for_completion=True,
            poke_interval=60,
            max_active_tis_per_dagrun=1,
            retries=0,  # as tasks da dbt_mes já têm retry; repetir aqui reconstruiria o mês inteiro
        ).expand(conf=planejar())

        @task(outlets=[GOLD_DEMANDA] if producao else [], trigger_rule="all_done")
        def publicar(**contexto):
            """Publica o Asset da Gold se algum mês foi registrado neste run (só em produção)."""
            _, athena = clientes_aws()
            meses = meses_registrados_desde(athena, ambiente, contexto["dag_run"].start_date)
            if not producao:
                raise AirflowSkipException(f"Dev não dispara a Fase 5. Meses construídos: {meses}")
            if not meses:
                raise AirflowSkipException("Nenhum mês construído neste run: nada a publicar")
            log.info("Gold atualizada: %s", ", ".join(meses))

        @task(trigger_rule="none_failed")
        def tudo_certo(**contexto):
            """Só passa se nenhum mês falhou E todo pedido de forcar_meses foi atendido.

            none_failed: roda também quando não havia mês para construir (construir_mes pulado),
            para o pedido impossível não passar em silêncio num run sem nenhum mês.
            """
            pedidos = contexto["ti"].xcom_pull(task_ids="planejar", key="pedidos_nao_atendidos")
            if pedidos:
                raise AirflowFailException(f"Pedidos de forcar_meses não atendidos: {', '.join(pedidos)}")
            log.info("Todos os meses pendentes construídos e todos os pedidos atendidos.")

        seeds >> freshness
        seeds >> construir_mes
        construir_mes >> [publicar(), tudo_certo()]

    return dbt_build()


for ambiente in ("dev", "prod"):
    globals()[f"dbt_build_{ambiente}"] = _dbt_build(ambiente)
