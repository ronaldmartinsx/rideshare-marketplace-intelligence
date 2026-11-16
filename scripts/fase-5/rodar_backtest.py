"""Roda o backtest walk-forward do Mac (Fase 5, passo 6).

No Airflow isso vira a DAG ml_forecast (passo 7). Aqui é para desenvolver e para tirar os números.

Uso:
    <venv>/bin/python scripts/fase-5/rodar_backtest.py prod --rodadas 1 --arvores 100
    <venv>/bin/python scripts/fase-5/rodar_backtest.py prod --rodadas 6
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "airflow"))

from include.ml import backtest, config, dados, persistencia  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("ambiente", nargs="?", default="prod", choices=["dev", "prod"])
    p.add_argument("--rodadas", type=int, default=1, help="quantas rodadas de backtest")
    p.add_argument("--arvores", type=int, default=config.N_ARVORES)
    p.add_argument("--producao", action="store_true", help="inclui a rodada do 'dia de valer'")
    p.add_argument("--sem-salvar", action="store_true", help="não grava o modelo no S3")
    p.add_argument("--gravar", action="store_true",
                   help="grava ml_forecast_demanda e ml_backtest_metricas na Gold")
    args = p.parse_args()

    sessao = boto3.Session(profile_name="rideshare-admin", region_name="us-east-1")

    print(f"lendo features de {config.BANCO[args.ambiente]} (modo {dados.PADRAO})...", flush=True)
    t = time.perf_counter()
    features = dados.ler_features(args.ambiente, sessao)
    print(f"  {len(features):,} linhas em {time.perf_counter() - t:.1f}s, "
          f"{features.memory_usage(deep=True).sum() / 1024**2:.0f} MB\n")

    print(f"rodando {args.rodadas} rodada(s) com {args.arvores} árvores...", flush=True)
    tabela, resultados = backtest.rodar(
        args.ambiente,
        sessao,
        rodadas=args.rodadas,
        incluir_producao=args.producao,
        n_arvores=args.arvores,
        salvar_modelo=not args.sem_salvar,
        features=features,
    )

    mostrar = ["mes_alvo", "linhas_treino", "linhas_teste", "segundos_treino",
               "wape_modelo", "wape_baseline", "ganho_pp", "vies_modelo", "vies_baseline"]
    print()
    print(tabela[mostrar].to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    if args.gravar:
        print("\ngravando as tabelas ml_* na Gold...", flush=True)
        escrito = persistencia.gravar(resultados, tabela, args.ambiente, sessao)
        print(f"  execucao {escrito['execucao']}")
        for nome in (persistencia.TABELA_FORECAST, persistencia.TABELA_METRICAS):
            print(f"  {nome:24} {escrito[nome]:,} linhas")

    avaliaveis = tabela.dropna(subset=["wape_modelo"])
    if not avaliaveis.empty:
        m, b = avaliaveis["wape_modelo"].mean(), avaliaveis["wape_baseline"].mean()
        print(f"\nmédia  modelo {m:.2f}%   baseline {b:.2f}%   "
              f"ganho {b - m:+.2f} pontos percentuais")
        venceu = int((avaliaveis["ganho_pp"] > 0).sum())
        print(f"venceu em {venceu} de {len(avaliaveis)} rodadas")


if __name__ == "__main__":
    main()
