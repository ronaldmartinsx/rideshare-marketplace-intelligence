-- Fase 5, passo 3: conferir o baseline escrito pelo Ronald. Só SELECT.
--     AWS_PROFILE=rideshare-admin dbt/.venv/bin/python scripts/athena_roda.py scripts/fase-5/conferir_baseline_dev.sql

-- Q1: o grão foi preservado e o palpite existe onde deveria.
select
    mes_corte,
    count(*)                                                     as linhas,
    sum(case when previsao_baseline is null then 1 else 0 end)   as palpite_nulo,
    sum(case when tem_alvo then 1 else 0 end)                    as com_gabarito,
    round(avg(previsao_baseline), 2)                             as media_palpite,
    round(avg(qtd_corridas), 2)                                  as media_gabarito
from dev_gold.ml_baseline_demanda
group by mes_corte
order by mes_corte
;

-- Q2: O TESTE DA REGRA DO NULO. Nas 1.048 linhas em que o lag de 4 semanas é nulo, o palpite tem de ser
-- a média dos TRÊS que existem, não nulo e não a média dos quatro tratando nulo como zero.
-- A coluna media_dos_tres é calculada aqui de forma independente, para comparar.
select
    count(*)                                                            as linhas_com_lag4_nulo,
    sum(case when previsao_baseline is null then 1 else 0 end)          as palpite_virou_nulo,
    sum(case when abs(previsao_baseline
                      - (lag_1_semana + lag_2_semanas + lag_3_semanas) / 3.0) < 0.0001
             then 1 else 0 end)                                         as igual_a_media_dos_tres,
    sum(case when abs(previsao_baseline
                      - (lag_1_semana + lag_2_semanas + lag_3_semanas) / 4.0) < 0.0001
             then 1 else 0 end)                                         as igual_a_media_dos_quatro_com_zero
from dev_gold.ml_baseline_demanda
where lag_4_semanas is null
;

-- Q3: nas linhas com os 4 lags completos, o palpite tem de ser a média simples dos quatro.
select
    count(*)                                                            as linhas_com_4_lags,
    sum(case when abs(previsao_baseline
                      - (lag_1_semana + lag_2_semanas + lag_3_semanas + lag_4_semanas) / 4.0) < 0.0001
             then 1 else 0 end)                                         as confere_media_dos_quatro
from dev_gold.ml_baseline_demanda
where lag_1_semana  is not null
  and lag_2_semanas is not null
  and lag_3_semanas is not null
  and lag_4_semanas is not null
;

-- Q4: o palpite ficou fracionário (cenário 4: não arredondar)?
select
    count(*)                                                                as linhas,
    sum(case when previsao_baseline <> floor(previsao_baseline) then 1 else 0 end) as fracionarios
from dev_gold.ml_baseline_demanda
;

-- Q5: espiada no WAPE que o baseline vai dar, por rodada. Ainda NÃO é o cálculo oficial (passo 4 é ✍️ do
-- Ronald): é só para saber a ordem de grandeza antes de comparar com o modelo.
select
    mes_alvo,
    count(*)                                                                      as linhas,
    sum(qtd_corridas)                                                             as corridas_reais,
    round(100.0 * sum(abs(qtd_corridas - previsao_baseline)) / sum(qtd_corridas), 2) as wape_pct
from dev_gold.ml_baseline_demanda
where tem_alvo
group by mes_alvo
order by mes_alvo
;
