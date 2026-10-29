"""Retries da dbt_mes: testes sem retry, models com retry (Fase 3, etapa 11).

Rodar no scheduler (o Cosmos precisa do projeto dbt montado):
  docker exec -w /usr/local/airflow rideshare_161090-scheduler-1 python -m pytest tests/dags/test_dbt_mes.py
"""

import pytest
from airflow.models import DagBag
from cosmos.operators.local import DbtTestLocalOperator


@pytest.fixture(scope="module")
def dagbag():
    return DagBag(include_examples=False)


@pytest.mark.parametrize("dag_id", ["dbt_mes_dev", "dbt_mes_prod"])
def test_testes_sem_retry_e_models_com_retry(dagbag, dag_id):
    dag = dagbag.dags[dag_id]
    testes = [t for t in dag.tasks if isinstance(t, DbtTestLocalOperator)]
    outras = [t for t in dag.tasks if not isinstance(t, DbtTestLocalOperator)]

    assert testes, "o Cosmos deveria criar tasks de teste"
    assert all(t.retries == 0 for t in testes)
    # Models e o registro continuam com retry: falha de rede no meio de um INSERT vale repetir
    assert all(t.retries >= 2 for t in outras)
