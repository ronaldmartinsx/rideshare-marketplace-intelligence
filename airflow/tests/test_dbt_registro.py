"""Testes da leitura do manifesto e do registro de construção (Fase 3, etapa 8).

O Athena é substituído por um "Athena de mentira", como em tests/ingestao/test_manifesto.py:
guarda o SQL recebido e devolve respostas prontas. A prova contra o Athena real é a dbt_build_dev.
Rodar: cd airflow && astro dev pytest tests/test_dbt_registro.py
"""

from datetime import datetime, timezone

import pytest

from include.dbt_construcao import Construcao
from include.dbt_registro import (
    gravar_construcao,
    ler_construidos,
    ler_vigentes,
    meses_registrados_desde,
    versoes_na_silver,
)


class AthenaDeMentira:
    """Responde cada consulta com a próxima resposta da fila e guarda o SQL recebido."""

    def __init__(self, respostas):
        self.respostas, self.sqls = list(respostas), []

    def start_query_execution(self, QueryString, WorkGroup):
        assert WorkGroup == "rideshare"
        self.sqls.append(QueryString)
        return {"QueryExecutionId": str(len(self.sqls))}

    def get_query_execution(self, QueryExecutionId):
        return {"QueryExecution": {"Status": {"State": "SUCCEEDED"}}}

    def get_paginator(self, nome):
        linhas = self.respostas.pop(0) if self.respostas else []
        pagina = {"ResultSet": {"Rows": [{"Data": [{"VarCharValue": v} if v is not None else {} for v in l]}
                                         for l in [["cabecalho"]] + linhas]}}
        return type("P", (), {"paginate": lambda self, **_: [pagina]})()


def test_ler_vigentes_separa_tlc_e_clima():
    athena = AthenaDeMentira([[
        ["tlc_hvfhv", "2025-01", "20261012T230806"],
        ["open_meteo", "2025-01", "20261012T231500"],
        ["tlc_hvfhv", "2025-02", "20261012T232000"],  # clima de fevereiro ainda não chegou
    ]])
    tlc, clima = ler_vigentes(athena)
    assert tlc == {"2025-01": "20261012T230806", "2025-02": "20261012T232000"}
    assert clima == {"2025-01": "20261012T231500"}


def test_ler_construidos_filtra_o_ambiente_no_sql():
    athena = AthenaDeMentira([[["2025-01", "20261012T230806", "20261012T231500"]]])
    construidos = ler_construidos(athena, "prod")
    assert construidos == {"2025-01": Construcao("20261012T230806", "20261012T231500")}
    assert "ambiente = 'prod'" in athena.sqls[0]


def test_versoes_na_silver_le_o_banco_do_ambiente():
    athena = AthenaDeMentira([[["20261012T230806", "20261012T231500"]]])
    assert versoes_na_silver(athena, "dev", "2025-01") == Construcao("20261012T230806", "20261012T231500")
    assert "dev_silver.stg_tlc__hvfhv_trips" in athena.sqls[0]
    assert "dev_silver.stg_open_meteo__weather_hourly" in athena.sqls[0]


def test_versoes_na_silver_sem_o_mes_falha_alto():
    """Sem o mês numa staging, gravar o registro mentiria que o mês foi construído."""
    athena = AthenaDeMentira([[["20261012T230806", None]]])
    with pytest.raises(RuntimeError, match="sem o mês 2025-01"):
        versoes_na_silver(athena, "prod", "2025-01")


def test_gravar_construcao_grava_uma_linha():
    athena = AthenaDeMentira([[["0"]], []])  # conferência: nenhuma linha igual; depois o INSERT
    construcao = Construcao("20261012T230806", "20261012T231500")
    assert gravar_construcao(athena, "prod", "2025-01", construcao, "manifesto", "manual__x") is True
    insert = athena.sqls[1]
    assert insert.startswith("INSERT INTO controle.dbt_meses_construidos VALUES ('prod', '2025-01',")
    assert "'manifesto', TIMESTAMP '" in insert and insert.endswith("'manual__x')")


def test_gravar_construcao_no_retry_nao_duplica():
    athena = AthenaDeMentira([[["1"]]])  # a linha já foi gravada pela tentativa anterior
    construcao = Construcao("20261012T230806", "20261012T231500")
    assert gravar_construcao(athena, "prod", "2025-01", construcao, "manifesto", "manual__x") is False
    assert len(athena.sqls) == 1  # só a conferência; nenhum INSERT


def test_meses_registrados_desde_o_inicio_do_run():
    athena = AthenaDeMentira([[["2025-01"], ["2025-02"]]])
    inicio = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)
    assert meses_registrados_desde(athena, "prod", inicio) == ["2025-01", "2025-02"]
    assert "construido_em >= TIMESTAMP '2026-10-25 09:00:00.000000'" in athena.sqls[0]
