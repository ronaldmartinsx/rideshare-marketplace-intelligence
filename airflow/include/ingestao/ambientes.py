"""Para onde cada ambiente grava, e a conexão com a AWS (compartilhado pelas DAGs de ingestão).

Produção e teste usam o MESMO código; só muda o destino (etapa 8).
"""

from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook

AMBIENTES = {
    "prod": {"prefixo_bronze": "bronze", "banco_controle": "controle"},
    "teste": {"prefixo_bronze": "teste_bronze", "banco_controle": "teste_controle"},
}


def clientes_aws():
    """Clientes S3 e Athena criados DENTRO de cada task: cada uma ganha a sua credencial de 1 hora (D8)."""
    sessao = AwsBaseHook(aws_conn_id="aws_default").get_session()
    return sessao.client("s3"), sessao.client("athena")
