-- Fase 5, passo 2a: conferir a grade construída em dev. Só SELECT.
--     AWS_PROFILE=rideshare-admin dbt/.venv/bin/python scripts/athena_roda.py scripts/fase-5/conferir_grade_dev.sql

-- Q1: meses na grade x meses com demanda de verdade. Se houver mês com 100% de zero por ausência,
-- a grade inventou mês que não existe na fato.
select
    ano_mes,
    count(*)                                                         as linhas,
    sum(qtd_corridas)                                                as corridas,
    sum(case when zero_por_ausencia then 1 else 0 end)               as linhas_ausentes,
    round(100.0 * sum(case when zero_por_ausencia then 1 else 0 end) / count(*), 1) as pct_ausente
from dev_gold.ml_demanda_hora_zona
group by ano_mes
order by ano_mes
;

-- Q2: quais meses a fato de dev realmente tem.
select source_month, sum(qtd_corridas) as corridas
from dev_gold.fct_demanda_zona_hora
group by source_month
order by source_month
;
