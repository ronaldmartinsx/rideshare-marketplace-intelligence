"""Leitura e escrita do manifesto de ingestão via Athena (Fase 2, etapa 6; D3, D4, D5).

- ler_historico: UMA consulta traz todas as linhas da fonte (a tabela é minúscula) e as agrupa
  por mês, no formato que decidir_acao recebe.
- registrar: grava uma linha (o "commit" da ingestão: sempre o último passo). Só INSERT (D5).
  Se a mesma linha já existe (retry depois de um INSERT que deu certo), não grava de novo.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, fields
from datetime import datetime, timezone

from include.ingestao.decisao import LinhaManifesto
from include.ingestao.fonte_http import ErroTransitorio

WORKGROUP = "rideshare"  # o workgroup com o freio de 1 GiB (a role do Airflow só pode usar este)

# Mensagens do Athena que indicam conflito momentâneo: tentar de novo resolve.
# ICEBERG_COMMIT_ERROR: duas tasks gravaram no manifesto ao mesmo tempo e uma perdeu a vez.
_ERROS_TRANSITORIOS = ("ICEBERG_COMMIT_ERROR", "ThrottlingException", "TooManyRequests")


@dataclass(frozen=True)
class RegistroManifesto:
    """Uma linha completa de <banco>.ingestion_manifest, na ordem das colunas da tabela."""

    source: str
    source_month: str
    source_url: str
    etag: str | None
    last_modified: datetime | None
    content_length: int | None
    file_sha256: str | None
    row_count: int | None
    schema_hash: str | None
    s3_path: str | None
    ingest_ts: str
    status: str  # aceito | rejeitado | mesmo_conteudo
    motivo: str | None
    registrado_em: datetime
    dag_run_id: str


def _executar(athena, sql: str, intervalo: float = 1.0) -> list[list[str | None]]:
    """Roda um comando no Athena, espera terminar e devolve as linhas do resultado (sem o cabeçalho)."""
    try:
        qid = athena.start_query_execution(QueryString=sql, WorkGroup=WORKGROUP)["QueryExecutionId"]
    except Exception as erro:
        if any(t in str(erro) for t in _ERROS_TRANSITORIOS):
            raise ErroTransitorio(f"Athena recusou por excesso de pedidos: {erro}") from erro
        raise

    while True:
        execucao = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
        estado = execucao["Status"]["State"]
        if estado in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(intervalo)

    if estado != "SUCCEEDED":
        motivo = execucao["Status"].get("StateChangeReason", "")
        if any(t in motivo for t in _ERROS_TRANSITORIOS):
            raise ErroTransitorio(f"Athena {estado}: {motivo}")
        raise RuntimeError(f"Athena {estado}: {motivo}\nSQL: {sql}")

    linhas = []
    for pagina in athena.get_paginator("get_query_results").paginate(QueryExecutionId=qid):
        for linha in pagina["ResultSet"]["Rows"]:
            linhas.append([dado.get("VarCharValue") for dado in linha["Data"]])
    return linhas[1:]  # a primeira linha é o cabeçalho


def _literal(valor) -> str:
    """Escreve um valor Python como literal SQL do Athena. Aspas simples viram duas (escape)."""
    if valor is None:
        return "NULL"
    if isinstance(valor, datetime):
        utc = valor.astimezone(timezone.utc) if valor.tzinfo else valor
        return f"TIMESTAMP '{utc.strftime('%Y-%m-%d %H:%M:%S.%f')}'"
    if isinstance(valor, int):
        return str(valor)
    return "'" + str(valor).replace("'", "''") + "'"


def ler_historico(athena, banco: str, source: str) -> dict[str, list[LinhaManifesto]]:
    """Todas as linhas da fonte, agrupadas por mês: {'2025-01': [LinhaManifesto, ...], ...}."""
    linhas = _executar(
        athena,
        f"SELECT source_month, ingest_ts, etag, file_sha256, status "
        f"FROM {banco}.ingestion_manifest WHERE source = {_literal(source)}",
    )
    por_mes: dict[str, list[LinhaManifesto]] = {}
    for mes, ingest_ts, etag, sha, status in linhas:
        por_mes.setdefault(mes, []).append(LinhaManifesto(ingest_ts, etag, sha, status))
    return por_mes


def proximo_mes_esperado(historico_por_mes: dict[str, list[LinhaManifesto]], primeiro_mes: str) -> str:
    """O mês seguinte ao mais recente que tem versão aceita. Sem nenhum aceito: o primeiro do recorte."""
    aceitos = [mes for mes, linhas in historico_por_mes.items() if any(l.status == "aceito" for l in linhas)]
    if not aceitos:
        return primeiro_mes
    ano, mes = map(int, max(aceitos).split("-"))
    ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    return f"{ano:04d}-{mes:02d}"


def registrar(athena, banco: str, registro: RegistroManifesto) -> bool:
    """Grava uma linha no manifesto. Devolve False se uma linha igual já existia (nada gravado).

    "Igual" = mesma fonte, mês, versão (ingest_ts), status e ETag. É o caso do retry depois de um
    INSERT que deu certo. Conferir e depois gravar é seguro aqui porque cada mês tem uma task só
    e a DAG roda um run por vez (max_active_runs=1): ninguém grava o mesmo mês no meio.
    """
    tabela = f"{banco}.ingestion_manifest"
    ja_existe = (
        f"SELECT count(*) FROM {tabela} "
        f"WHERE source = {_literal(registro.source)} AND source_month = {_literal(registro.source_month)} "
        f"AND ingest_ts = {_literal(registro.ingest_ts)} AND status = {_literal(registro.status)} "
        f"AND etag IS NOT DISTINCT FROM {_literal(registro.etag)}"
    )
    if int(_executar(athena, ja_existe)[0][0]) > 0:
        return False

    valores = ", ".join(_literal(getattr(registro, campo.name)) for campo in fields(registro))
    _executar(athena, f"INSERT INTO {tabela} VALUES ({valores})")
    return True
