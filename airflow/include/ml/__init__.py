"""Previsão de demanda por hora e zona (Fase 5).

A divisão de responsabilidades segue a convenção da Fase 2 (decisao.py × manifesto.py): a REGRA é
pura e testável sem AWS; a entrada e saída ficam em módulos separados.

- janelas.py  : PURA. A regra das rodadas do backtest (quais cortes treinam, qual é previsto).
- config.py   : constantes (colunas, tipos, parâmetros do LightGBM, caminho do modelo no S3).
- dados.py    : lê as features do Athena com awswrangler e aplica os tipos.
- modelo.py   : treina o LightGBM, prevê e salva o binário no S3.
- backtest.py : roda as rodadas e compara com o baseline.

Toda a transformação de dado ficou em SQL (decisão D3 do plano da fase). O Python entra só onde o
SQL não vai: treinar o modelo.
"""
