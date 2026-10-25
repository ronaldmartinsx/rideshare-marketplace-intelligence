"""DAG manutencao_iceberg: OPTIMIZE e VACUUM semanais das tabelas Iceberg (Fase 3, etapa 8, F12).

    listar_tabelas (Glue) ──> manter_tabela (uma task por tabela)

- Controle (manifesto e registro de construção): OPTIMIZE (junta os arquivos minúsculos de cada
  INSERT) + VACUUM. Retenção de 90 dias, definida na criação das tabelas.
- Silver e Gold (prod e dev): só VACUUM. Retenção padrão do Athena, 5 dias: a Bronze é a fonte da
  verdade e a Silver/Gold podem ser reconstruídas.

O VACUUM só apaga arquivos órfãos com mais de 5 dias (documentação do Athena), então não atrapalha
uma construção do dbt rodando ao mesmo tempo. Conflito de gravação (ICEBERG_COMMIT_ERROR) é
resolvido pelo retry.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook
from airflow.sdk import Param, dag, task

from include.ingestao.ambientes import clientes_aws
from include.ingestao.manifesto import _executar
from include.manutencao import BANCOS, comandos, tabelas_iceberg

log = logging.getLogger(__name__)


@dag(
    dag_id="manutencao_iceberg",
    schedule="0 6 * * 0",  # domingo, 6h UTC: antes da tlc_ingest das 9h
    start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=5),  # dá tempo para a outra gravação terminar
    },
    params={
        "bancos": Param(BANCOS, type="array", description="Bancos a varrer (ex.: só dev_silver para testar)"),
    },
    tags=["manutencao", "iceberg", "fase-3"],
    doc_md=__doc__,
)
def manutencao_iceberg():
    @task
    def listar_tabelas(**contexto) -> list[dict]:
        glue = AwsBaseHook(aws_conn_id="aws_default").get_session().client("glue")
        tabelas = tabelas_iceberg(glue, contexto["params"]["bancos"])
        log.info("%d tabelas Iceberg: %s", len(tabelas), ", ".join(t["tabela"] for t in tabelas))
        return tabelas

    @task(map_index_template="{{ task.op_kwargs['item']['tabela'] }}", max_active_tis_per_dagrun=2)
    def manter_tabela(item: dict):
        """Roda os comandos de uma tabela. Uma task por tabela: a que falhar fica vermelha com o nome."""
        _, athena = clientes_aws()
        for comando in comandos(item["tabela"], item["compactar"]):
            log.info("Rodando: %s", comando)
            _executar(athena, comando, intervalo=5)

    manter_tabela.expand(item=listar_tabelas())


manutencao_iceberg()
