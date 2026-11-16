"""Gravação das tabelas ml_* na Gold (Fase 5, passo 6; spec 6.4 e 9.1).

Duas tabelas, com os grãos que a spec 6.4 define:
- ml_forecast_demanda   : hora-alvo × zona × execução → previsão, intervalo, versão do modelo
- ml_backtest_metricas  : execução × janela → WAPE do modelo E do baseline

Diferente das outras quatro tabelas da fase, estas NÃO são models dbt: a spec 9.1 manda o Python
gravar em `gold.ml_*` via awswrangler. A consequência honesta disso é que elas não aparecem no
`dbt docs` nem ganham testes do dbt — é o preço de o produtor ser o Python e não o SQL.

Modo `append`, e não `overwrite`, de propósito: o grão da spec inclui **execução**, então execuções
se acumulam e dá para comparar o resultado de hoje com o de um mês atrás. É a mesma ideia do
manifesto de ingestão (Fase 2) e do registro de construção do dbt (ADR 0016) — histórico em vez de
foto do último estado.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from include.ml import config

TABELA_FORECAST = "ml_forecast_demanda"
TABELA_METRICAS = "ml_backtest_metricas"

# Rascunho da escrita em Iceberg. Vai no bucket de resultados, que expira em 7 dias.
TEMP_PATH = "s3://rmartins-rideshare-athena-results/iceberg-temp/"


def nova_execucao() -> str:
    """Identificador da execução inteira do backtest. Liga as duas tabelas entre si."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _local(tabela: str) -> str:
    """Onde os arquivos da tabela moram. Prefixo = nome do banco (ADR 0013)."""
    return f"s3://{config.BUCKET_MODELOS}/gold/{tabela}/"


def _gravar(df: pd.DataFrame, tabela: str, ambiente: str, sessao, particoes: list[str]) -> int:
    import awswrangler as wr

    wr.athena.to_iceberg(
        df=df,
        database=config.BANCO[ambiente],
        table=tabela,
        table_location=_local(tabela),
        temp_path=TEMP_PATH,
        partition_cols=particoes,
        workgroup=config.WORKGROUP,  # o padrão da biblioteca é "primary", que não existe aqui
        mode="append",
        keep_files=False,
        boto3_session=sessao,
    )
    return len(df)


def montar_previsoes(resultados: list[dict], execucao: str) -> pd.DataFrame:
    """Uma linha por hora-alvo × zona × execução, de TODAS as rodadas.

    Guarda também as rodadas de backtest, e não só a de produção: é o que permite a página do Power
    BI mostrar previsto contra real nos meses que já aconteceram. Sem isso a página só teria uma
    previsão que ninguém pode conferir.
    """
    partes = []
    for r in resultados:
        teste = r["teste"]
        partes.append(
            pd.DataFrame(
                {
                    "hora_alvo": teste["hora_alvo"].to_numpy(),
                    "zona_id": teste["zona_id"].to_numpy(),
                    "previsao": r["previsao"],
                    # Decisão D4 do plano: sem intervalo nesta versão. A coluna existe no schema da
                    # spec 6.4 e fica nula, com a limitação documentada, em vez de inventar número.
                    "intervalo_inferior": pd.Series([None] * len(teste), dtype="float64"),
                    "intervalo_superior": pd.Series([None] * len(teste), dtype="float64"),
                    "qtd_corridas_real": teste[config.COLUNA_ALVO].to_numpy(),
                    "versao_modelo": r["versao_modelo"],
                    "tipo_rodada": r["tipo"],
                    "execucao": execucao,
                    "mes_alvo": str(r["mes_alvo"]),
                }
            )
        )
    return pd.concat(partes, ignore_index=True)


def montar_metricas(tabela: pd.DataFrame, execucao: str) -> pd.DataFrame:
    """Uma linha por execução × janela (o mês previsto), com o WAPE dos DOIS competidores.

    O baseline vem na mesma linha de propósito: métrica de modelo sem a régua ao lado é número
    solto. Quem abrir esta tabela em dezembro tem a comparação completa sem precisar de outra fonte.
    """
    m = tabela.copy()
    m["execucao"] = execucao
    m["mes_alvo"] = m["mes_alvo"].astype(str)
    m["corte"] = m["corte"].astype(str)
    m["venceu_baseline"] = m["ganho_pp"] > 0
    colunas = ["execucao", "mes_alvo", "corte", "tipo", "cortes_treino", "linhas_treino",
               "linhas_teste", "segundos_treino", "wape_modelo", "wape_baseline", "ganho_pp",
               "vies_modelo", "vies_baseline", "venceu_baseline", "versao_modelo"]
    return m[colunas]


def gravar(resultados: list[dict], tabela_metricas: pd.DataFrame, ambiente: str, sessao,
           execucao: str | None = None) -> dict:
    """Grava as duas tabelas da execução e devolve o que foi escrito."""
    execucao = execucao or nova_execucao()

    previsoes = montar_previsoes(resultados, execucao)
    metricas = montar_metricas(tabela_metricas, execucao)

    return {
        "execucao": execucao,
        TABELA_FORECAST: _gravar(previsoes, TABELA_FORECAST, ambiente, sessao, ["mes_alvo"]),
        TABELA_METRICAS: _gravar(metricas, TABELA_METRICAS, ambiente, sessao, ["execucao"]),
    }
