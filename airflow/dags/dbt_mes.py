"""DAGs dbt_mes_dev e dbt_mes_prod: o projeto dbt de UM mês, um model por task (Fase 3, decisão F5).

Disparadas pela dbt_build (uma execução por mês, com o mês no parâmetro source_month). O Cosmos lê o
projeto dbt e cria uma task por model, com os testes logo depois de cada model: se um teste "error"
falha (o gate de volume, por exemplo), as tasks seguintes, como a Gold, nem começam (proteção) e o
run fica vermelho (alarme).

Duas DAGs, uma por ambiente: o target do dbt (dev -> dev_silver/dev_gold; prod -> silver/gold) é
fixo no perfil, então cada ambiente tem a sua.

A última task, registrar_construcao, só roda se TODAS as tasks do dbt ficarem verdes (gate e
reconciliações incluídos). Ela grava no registro (controle.dbt_meses_construidos) as versões que
a Silver de fato usou. É assim que a dbt_build sabe que o mês está em dia.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from airflow.sdk import Param, task
from cosmos import DbtDag, ExecutionConfig, ProjectConfig, RenderConfig
from cosmos.constants import LoadMode
from cosmos.operators.local import DbtTestLocalOperator

from include.dbt_perfil import DBT_EXECUTAVEL, PROJETO_DBT, perfil
from include.dbt_registro import gravar_construcao, versoes_na_silver
from include.ingestao.ambientes import clientes_aws

log = logging.getLogger(__name__)


def _registrar_construcao(ambiente: str):
    """Task final: grava o mês no registro de construção deste ambiente (Fase 3, B1)."""

    @task(task_id="registrar_construcao", retries=3)
    def registrar_construcao(**contexto):
        _, athena = clientes_aws()
        mes = contexto["params"]["source_month"]
        construcao = versoes_na_silver(athena, ambiente, mes)
        gravado = gravar_construcao(
            athena, ambiente, mes, construcao, contexto["params"]["motivo"], contexto["run_id"]
        )
        log.info("%s %s registrado: TLC %s, clima %s%s", ambiente, mes, construcao.ingest_ts_tlc,
                 construcao.ingest_ts_clima, "" if gravado else " (já gravado por uma tentativa anterior)")

    return registrar_construcao()


for ambiente in ("dev", "prod"):
    with DbtDag(
        dag_id=f"dbt_mes_{ambiente}",
        project_config=ProjectConfig(PROJETO_DBT),
        profile_config=perfil(ambiente),
        execution_config=ExecutionConfig(dbt_executable_path=DBT_EXECUTAVEL),
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            dbt_deps=False,  # igual ao install_deps abaixo: o Cosmos exige os dois iguais
            select=["path:models"],  # só os models (e seus testes); os seeds rodam à parte, na dbt_build
            # Testes com dois "pais" (as reconciliações Silver x Gold) em task própria, depois dos dois
            should_detach_multiple_parents_tests=True,
        ),
        operator_args={
            # O mês vem do parâmetro da execução (preenchido pela dbt_build). "vars" é template_field
            # no Cosmos 1.15.1 (conferido no código): o Airflow preenche o mês na hora de rodar.
            "vars": {"source_month": "{{ params.source_month }}"},
            "install_deps": False,  # o dbt_packages já está no projeto montado (dbt deps rodado no Mac)
        },
        params={
            "source_month": Param("2026-05", type="string", pattern=r"^\d{4}-\d{2}$",
                                  description="Mês do arquivo a processar (AAAA-MM)"),
            # Vai para o registro. A dbt_build preenche; disparo à mão fica como "manual".
            "motivo": Param("manual", enum=["manual", "manifesto", "forcado"],
                            description="Por que este mês está sendo construído"),
        },
        schedule=None,  # só por disparo da dbt_build (ou manual)
        start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
        catchup=False,
        max_active_runs=1,  # um mês por vez: o delete + append de um mês não pode cruzar com outro
        default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
        tags=["dbt", "silver", "gold", "fase-3", ambiente],
        doc_md=__doc__,
    ) as dag_dbt:
        # As folhas são as últimas tasks do dbt (testes da Gold e reconciliações). O registro
        # depende de todas: com a regra padrão (all_success), qualquer vermelho o impede.
        folhas = list(dag_dbt.leaves)
        folhas >> _registrar_construcao(ambiente)

        # Teste sem retry (decisão do Ronald, 28/10/2026): um teste que falha (gate de volume,
        # reconciliação) falha igual na 2ª tentativa, e o retry só atrasa o alarme em 4 minutos.
        # Se o Athena oscilar, o mês fica sem registro e volta como pendente no próximo run.
        for tarefa in dag_dbt.tasks:
            if isinstance(tarefa, DbtTestLocalOperator):
                tarefa.retries = 0
    globals()[f"dbt_mes_{ambiente}"] = dag_dbt
