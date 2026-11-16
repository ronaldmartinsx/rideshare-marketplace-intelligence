"""O backtest walk-forward: roda as rodadas e compara o modelo com o baseline (Fase 5, passo 6).

Junta as outras peças sem reimplementar nenhuma: janelas.py diz quais cortes treinam, dados.py lê,
modelo.py treina e prevê, e o baseline vem pronto do SQL.

A regra inviolável da comparação: modelo e baseline são avaliados nas MESMAS LINHAS, da MESMA
rodada, com a MESMA fórmula. Comparar o modelo na rodada 3 com o baseline na rodada 5 não quer
dizer nada, e é um erro fácil quando os dois são calculados em lugares diferentes.
"""

from __future__ import annotations

import time
from typing import Sequence

import numpy as np
import pandas as pd

from include.ml import config, dados, janelas, modelo


def wape(real: pd.Series | np.ndarray, previsto: pd.Series | np.ndarray) -> float:
    """WAPE em percentual: soma dos erros absolutos ÷ soma do real, vezes 100.

    MESMA fórmula do ml_wape_baseline.sql, escrito pelo Ronald no passo 4 — razão das somas, nunca
    média das razões. Se este número e o da tabela SQL divergirem na mesma rodada, uma das duas
    implementações está errada, e o backtest confere isso explicitamente.
    """
    real = np.asarray(real, dtype="float64")
    previsto = np.asarray(previsto, dtype="float64")
    denominador = real.sum()
    if denominador == 0:
        return float("nan")
    return 100.0 * np.abs(real - previsto).sum() / denominador


def vies(real: pd.Series | np.ndarray, previsto: pd.Series | np.ndarray) -> float:
    """Erro COM sinal, em percentual. Coluna inventada pelo Ronald no passo 4.

    O WAPE é absoluto e não distingue "errar sempre para cima" de "errar para os dois lados". Sem
    o viés, 14% de WAPE não diz se o problema é calibração (fácil) ou dispersão (difícil).
    """
    real = np.asarray(real, dtype="float64")
    previsto = np.asarray(previsto, dtype="float64")
    denominador = real.sum()
    if denominador == 0:
        return float("nan")
    return 100.0 * (previsto.sum() - real.sum()) / denominador


def rodar_uma(
    features: pd.DataFrame,
    rodada: janelas.Rodada,
    ambiente: str,
    sessao,
    n_arvores: int = config.N_ARVORES,
    salvar_modelo: bool = True,
) -> dict:
    """Uma rodada completa: treina, prevê, compara com o baseline e devolve as métricas.

    `features` é a tabela inteira, lida UMA vez: o recorte por rodada é feito em memória, para não
    pagar 7 leituras no Athena.
    """
    treino = dados.recortar(features, rodada.cortes_treino, somente_com_alvo=True)
    # Na rodada de produção o alvo não existe: é justamente o que se quer descobrir.
    teste = dados.recortar(features, [rodada.corte], somente_com_alvo=rodada.avaliavel)

    inicio = time.perf_counter()
    booster = modelo.treinar(treino, n_arvores=n_arvores)
    segundos_treino = time.perf_counter() - inicio

    previsao = modelo.prever(booster, teste)

    versao = modelo.versao(rodada, ambiente)
    caminho = modelo.salvar(booster, sessao, versao) if salvar_modelo else None

    resultado = {
        "tipo": rodada.tipo,
        "corte": rodada.corte,
        "mes_alvo": rodada.mes_alvo,
        "cortes_treino": len(rodada.cortes_treino),
        "linhas_treino": len(treino),
        "linhas_teste": len(teste),
        "segundos_treino": segundos_treino,
        "versao_modelo": versao,
        "caminho_modelo": caminho,
        "wape_modelo": None,
        "wape_baseline": None,
        "vies_modelo": None,
        "vies_baseline": None,
        "previsao": previsao,
        "teste": teste,
    }

    if not rodada.avaliavel:
        return resultado  # produção: não há gabarito para comparar

    real = teste[config.COLUNA_ALVO]
    resultado["wape_modelo"] = wape(real, previsao)
    resultado["vies_modelo"] = vies(real, previsao)

    # O baseline vem PRONTO do SQL, filtrado no mesmo corte, e é alinhado por chave — nunca por
    # posição. Alinhar por posição é o jeito silencioso de comparar linhas diferentes.
    base = dados.ler_baseline(ambiente, sessao, cortes=[rodada.corte])
    base = base.loc[base["tem_alvo"]]
    juntos = teste[["hora_alvo", "zona_id", config.COLUNA_ALVO]].merge(
        base[["hora_alvo", "zona_id", "previsao_baseline"]],
        on=["hora_alvo", "zona_id"],
        how="inner",
        validate="one_to_one",
    )
    if len(juntos) != len(teste):
        raise ValueError(
            f"baseline não cobre o teste: {len(juntos)} de {len(teste)} linhas casaram"
        )

    resultado["wape_baseline"] = wape(juntos[config.COLUNA_ALVO], juntos["previsao_baseline"])
    resultado["vies_baseline"] = vies(juntos[config.COLUNA_ALVO], juntos["previsao_baseline"])
    resultado["importancia"] = modelo.importancia(booster)
    return resultado


def rodar(
    ambiente: str,
    sessao,
    rodadas: int = janelas.RODADAS_PADRAO,
    incluir_producao: bool = False,
    n_arvores: int = config.N_ARVORES,
    salvar_modelo: bool = True,
    features: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, list[dict]]:
    """O backtest inteiro. Devolve (tabela de métricas, resultados completos).

    A tabela de features é lida UMA vez e recortada em memória para todas as rodadas.
    """
    if features is None:
        features = dados.ler_features(ambiente, sessao)

    avaliaveis = sorted(features.loc[features["tem_alvo"], "mes_corte"].unique().tolist())
    sem_alvo = sorted(features.loc[~features["tem_alvo"], "mes_corte"].unique().tolist())
    corte_producao = sem_alvo[-1] if (incluir_producao and sem_alvo) else None

    planejadas = janelas.planejar_rodadas(avaliaveis, corte_producao, rodadas=rodadas)
    if not planejadas:
        raise ValueError("nenhuma rodada planejada: faltam cortes com gabarito")

    resultados = [
        rodar_uma(features, r, ambiente, sessao, n_arvores=n_arvores, salvar_modelo=salvar_modelo)
        for r in planejadas
    ]

    colunas = ["tipo", "corte", "mes_alvo", "cortes_treino", "linhas_treino", "linhas_teste",
               "segundos_treino", "wape_modelo", "wape_baseline", "vies_modelo", "vies_baseline",
               "versao_modelo"]
    tabela = pd.DataFrame([{c: r[c] for c in colunas} for r in resultados])
    tabela["ganho_pp"] = tabela["wape_baseline"] - tabela["wape_modelo"]
    return tabela, resultados
