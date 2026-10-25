"""Onde está o projeto dbt e como o dbt fala com o Athena dentro do Airflow (Fase 3, F6 a F8).

Comum às DAGs dbt_mes e dbt_build: uma DAG não importa o arquivo de outra.
"""

from cosmos import ProfileConfig
from cosmos.profiles import AthenaAccessKeyProfileMapping

PROJETO_DBT = "/usr/local/airflow/dbt"  # montado pelo docker-compose.override.yml (F6)
DBT_EXECUTAVEL = "/usr/local/airflow/dbt_venv/bin/dbt"  # ambiente próprio do dbt (Dockerfile, F7)


def perfil(ambiente: str) -> ProfileConfig:
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
