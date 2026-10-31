"""Testes da regra de pendência da dbt_build (Fase 3, etapa 8).

Um teste por linha da tabela de cenários desenhada pelo Ronald (25/10/2026), mais a ordem dos
meses e o caso dev × prod. Rodar: cd airflow && astro dev pytest tests/test_dbt_construcao.py
"""

from include.dbt_construcao import (
    MOTIVO_FORCADO,
    MOTIVO_MANIFESTO,
    Construcao,
    decidir_mes,
    planejar_construcao,
)

# Versões (ingest_ts) usadas nos cenários
TLC_A = "20261012T230806"
TLC_B = "20261101T090000"
CLIMA_C = "20261012T231500"
CLIMA_D = "20261101T091500"

CONSTRUIDO_A_C = Construcao(ingest_ts_tlc=TLC_A, ingest_ts_clima=CLIMA_C)


# ---------------------------------------------------------------- decidir_mes: a tabela

def test_linha_1_nunca_construido_e_construido_pelo_manifesto():
    decisao = decidir_mes("2025-03", TLC_A, CLIMA_C, ultima_construcao=None, forcado=False)
    assert decisao.construir and decisao.motivo == MOTIVO_MANIFESTO


def test_linha_2_sem_clima_espera_sem_alarme():
    """O clima chega logo depois e dispara a dbt_build de novo: não é erro."""
    decisao = decidir_mes("2025-03", TLC_A, None, ultima_construcao=None, forcado=False)
    assert not decisao.construir
    assert not decisao.pedido_nao_atendido
    assert decisao.motivo == "sem versão vigente de clima na Bronze"


def test_linha_3_ja_construido_com_as_versoes_vigentes_e_pulado():
    decisao = decidir_mes("2025-03", TLC_A, CLIMA_C, CONSTRUIDO_A_C, forcado=False)
    assert not decisao.construir and not decisao.pedido_nao_atendido


def test_linha_4_tlc_nova_e_construida_pelo_manifesto():
    decisao = decidir_mes("2025-03", TLC_B, CLIMA_C, CONSTRUIDO_A_C, forcado=False)
    assert decisao.construir and decisao.motivo == MOTIVO_MANIFESTO


def test_linha_5_clima_novo_e_construido_pelo_manifesto():
    decisao = decidir_mes("2025-03", TLC_A, CLIMA_D, CONSTRUIDO_A_C, forcado=False)
    assert decisao.construir and decisao.motivo == MOTIVO_MANIFESTO


def test_linha_6_em_dia_mas_forcado_e_construido_como_forcado():
    """O código do dbt mudou: manifesto e registro batem, só o pedido manual reconstrói."""
    decisao = decidir_mes("2025-03", TLC_A, CLIMA_C, CONSTRUIDO_A_C, forcado=True)
    assert decisao.construir and decisao.motivo == MOTIVO_FORCADO


def test_linha_7_forcado_sem_clima_e_pedido_nao_atendido():
    decisao = decidir_mes("2025-03", TLC_A, None, ultima_construcao=None, forcado=True)
    assert not decisao.construir and decisao.pedido_nao_atendido


def test_linha_8_forcado_sem_nada_e_pedido_nao_atendido():
    """O caso do 2205-01 digitado por engano."""
    decisao = decidir_mes("2205-01", None, None, ultima_construcao=None, forcado=True)
    assert not decisao.construir and decisao.pedido_nao_atendido
    assert decisao.motivo == "sem versão vigente de TLC e clima na Bronze"


def test_manifesto_tem_precedencia_sobre_forcado():
    """Pergunta 2: TLC nova E forçado. Constrói uma vez, e o registro conta que o dado mudou."""
    decisao = decidir_mes("2025-03", TLC_B, CLIMA_C, CONSTRUIDO_A_C, forcado=True)
    assert decisao.construir and decisao.motivo == MOTIVO_MANIFESTO


# ---------------------------------------------------------------- planejar_construcao

def test_meses_saem_do_mais_antigo_para_o_mais_novo():
    """O gate de um mês compara com os 3 anteriores: eles precisam vir antes."""
    vigentes = {"2025-02": TLC_A, "2024-12": TLC_A, "2025-01": TLC_A}
    clima = dict.fromkeys(vigentes, CLIMA_C)
    decisoes = planejar_construcao(vigentes, clima, construidos={}, forcar_meses=[])
    assert [d.mes for d in decisoes] == ["2024-12", "2025-01", "2025-02"]


def test_mes_forcado_que_nao_existe_no_manifesto_tambem_e_decidido():
    """Sem isto, o 2205-01 sumiria da lista e o pedido passaria em silêncio."""
    decisoes = planejar_construcao({"2025-01": TLC_A}, {"2025-01": CLIMA_C}, {}, forcar_meses=["2205-01"])
    assert [(d.mes, d.pedido_nao_atendido) for d in decisoes] == [("2025-01", False), ("2205-01", True)]


def test_dev_avalia_so_meses_ja_construidos_e_forcados():
    """Dev é uma amostra: os outros meses do manifesto nem entram na lista."""
    vigentes = {"2025-01": TLC_B, "2025-02": TLC_A, "2025-03": TLC_A}
    clima = dict.fromkeys(vigentes, CLIMA_C)
    construidos_em_dev = {"2025-01": CONSTRUIDO_A_C}  # construído com A; a vigente agora é B
    decisoes = planejar_construcao(vigentes, clima, construidos_em_dev, ["2025-03"],
                                   somente_meses_conhecidos=True)
    # 2025-01 acompanha o manifesto; 2025-03 entra por ter sido forçado; 2025-02 fica fora de dev
    assert [(d.mes, d.motivo) for d in decisoes] == [("2025-01", MOTIVO_MANIFESTO), ("2025-03", MOTIVO_MANIFESTO)]


def test_construido_em_dev_continua_pendente_em_prod():
    """Pergunta 3: a DAG passa o registro JÁ filtrado pelo ambiente; em prod, dev não aparece."""
    construidos_em_prod = {}  # 2026-05 só tem linha de dev no registro
    decisoes = planejar_construcao({"2026-05": TLC_A}, {"2026-05": CLIMA_C}, construidos_em_prod, [])
    assert decisoes[0].construir and decisoes[0].motivo == MOTIVO_MANIFESTO
