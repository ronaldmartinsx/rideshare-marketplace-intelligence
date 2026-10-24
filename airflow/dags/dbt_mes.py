"""DAGs dbt_mes_dev e dbt_mes_prod: o projeto dbt de UM mês, um model por task (Fase 3, decisão F5).

Disparadas pela dbt_build (uma execução por mês, com o mês no parâmetro source_month). O Cosmos lê o
projeto dbt e cria uma task por model, com os testes logo depois de cada model: se um teste "error"
falha (o gate de volume, por exemplo), as tasks seguintes, como a Gold, nem começam (proteção) e o
run fica vermelho (alarme).

Duas DAGs, uma por ambiente: o target do dbt (dev -> dev_silver/dev_gold; prod -> silver/gold) é
fixo no perfil, então cada ambiente tem a sua.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from airflow.sdk import Param
from cosmos import DbtDag, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import LoadMode
from cosmos.profiles import AthenaAccessKeyProfileMapping

PROJETO_DBT = "/usr/local/airflow/dbt"  # montado pelo docker-compose.override.yml (F6)
DBT_EXECUTAVEL = "/usr/local/airflow/dbt_venv/bin/dbt"  # ambiente próprio do dbt (Dockerfile, F7)


def _perfil(ambiente: str) -> ProfileConfig:
    """Conexão do dbt com o Athena pela Connection aws_default: veste a role rideshare-airflow (F8)."""
    return ProfileConfig(
        profile_name="rideshare",
        target_name=ambiente,
        profile_mapping=AthenaAccessKeyProfileMapping(
            conn_id="aws_default",
            profile_args={
                "region_name": "us-east-1",
                "database": "awsdatacatalog",
                "schema": ambiente,  # a macro generate_schema_name monta dev_silver ou silver
                "work_group": "rideshare",
                "s3_staging_dir": "s3://rmartins-rideshare-athena-results/resultados/",
                "s3_data_dir": "s3://rmartins-rideshare-lake/",
                "s3_data_naming": "schema_table",
                "threads": 4,
            },
        ),
    )


for ambiente in ("dev", "prod"):
    globals()[f"dbt_mes_{ambiente}"] = DbtDag(
        dag_id=f"dbt_mes_{ambiente}",
        project_config=ProjectConfig(PROJETO_DBT),
        profile_config=_perfil(ambiente),
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
        },
        schedule=None,  # só por disparo da dbt_build (ou manual)
        start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
        catchup=False,
        max_active_runs=1,  # um mês por vez: o delete + append de um mês não pode cruzar com outro
        default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
        tags=["dbt", "silver", "gold", "fase-3", ambiente],
        doc_md=__doc__,
    )
