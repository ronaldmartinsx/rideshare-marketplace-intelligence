"""Testes do contrato de schema (Fase 2, etapa 4).

Cada teste é um cenário da Aula 4. Os arquivos Parquet são pequenos e criados na hora,
com o mesmo schema que a TLC usa (conferido no arquivo real de 2025-01).
"""

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from include.ingestao.contrato import (
    calcular_schema_hash,
    carregar_contrato,
    contar_linhas,
    ler_colunas,
    validar,
)

# Schema real de 2025-01, como o pyarrow lê (large_string, int32, timestamp[us]...)
SCHEMA_2025 = pa.schema(
    [
        ("hvfhs_license_num", pa.large_string()),
        ("dispatching_base_num", pa.large_string()),
        ("originating_base_num", pa.large_string()),
        ("request_datetime", pa.timestamp("us")),
        ("on_scene_datetime", pa.timestamp("us")),
        ("pickup_datetime", pa.timestamp("us")),
        ("dropoff_datetime", pa.timestamp("us")),
        ("PULocationID", pa.int32()),
        ("DOLocationID", pa.int32()),
        ("trip_miles", pa.float64()),
        ("trip_time", pa.int64()),
        ("base_passenger_fare", pa.float64()),
        ("tolls", pa.float64()),
        ("bcf", pa.float64()),
        ("sales_tax", pa.float64()),
        ("congestion_surcharge", pa.float64()),
        ("airport_fee", pa.float64()),
        ("tips", pa.float64()),
        ("driver_pay", pa.float64()),
        ("shared_request_flag", pa.large_string()),
        ("shared_match_flag", pa.large_string()),
        ("access_a_ride_flag", pa.large_string()),
        ("wav_request_flag", pa.large_string()),
        ("wav_match_flag", pa.large_string()),
        ("cbd_congestion_fee", pa.float64()),
    ]
)


def schema_trocando(nome: str, tipo: pa.DataType | None) -> pa.Schema:
    """SCHEMA_2025 com uma coluna trocada de tipo (ou removida, se tipo=None)."""
    campos = []
    for campo in SCHEMA_2025:
        if campo.name != nome:
            campos.append(campo)
        elif tipo is not None:
            campos.append(pa.field(nome, tipo))
    return pa.schema(campos)


def gravar_parquet(caminho, schema: pa.Schema, linhas: int = 3) -> str:
    """Grava um Parquet de poucas linhas (todas nulas: aqui só o schema importa)."""
    tabela = pa.table({campo.name: pa.nulls(linhas, campo.type) for campo in schema}, schema=schema)
    pq.write_table(tabela, caminho)
    return str(caminho)


@pytest.fixture(scope="module")
def contrato():
    return carregar_contrato("tlc_hvfhv")


def test_arquivo_real_de_2025_cumpre_o_contrato(tmp_path, contrato):
    colunas = ler_colunas(gravar_parquet(tmp_path / "a.parquet", SCHEMA_2025))
    resultado = validar(colunas, contrato, "2025-01")
    assert resultado.status == "aceito"
    assert resultado.alertas == []


def test_maiusculas_viram_minusculas_e_large_string_vira_string(tmp_path):
    colunas = ler_colunas(gravar_parquet(tmp_path / "a.parquet", SCHEMA_2025))
    assert colunas["pulocationid"] == "int"
    assert colunas["hvfhs_license_num"] == "string"
    assert colunas["pickup_datetime"] == "timestamp"
    assert "PULocationID" not in colunas


def test_contagem_de_linhas_vem_do_rodape(tmp_path):
    assert contar_linhas(gravar_parquet(tmp_path / "a.parquet", SCHEMA_2025, linhas=7)) == 7


def test_2024_sem_cbd_e_normal(tmp_path, contrato):
    """Antes de 2025-01, a falta da coluna do CBD está prevista no contrato (desde: 2025-01)."""
    schema = schema_trocando("cbd_congestion_fee", None)
    resultado = validar(ler_colunas(gravar_parquet(tmp_path / "a.parquet", schema)), contrato, "2024-06")
    assert resultado.status == "aceito"
    assert resultado.alertas == []


def test_2025_sem_cbd_alerta_coluna_faltante(tmp_path, contrato):
    schema = schema_trocando("cbd_congestion_fee", None)
    resultado = validar(ler_colunas(gravar_parquet(tmp_path / "a.parquet", schema)), contrato, "2025-03")
    assert resultado.status == "aceito"
    assert resultado.colunas_faltantes == ["cbd_congestion_fee"]


def test_coluna_nova_alerta_mas_aceita(tmp_path, contrato):
    schema = SCHEMA_2025.append(pa.field("surge_multiplier", pa.float64()))
    resultado = validar(ler_colunas(gravar_parquet(tmp_path / "a.parquet", schema)), contrato, "2026-09")
    assert resultado.status == "aceito"
    assert resultado.colunas_novas == ["surge_multiplier"]
    assert "coluna nova: surge_multiplier" in resultado.motivo


def test_tipo_diferente_rejeita(tmp_path, contrato):
    schema = schema_trocando("trip_miles", pa.large_string())
    resultado = validar(ler_colunas(gravar_parquet(tmp_path / "a.parquet", schema)), contrato, "2026-09")
    assert resultado.status == "rejeitado"
    assert resultado.tipos_diferentes == ["trip_miles esperado double, veio string"]


def test_int64_como_em_2019_rejeita(tmp_path, contrato):
    """O caso real de 2019/2022: PULocationID em INT64, e a tabela da Bronze declara int."""
    schema = schema_trocando("PULocationID", pa.int64())
    resultado = validar(ler_colunas(gravar_parquet(tmp_path / "a.parquet", schema)), contrato, "2025-01")
    assert resultado.status == "rejeitado"


def test_tipo_nulo_e_compativel_mas_gera_alerta_de_qualidade(tmp_path, contrato):
    """O caso real de 2019: airport_fee inteira vazia, com tipo null."""
    schema = schema_trocando("airport_fee", pa.null())
    resultado = validar(ler_colunas(gravar_parquet(tmp_path / "a.parquet", schema)), contrato, "2025-01")
    assert resultado.status == "aceito"
    assert resultado.colunas_tipo_nulo == ["airport_fee"]


def test_hash_ignora_a_ordem_e_muda_com_o_tipo():
    a = {"x": "int", "y": "string"}
    assert calcular_schema_hash(a) == calcular_schema_hash({"y": "string", "x": "int"})
    assert calcular_schema_hash(a) != calcular_schema_hash({"x": "bigint", "y": "string"})


def test_regra_com_valor_invalido_e_erro_do_contrato(contrato, monkeypatch, tmp_path):
    import include.ingestao.contrato as modulo

    (tmp_path / "ruim.yml").write_text(
        "fonte: ruim\nversao_contrato: 1\ncolunas: []\nregras:\n  tipo_diferente: ignorar\n"
    )
    monkeypatch.setattr(modulo, "PASTA_CONTRATOS", tmp_path)
    with pytest.raises(ValueError, match="tipo_diferente"):
        modulo.carregar_contrato("ruim")
