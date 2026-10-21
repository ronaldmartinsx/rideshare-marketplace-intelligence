"""Roda um arquivo .sql no Athena (workgroup rideshare) e mostra o resultado de cada comando.

O Athena aceita um comando por execução: o arquivo é dividido nos ";". Linhas que começam com
"--" são ignoradas. Usa o perfil da AWS CLI (padrão: rideshare-admin, login SSO).

Uso, a partir da raiz do repositório (o boto3 vem no ambiente do dbt):
    dbt/.venv/bin/python scripts/athena_roda.py consulta.sql
    dbt/.venv/bin/python scripts/athena_roda.py scripts/fase-2/controle_manifesto.sql teste_controle

O segundo argumento, opcional, troca o marcador __BANCO__ do arquivo pelo nome dado.
"""

import os
import sys
import time

import boto3

PERFIL = os.environ.get("AWS_PROFILE", "rideshare-admin")


def main() -> None:
    sql = open(sys.argv[1], encoding="utf-8").read()
    if len(sys.argv) > 2:
        sql = sql.replace("__BANCO__", sys.argv[2])
    sql = "\n".join(linha for linha in sql.splitlines() if not linha.strip().startswith("--"))
    athena = boto3.Session(profile_name=PERFIL, region_name="us-east-1").client("athena")

    for comando in (c.strip() for c in sql.split(";") if c.strip()):
        qid = athena.start_query_execution(QueryString=comando, WorkGroup="rideshare")["QueryExecutionId"]
        while True:
            execucao = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
            estado = execucao["Status"]["State"]
            if estado in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            time.sleep(1)
        mb = execucao["Statistics"].get("DataScannedInBytes", 0) / 1024**2
        print(f"{estado:9} | {mb:8.1f} MB lidos | {' '.join(comando.split()[:8])}")
        if estado != "SUCCEEDED":
            print("   ", execucao["Status"].get("StateChangeReason", "")[:400])
            sys.exit(1)
        if comando.upper().startswith(("SELECT", "WITH", "SHOW", "DESCRIBE")):
            for linha in athena.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"]:
                print("   ", " | ".join(dado.get("VarCharValue", "") for dado in linha["Data"]))


if __name__ == "__main__":
    main()
