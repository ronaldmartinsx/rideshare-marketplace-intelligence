-- Fase 5, passo 2b: conferir a tabela de features em dev. Só SELECT.
--     AWS_PROFILE=rideshare-admin dbt/.venv/bin/python scripts/athena_roda.py scripts/fase-5/conferir_features_dev.sql

-- Q1: os cortes, seus alvos e o horizonte. O último corte é o "dia de valer": tem_alvo = false.
select
    mes_corte,
    max(corte)                                              as corte,
    max(mes_alvo)                                           as mes_alvo,
    count(*)                                                as linhas,
    count(distinct zona_id)                                 as zonas,
    min(horizonte_horas)                                    as horizonte_min,
    max(horizonte_horas)                                    as horizonte_max,
    sum(case when tem_alvo then 1 else 0 end)               as com_alvo,
    sum(case when tem_alvo then 0 else 1 end)               as sem_alvo
from dev_gold.ml_features_demanda
group by mes_corte
order by mes_corte
;

-- Q2: A PROVA DA "MESMA FOTO". Para um corte, uma zona e uma hora da semana, todas as horas-alvo do mês
-- devem ter EXACTAMENTE os mesmos 4 lags. Se houver mais de um valor distinto, o lag vazou da hora-alvo.
select
    mes_corte,
    count(*)                                        as combinacoes,
    max(valores_distintos_lag1)                     as max_valores_distintos_lag1,
    max(valores_distintos_lag4)                     as max_valores_distintos_lag4
from (
    select
        mes_corte,
        zona_id,
        hora_da_semana,
        count(distinct coalesce(cast(lag_1_semana as varchar), 'NULO'))  as valores_distintos_lag1,
        count(distinct coalesce(cast(lag_4_semanas as varchar), 'NULO')) as valores_distintos_lag4
    from dev_gold.ml_features_demanda
    group by mes_corte, zona_id, hora_da_semana
)
group by mes_corte
order by mes_corte
;

-- Q3: completude dos lags. Nulo só deveria aparecer quando o lag aponta para a 2h inexistente de março.
select
    mes_corte,
    sum(case when lag_1_semana  is null then 1 else 0 end) as nulo_lag1,
    sum(case when lag_2_semanas is null then 1 else 0 end) as nulo_lag2,
    sum(case when lag_3_semanas is null then 1 else 0 end) as nulo_lag3,
    sum(case when lag_4_semanas is null then 1 else 0 end) as nulo_lag4,
    count(*)                                               as linhas
from dev_gold.ml_features_demanda
group by mes_corte
order by mes_corte
;

-- Q4: o feriado OBSERVADO funcionou? Em dev (mar a jun/2026) os federais são Memorial Day (25/05) e
-- Juneteenth (19/06). Nenhum deles tem observação deslocada, então serve para conferir o caminho normal.
select
    mes_alvo,
    nome_feriado_observado,
    min(data_format)        as primeira_hora,
    count(distinct hora_alvo) as horas,
    count(distinct zona_id)   as zonas
from (
    select mes_alvo, nome_feriado_observado, hora_alvo, zona_id,
           date_format(hora_alvo, '%Y-%m-%d %a') as data_format
    from dev_gold.ml_features_demanda
    where is_feriado_observado
)
group by mes_alvo, nome_feriado_observado
order by mes_alvo
;

-- Q5: sanidade do alvo e dos lags. A média do alvo e a média dos lags devem ser da mesma ordem de
-- grandeza (a demanda não muda de escala de um mês para o outro).
select
    mes_corte,
    round(avg(qtd_corridas), 2)   as media_alvo,
    round(avg(lag_1_semana), 2)   as media_lag1,
    round(avg(lag_4_semanas), 2)  as media_lag4,
    max(qtd_corridas)             as max_alvo,
    max(lag_1_semana)             as max_lag1
from dev_gold.ml_features_demanda
group by mes_corte
order by mes_corte
;
