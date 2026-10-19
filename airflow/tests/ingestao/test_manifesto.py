"""Testes da leitura e escrita do manifesto (Fase 2, etapa 6).

O Athena é substituído por um "Athena de mentira" que guarda o SQL recebido e devolve respostas
prontas. A prova contra o Athena real (teste_controle) é feita à parte.
"""

from datetime import datetime, timezone

import pytest

from include.ingestao.decisao import LinhaManifesto
from include.ingestao.fonte_http import ErroTransitorio
from include.ingestao.manifesto import (
    RegistroManifesto,
    _literal,
    ler_historico,
    proximo_mes_esperado,
    registrar,
)


class AthenaDeMentira:
    """Responde cada consulta com a próxima resposta da fila e guarda o SQL recebido."""

    def __init__(self, respostas, estado="SUCCEEDED", motivo=""):
        self.respostas, self.estado, self.motivo, self.sqls = list(respostas), estado, motivo, []

    def start_query_execution(self, QueryString, WorkGroup):
        assert WorkGroup == "rideshare"
        self.sqls.append(QueryString)
        return {"QueryExecutionId": str(len(self.sqls))}

    def get_query_execution(self, QueryExecutionId):
        return {"QueryExecution": {"Status": {"State": self.estado, "StateChangeReason": self.motivo}}}

    def get_paginator(self, nome):
        linhas = self.respostas.pop(0) if self.respostas else []
        pagina = {"ResultSet": {"Rows": [{"Data": [{"VarCharValue": v} if v is not None else {} for v in l]}
                                         for l in [["cabecalho"]] + linhas]}}
        return type("P", (), {"paginate": lambda self, **_: [pagina]})()


def registro(**muda):
    base = dict(
        source="tlc_hvfhv", source_month="2026-08", source_url="https://x/2026-08.parquet",
        etag='"abc-30"', last_modified=datetime(2026, 10, 1, 13, 38, 15, tzinfo=timezone.utc),
        content_length=502392134, file_sha256="f" * 64, row_count=20000000, schema_hash="6fa1",
        s3_path="s3://b/k", ingest_ts="20261018T070000", status="aceito", motivo=None,
        registrado_em=datetime(2026, 10, 18, 7, 1, tzinfo=timezone.utc), dag_run_id="scheduled__x",
    )
    base.update(muda)
    return RegistroManifesto(**base)


def test_literal_escapa_aspas_e_formata_tipos():
    assert _literal(None) == "NULL"
    assert _literal(42) == "42"
    assert _literal("d'água") == "'d''água'"
    assert _literal('"etag-com-aspas-duplas"') == "'\"etag-com-aspas-duplas\"'"
    assert _literal(datetime(2025, 4, 23, 16, 30, 36, tzinfo=timezone.utc)) == "TIMESTAMP '2025-04-23 16:30:36.000000'"


def test_ler_historico_agrupa_por_mes():
    athena = AthenaDeMentira([[["2025-01", "20261012T230806", '"A"', "s1", "aceito"],
                               ["2025-01", "20261012T230806", '"B"', "s1", "mesmo_conteudo"],
                               ["2026-08", "20261018T070000", '"C"', "s2", "aceito"]]])
    historico = ler_historico(athena, "controle", "tlc_hvfhv")
    assert historico["2025-01"] == [LinhaManifesto("20261012T230806", '"A"', "s1", "aceito"),
                                    LinhaManifesto("20261012T230806", '"B"', "s1", "mesmo_conteudo")]
    assert len(historico["2026-08"]) == 1
    assert "FROM controle.ingestion_manifest WHERE source = 'tlc_hvfhv'" in athena.sqls[0]


def test_proximo_mes_esperado_vira_o_ano_e_ignora_rejeitados():
    historico = {"2025-12": [LinhaManifesto("t", "e", "s", "aceito")],
                 "2026-01": [LinhaManifesto("t", "e", "s", "rejeitado")]}
    assert proximo_mes_esperado(historico, "2024-01") == "2026-01"
    assert proximo_mes_esperado({}, "2024-01") == "2024-01"


def test_registrar_grava_quando_nao_existe():
    athena = AthenaDeMentira([[["0"]], []])
    assert registrar(athena, "controle", registro()) is True
    assert athena.sqls[1].startswith("INSERT INTO controle.ingestion_manifest VALUES ('tlc_hvfhv', '2026-08'")


def test_registrar_no_retry_nao_duplica():
    athena = AthenaDeMentira([[["1"]]])
    assert registrar(athena, "controle", registro()) is False
    assert len(athena.sqls) == 1  # só a conferência; nenhum INSERT


def test_conflito_de_commit_do_iceberg_e_transitorio():
    athena = AthenaDeMentira([], estado="FAILED", motivo="ICEBERG_COMMIT_ERROR: Failed to commit")
    with pytest.raises(ErroTransitorio):
        ler_historico(athena, "controle", "tlc_hvfhv")


def test_erro_de_sql_falha_alto():
    athena = AthenaDeMentira([], estado="FAILED", motivo="SYNTAX_ERROR: line 1:1")
    with pytest.raises(RuntimeError, match="SYNTAX_ERROR"):
        ler_historico(athena, "controle", "tlc_hvfhv")
