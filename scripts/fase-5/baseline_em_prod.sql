-- Fase 5, passo 5.0: o baseline em produção, sobre as 32 rodadas. Só SELECT.
--     AWS_PROFILE=rideshare-admin dbt/.venv/bin/python scripts/athena_roda.py scripts/fase-5/baseline_em_prod.sql

-- Q1: resumo das 32 rodadas. É a régua da fase.
select
    count(*)                                                  as rodadas,
    round(min(wape_pct), 2)                                   as wape_min,
    round(avg(wape_pct), 2)                                   as wape_medio,
    round(max(wape_pct), 2)                                   as wape_max,
    round(avg(abs(vies_pct)), 2)                              as vies_absoluto_medio,
    sum(qtd_linhas_sem_baseline)                              as linhas_sem_palpite,
    sum(qtd_corridas_sem_baseline)                            as corridas_sem_palpite
from gold.ml_wape_baseline
;

-- Q2: AS 6 RODADAS DO BACKTEST (as últimas 6 avaliáveis). São estas que o modelo tem de vencer.
select
    mes_corte,
    mes_alvo,
    linhas_avaliadas,
    corridas_reais,
    wape_pct,
    vies_pct
from gold.ml_wape_baseline
order by mes_alvo desc
limit 6
;

-- Q3: as 32 rodadas em ordem, para ver se o WAPE do baseline é estável ou tem tendência.
-- Baseline que piora com o tempo indicaria mudança de regime na demanda.
select
    mes_alvo,
    round(wape_pct, 2) as wape_pct,
    round(vies_pct, 2) as vies_pct
from gold.ml_wape_baseline
order by mes_alvo
;
