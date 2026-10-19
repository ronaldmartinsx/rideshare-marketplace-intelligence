"""Testes do clima: contrato e JSON canônico (Fase 2, etapa 9)."""

import copy

import pytest

from include.ingestao.contrato import carregar_contrato, horas_esperadas_clima, validar_clima
from include.ingestao.fonte_open_meteo import canonico, janela_do_mes, url_do_mes


def resposta_real(mes="2026-08", horas=None):
    """Uma resposta no formato real da API (conferido em 18/10/2026), com valores inventados."""
    horas = horas or horas_esperadas_clima(mes)
    return {
        "latitude": 40.808434, "longitude": -74.0199, "generationtime_ms": 0.219,
        "utc_offset_seconds": 0, "timezone": "GMT", "timezone_abbreviation": "GMT", "elevation": 40.0,
        "hourly_units": {"time": "iso8601", "temperature_2m": "°C", "precipitation": "mm",
                         "rain": "mm", "snowfall": "cm", "wind_speed_10m": "km/h"},
        "hourly": {"time": [f"h{i}" for i in range(horas)],
                   **{v: [1.0] * horas for v in ["temperature_2m", "precipitation", "rain",
                                                  "snowfall", "wind_speed_10m"]}},
    }


@pytest.fixture(scope="module")
def contrato():
    return carregar_contrato("open_meteo")


def test_janela_inclui_o_dia_1_seguinte_e_vira_o_ano():
    assert janela_do_mes("2026-08") == ("2026-08-01", "2026-09-01")
    assert janela_do_mes("2025-12") == ("2025-12-01", "2026-01-01")
    assert horas_esperadas_clima("2026-08") == 768  # 32 dias, como a resposta real


def test_url_pede_em_utc():
    assert "timezone=GMT" in url_do_mes("2026-08") and "end_date=2026-09-01" in url_do_mes("2026-08")


def test_canonico_ignora_o_campo_volatil_e_a_ordem_das_chaves():
    a = resposta_real()
    b = copy.deepcopy(a)
    b["generationtime_ms"] = 99.9  # outro pedido, outro tempo de servidor
    b = dict(reversed(list(b.items())))  # chaves em outra ordem
    assert canonico(a) == canonico(b)
    assert b"generationtime_ms" not in canonico(a)
    assert b"\n" not in canonico(a)  # uma linha só, para o Athena


def test_resposta_real_cumpre_o_contrato(contrato):
    resultado = validar_clima(resposta_real(), contrato, "2026-08")
    assert resultado.status == "aceito" and resultado.alertas == []


def test_fevereiro_bissexto_tem_horas_proprias(contrato):
    assert horas_esperadas_clima("2028-02") == 30 * 24
    assert validar_clima(resposta_real("2028-02"), contrato, "2028-02").status == "aceito"


def test_unidade_diferente_rejeita(contrato):
    dados = resposta_real()
    dados["hourly_units"]["temperature_2m"] = "°F"
    resultado = validar_clima(dados, contrato, "2026-08")
    assert resultado.status == "rejeitado"
    assert "temperature_2m esperado °C, veio °F" in resultado.motivo


def test_horas_faltando_rejeita(contrato):
    assert validar_clima(resposta_real(horas=700), contrato, "2026-08").status == "rejeitado"


def test_ponto_da_grade_diferente_rejeita(contrato):
    dados = resposta_real()
    dados["latitude"] = 40.70
    assert validar_clima(dados, contrato, "2026-08").status == "rejeitado"


def test_variavel_faltante_rejeita_e_nova_alerta(contrato):
    sem_vento = resposta_real()
    del sem_vento["hourly"]["wind_speed_10m"]
    assert validar_clima(sem_vento, contrato, "2026-08").status == "rejeitado"

    com_umidade = resposta_real()
    com_umidade["hourly"]["relative_humidity_2m"] = [50.0] * 768
    com_umidade["hourly_units"]["relative_humidity_2m"] = "%"
    resultado = validar_clima(com_umidade, contrato, "2026-08")
    assert resultado.status == "aceito" and resultado.colunas_novas == ["relative_humidity_2m"]


def test_variavel_toda_nula_e_alerta_de_qualidade(contrato):
    dados = resposta_real()
    dados["hourly"]["snowfall"] = [None] * 768
    resultado = validar_clima(dados, contrato, "2026-08")
    assert resultado.status == "aceito" and resultado.colunas_tipo_nulo == ["snowfall"]
