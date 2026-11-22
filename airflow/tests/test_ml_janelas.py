"""Testes da regra das rodadas do backtest (Fase 5, passo 5).

Um teste por linha da tabela de cenários combinada com o Ronald (15/11/2026), mais o teste que prova
a garantia antivazamento e a virada de ano do próximo mês.
Rodar: cd airflow && astro dev pytest tests/test_ml_janelas.py
"""

from include.ml.janelas import (
    TIPO_BACKTEST,
    TIPO_PRODUCAO,
    Rodada,
    planejar_rodadas,
    proximo_mes,
)


def cortes_de(primeiro: str, ultimo: str) -> list[str]:
    """Todos os meses de primeiro a ultimo, inclusive. Só para montar os cenários."""
    meses, atual = [], primeiro
    while atual <= ultimo:
        meses.append(atual)
        atual = proximo_mes(atual)
    return meses


# Produção: cortes de 2024-01 a 2026-08 têm gabarito (o alvo vai até 2026-09, último mês com dado).
# O corte 2026-09 prevê 2026-10 e é o de produção.
AVALIAVEIS_PROD = cortes_de("2024-01", "2026-08")
CORTE_PRODUCAO = "2026-09"


# ---------- Cenário 1: 32 cortes avaliáveis, 6 rodadas ----------

def test_cenario_1_pega_as_ultimas_seis_rodadas():
    assert len(AVALIAVEIS_PROD) == 32

    rodadas = planejar_rodadas(AVALIAVEIS_PROD, rodadas=6)

    assert len(rodadas) == 6
    assert [r.corte for r in rodadas] == [
        "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08",
    ]
    # O mês previsto é sempre o seguinte ao corte (a tabela da Aula 3)
    assert [r.mes_alvo for r in rodadas] == [
        "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09",
    ]


def test_cenario_1_cada_rodada_treina_com_todos_os_anteriores():
    rodadas = planejar_rodadas(AVALIAVEIS_PROD, rodadas=6)

    # A primeira rodada (corte 2026-03) treina com os 26 cortes de 2024-01 a 2026-02
    assert rodadas[0].cortes_treino == tuple(cortes_de("2024-01", "2026-02"))
    # A última (corte 2026-08) treina com os 31 anteriores
    assert rodadas[-1].cortes_treino == tuple(cortes_de("2024-01", "2026-07"))
    # A janela de treino cresce a cada rodada: é o "walk-forward"
    assert [len(r.cortes_treino) for r in rodadas] == [26, 27, 28, 29, 30, 31]


# ---------- Cenário 2: o corte de produção ----------

def test_cenario_2_producao_treina_com_tudo_e_nao_e_avaliavel():
    rodadas = planejar_rodadas(AVALIAVEIS_PROD, corte_producao=CORTE_PRODUCAO, rodadas=6)

    assert len(rodadas) == 7  # 6 de backtest + 1 de produção
    producao = rodadas[-1]

    assert producao.tipo == TIPO_PRODUCAO
    assert producao.corte == "2026-09"
    assert producao.mes_alvo == "2026-10"      # o mês que ainda não aconteceu
    assert producao.cortes_treino == tuple(AVALIAVEIS_PROD)  # usa os 32, inclusive os do backtest
    assert producao.avaliavel is False


def test_cenario_2_rodadas_de_backtest_sao_avaliaveis():
    rodadas = planejar_rodadas(AVALIAVEIS_PROD, corte_producao=CORTE_PRODUCAO, rodadas=6)

    assert all(r.avaliavel for r in rodadas if r.tipo == TIPO_BACKTEST)
    assert sum(1 for r in rodadas if r.avaliavel) == 6


# ---------- Cenário 3: menos cortes do que rodadas pedidas (o caso do dev) ----------

def test_cenario_3_dev_devolve_o_que_couber_sem_inventar():
    # dev é amostra de 4 meses (spec 11.2): cortes 2026-02 a 2026-05, e só 3 têm gabarito
    avaliaveis_dev = ["2026-02", "2026-03", "2026-04"]

    rodadas = planejar_rodadas(avaliaveis_dev, rodadas=6)

    # Pediu 6, só 2 são possíveis: o corte 2026-02 cai no cenário 4 (ver abaixo)
    assert len(rodadas) == 2
    assert [r.corte for r in rodadas] == ["2026-03", "2026-04"]


# ---------- Cenário 4: rodada sem nenhum corte de treino ----------

def test_cenario_4_descarta_rodada_sem_corte_de_treino():
    # O corte mais antigo nunca tem anterior: não se treina modelo com nada
    rodadas = planejar_rodadas(["2026-02", "2026-03"], rodadas=6)

    assert [r.corte for r in rodadas] == ["2026-03"]
    assert rodadas[0].cortes_treino == ("2026-02",)


def test_cenario_4_um_corte_sozinho_nao_gera_rodada():
    assert planejar_rodadas(["2026-02"], rodadas=6) == []


# ---------- Cenário 5: ordem da entrada não importa ----------

def test_cenario_5_ordena_e_remove_duplicata():
    baguncado = ["2026-04", "2026-02", "2026-04", "2026-03"]

    assert planejar_rodadas(baguncado, rodadas=6) == planejar_rodadas(
        ["2026-02", "2026-03", "2026-04"], rodadas=6
    )


# ---------- A GARANTIA ANTIVAZAMENTO ----------

def test_nenhum_corte_de_treino_alcanca_o_corte_da_rodada():
    """A prova da regra: treino só com cortes ESTRITAMENTE anteriores.

    Se um corte de treino fosse igual ou posterior ao corte da rodada, o modelo teria treinado com
    o mês que deveria adivinhar. Não daria exceção nem teste vermelho em nenhum outro lugar — daria
    um WAPE melhor. É por isso que esta garantia tem teste próprio.
    """
    rodadas = planejar_rodadas(AVALIAVEIS_PROD, corte_producao=CORTE_PRODUCAO, rodadas=6)

    for rodada in rodadas:
        for corte_treino in rodada.cortes_treino:
            assert corte_treino < rodada.corte, (
                f"rodada {rodada.corte} treinaria com {corte_treino}"
            )


def test_o_mes_alvo_do_treino_nunca_passa_do_corte_da_rodada():
    """A mesma garantia pelo outro lado: o ALVO de cada linha de treino já aconteceu no corte.

    O mês-alvo de um corte é o mês seguinte a ele. Treinar com o corte C-1 significa usar alvos do
    mês C, que já terminou quando se está parado no fim de C. Nada do futuro entra.
    """
    rodadas = planejar_rodadas(AVALIAVEIS_PROD, rodadas=6)

    for rodada in rodadas:
        for corte_treino in rodada.cortes_treino:
            assert proximo_mes(corte_treino) <= rodada.corte


# ---------- proximo_mes ----------

def test_proximo_mes_vira_o_ano():
    assert proximo_mes("2026-12") == "2027-01"


def test_proximo_mes_mantem_dois_digitos():
    assert proximo_mes("2026-01") == "2026-02"
    assert proximo_mes("2026-08") == "2026-09"
    assert proximo_mes("2026-09") == "2026-10"


def test_rodada_e_imutavel():
    """frozen=True: rodada planejada não pode ser alterada depois, por engano, no meio do backtest."""
    rodada = Rodada(tipo=TIPO_BACKTEST, corte="2026-03", mes_alvo="2026-04", cortes_treino=())

    try:
        rodada.corte = "2026-09"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("Rodada deveria ser imutável")
