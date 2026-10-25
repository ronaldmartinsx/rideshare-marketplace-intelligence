"""Testes da manutenção Iceberg (Fase 3, etapa 8, F12).

O Glue é substituído por um "Glue de mentira" com tabelas prontas.
Rodar: cd airflow && astro dev pytest tests/test_manutencao.py
"""

from include.manutencao import comandos, tabelas_iceberg


class GlueDeMentira:
    """Devolve as tabelas de cada banco; banco fora do dicionário não existe."""

    class exceptions:
        class EntityNotFoundException(Exception):
            pass

    def __init__(self, bancos):
        self.bancos = bancos

    def get_paginator(self, nome):
        assert nome == "get_tables"
        glue = self

        class Paginador:
            def paginate(self, DatabaseName):
                if DatabaseName not in glue.bancos:
                    raise glue.exceptions.EntityNotFoundException(DatabaseName)
                return [{"TableList": glue.bancos[DatabaseName]}]

        return Paginador()


def tabela(nome, tipo="ICEBERG"):
    return {"Name": nome, "Parameters": {"table_type": tipo}}


def test_so_tabelas_iceberg_e_sem_temporarias_do_dbt():
    glue = GlueDeMentira({
        "dev_silver": [
            tabela("int_trips_enriched"),
            tabela("stg_tlc__hvfhv_trips"),  # "__" do padrão de nome das stagings: entra
            tabela("int_trips_enriched__tmp_not_partitioned"),  # temporárias do dbt: ficam fora
            tabela("int_trips_enriched__dbt_tmp"),
            tabela("int_trips_enriched__bkp"),
            tabela("int_trips_enriched__ha"),
            {"Name": "uma_view", "Parameters": {}},  # view não é Iceberg
        ],
    })
    assert tabelas_iceberg(glue, ["dev_silver"]) == [
        {"tabela": "dev_silver.int_trips_enriched", "compactar": False},
        {"tabela": "dev_silver.stg_tlc__hvfhv_trips", "compactar": False},
    ]


def test_banco_que_ainda_nao_existe_e_ignorado():
    glue = GlueDeMentira({"controle": [tabela("ingestion_manifest", tipo="iceberg")]})
    assert tabelas_iceberg(glue, ["silver", "controle"]) == [
        {"tabela": "controle.ingestion_manifest", "compactar": True}
    ]


def test_controle_compacta_antes_de_limpar():
    assert comandos("controle.ingestion_manifest", compactar=True) == [
        "OPTIMIZE controle.ingestion_manifest REWRITE DATA USING BIN_PACK",
        "VACUUM controle.ingestion_manifest",
    ]


def test_tabela_do_dbt_so_limpa():
    assert comandos("silver.int_trips_enriched", compactar=False) == ["VACUUM silver.int_trips_enriched"]
