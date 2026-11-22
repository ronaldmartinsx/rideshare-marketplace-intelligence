"""Mede os modos de leitura do awswrangler na tabela de features (Fase 5, decisão B do passo 5).

Decisão B do plano: a forma de leitura é MEDIDA, não escolhida no escuro.

Mede CSV e UNLOAD. O terceiro modo da biblioteca, CTAS, fica de fora de propósito: ele cria tabela
temporária no banco da consulta, que em produção é o `gold`. Catálogo de produção não é lugar de
rascunho para benchmark. E se o UNLOAD ganhar, o CTAS fica irrelevante — ele entrega Parquet com um
efeito colateral que o UNLOAD não tem.

Uso (precisa de um ambiente com awswrangler; não faz parte do projeto):
    <venv>/bin/python scripts/fase-5/medir_leitura.py prod
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "airflow"))

from include.ml import config, dados  # noqa: E402

PERFIL = "rideshare-admin"


def medir(ambiente: str, modo: str, sessao) -> dict:
    """Uma leitura completa da tabela de features, cronometrada e com a memória do DataFrame."""
    inicio = time.perf_counter()
    df = dados.ler_features(ambiente, sessao, modo=modo)
    segundos = time.perf_counter() - inicio

    # deep=True para contar o conteúdo das colunas de texto, e não só os ponteiros
    memoria_mb = df.memory_usage(deep=True).sum() / 1024**2

    return {
        "modo": modo,
        "segundos": segundos,
        "linhas": len(df),
        "colunas": len(df.columns),
        "memoria_mb": memoria_mb,
        "df": df,
    }


def main() -> None:
    ambiente = sys.argv[1] if len(sys.argv) > 1 else "prod"
    sessao = boto3.Session(profile_name=PERFIL, region_name="us-east-1")

    print(f"Tabela: {config.BANCO[ambiente]}.{config.TABELA_FEATURES}")
    print(f"Colunas pedidas: {len(config.COLUNAS_LEITURA)}")
    print(f"Categorias: {', '.join(config.COLUNAS_CATEGORIA)}\n")

    resultados = []
    for modo in (dados.CSV, dados.UNLOAD):
        print(f"  lendo no modo {modo}...", flush=True)
        try:
            resultados.append(medir(ambiente, modo, sessao))
        except Exception as erro:  # noqa: BLE001
            print(f"  {modo}: FALHOU -> {type(erro).__name__}: {erro}")

    if not resultados:
        sys.exit("nenhuma leitura funcionou")

    print(f"\n{'modo':8} {'segundos':>10} {'linhas':>12} {'memoria MB':>12}")
    for r in resultados:
        print(f"{r['modo']:8} {r['segundos']:10.1f} {r['linhas']:12,} {r['memoria_mb']:12.1f}")

    # As duas leituras têm de devolver o MESMO dado: modo de transporte não pode mudar conteúdo.
    if len(resultados) == 2:
        a, b = resultados
        print("\nmesmo número de linhas:", a["linhas"] == b["linhas"])
        print("mesma soma do alvo    :",
              a["df"][config.COLUNA_ALVO].sum() == b["df"][config.COLUNA_ALVO].sum())

    melhor = min(resultados, key=lambda r: r["segundos"])
    print(f"\nmais rápido: {melhor['modo']} ({melhor['segundos']:.1f} s)")

    # Memória por coluna, para ver se as categorias fizeram o trabalho esperado
    df = melhor["df"]
    print("\nas 8 colunas mais pesadas:")
    uso = (df.memory_usage(deep=True) / 1024**2).sort_values(ascending=False)
    for coluna, mb in uso.head(8).items():
        print(f"  {str(coluna):26} {mb:8.1f} MB  {df[coluna].dtype if coluna in df else ''}")


if __name__ == "__main__":
    main()
