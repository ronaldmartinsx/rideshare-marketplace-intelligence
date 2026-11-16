"""Treino, previsão e versionamento do LightGBM (Fase 5, passo 5).

Módulo de ENTRADA E SAÍDA. A regra das rodadas está em janelas.py (pura), as escolhas de modelagem
em config.py e a leitura em dados.py.

O que este arquivo NÃO faz, de propósito:
- não decide quais cortes treinam (é janelas.py);
- não calcula o baseline nem o WAPE (é SQL, peças ✍️ do Ronald nos passos 3 e 4);
- não escolhe features nem parâmetros (é config.py).
Ele treina, prevê e guarda. Nada mais.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from include.ml import config


def treinar(treino: pd.DataFrame, n_arvores: int = config.N_ARVORES, params: dict | None = None):
    """Treina um LightGBM no recorte dado e devolve o Booster.

    Usa a API nativa (lgb.train + lgb.Dataset) em vez do embrulho estilo scikit-learn, por duas
    razões: o controle explícito das colunas categóricas e o acesso à importância das features.

    O alvo é qtd_corridas. As features são exatamente config.COLUNAS_FEATURE — e mes_corte e
    mes_alvo ficam FORA de propósito: deixariam o modelo decorar meses específicos, que nunca se
    repetem no futuro.
    """
    import lightgbm as lgb

    faltando = [c for c in config.COLUNAS_FEATURE if c not in treino.columns]
    if faltando:
        raise ValueError(f"faltam features no recorte de treino: {faltando}")

    x = treino[config.COLUNAS_FEATURE]
    y = treino[config.COLUNA_ALVO]

    if y.isna().any():
        # Linha sem gabarito não ensina nada; se chegou aqui, o recorte foi feito errado.
        raise ValueError("há alvo nulo no recorte de treino: use dados.recortar(somente_com_alvo=True)")

    conjunto = lgb.Dataset(
        x,
        label=y,
        # zona_id é int32 e PRECISA ser nomeada aqui: sem isso a árvore faria cortes do tipo
        # "zona_id <= 96", que não significam nada. As outras duas são dtype category e o LightGBM
        # as detectaria sozinho, mas ficam nomeadas para a intenção estar escrita.
        categorical_feature=config.CATEGORICAS_LIGHTGBM,
        free_raw_data=False,
    )

    return lgb.train({**config.PARAMS_LIGHTGBM, **(params or {})}, conjunto, num_boost_round=n_arvores)


def prever(booster, dados_: pd.DataFrame) -> np.ndarray:
    """A previsão para cada linha, na mesma ordem do DataFrame recebido.

    Nunca negativa: demanda abaixo de zero não existe, e o L1 pode devolver valor negativo numa
    zona de demanda quase nula. Cortar em zero é a única pós-correção aplicada, e ela só pode
    MELHORAR o WAPE, porque aproxima a previsão do mínimo possível do real.
    """
    cru = booster.predict(dados_[config.COLUNAS_FEATURE])
    return np.clip(cru, 0, None)


def importancia(booster) -> pd.DataFrame:
    """Quanto cada feature foi usada, para a análise do resultado.

    Usa ganho (quanto cada feature reduziu o erro) e não contagem de cortes: contagem favorece
    feature de muitos valores distintos, e aqui há uma com 262 (zona_id).
    """
    return (
        pd.DataFrame(
            {
                "feature": booster.feature_name(),
                "ganho": booster.feature_importance(importance_type="gain"),
                "cortes": booster.feature_importance(importance_type="split"),
            }
        )
        .sort_values("ganho", ascending=False)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Versionamento (spec 9.1 e Aula 3)
# ---------------------------------------------------------------------------

def versao(rodada, ambiente: str) -> str:
    """Identificador da versão do modelo: ambiente, corte da rodada e instante do treino.

    Sem isso, "o modelo piorou" não tem resposta: não se sabe se mudaram os dados, o código ou os
    parâmetros. É o terceiro membro da família do manifesto de ingestão (Fase 2) e do registro de
    construção do dbt (ADR 0016).
    """
    agora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{ambiente}__{rodada.tipo}__corte{rodada.corte}__{agora}"


def caminho_s3(versao_: str) -> str:
    """Onde o binário do modelo mora. S3, nunca Git: Git é para código, modelo é dado."""
    return f"s3://{config.BUCKET_MODELOS}/{config.PREFIXO_MODELOS}/{versao_}.txt"


def salvar(booster, sessao, versao_: str) -> str:
    """Grava o modelo no S3 e devolve o caminho.

    save_model() do LightGBM produz TEXTO, não binário opaco: dá para abrir e ler as árvores. Isso
    é bom para auditoria e péssimo para o tamanho, mas um modelo deste porte dá poucos MB.
    """
    caminho = caminho_s3(versao_)
    bucket, chave = caminho.removeprefix("s3://").split("/", 1)
    sessao.client("s3").put_object(
        Bucket=bucket,
        Key=chave,
        Body=booster.model_to_string().encode("utf-8"),
    )
    return caminho


def carregar(sessao, caminho: str):
    """Relê um modelo salvo, para prever sem treinar de novo."""
    import lightgbm as lgb

    bucket, chave = caminho.removeprefix("s3://").split("/", 1)
    corpo = sessao.client("s3").get_object(Bucket=bucket, Key=chave)["Body"].read()
    return lgb.Booster(model_str=corpo.decode("utf-8"))
