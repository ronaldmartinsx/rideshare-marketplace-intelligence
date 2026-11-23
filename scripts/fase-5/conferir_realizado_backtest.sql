-- Fase 5, pendência da seção 6 do aprendizado: o realizado do backtest oficial é 126.277.028
-- (Power BI) ou 126.277.020 (guia)? Hipótese: a coluna é REAL (32 bits), a soma sai REAL e o
-- Athena a exibe com 8 dígitos significativos (1.2627702E8), perdendo as unidades.
-- Só SELECT / DESCRIBE. Rodar com:
--     AWS_PROFILE=rideshare-admin dbt/.venv/bin/python scripts/athena_roda.py scripts/fase-5/conferir_realizado_backtest.sql

-- Q1: qual é o tipo declarado de cada coluna? É aqui que a hipótese se confirma ou cai.
describe gold.ml_forecast_demanda
;

-- Q2: a mesma soma em três réguas. Se a hipótese estiver certa, soma_como_esta (REAL) vem
-- arredondada e as duas outras trazem o número exato 126.277.028.
select
    count(*)                                         as linhas,
    count(distinct mes_alvo)                         as meses,
    sum(qtd_corridas_real)                           as soma_como_esta,
    sum(cast(qtd_corridas_real as double))           as soma_em_double,
    sum(cast(qtd_corridas_real as decimal(38, 0)))   as soma_em_decimal,
    sum(cast(previsao as double))                    as previsao_em_double
from gold.ml_forecast_demanda
where execucao = '20261116T233529Z'
  and tipo_rodada = 'backtest'
;

-- Q3: a soma em Double só é exata se nenhuma linha tiver fração. Confere isso e mostra o maior
-- valor da coluna (quanto maior o número, menos casas sobram num REAL de 32 bits).
select
    count(*)                                                                         as linhas,
    sum(case when qtd_corridas_real <> floor(qtd_corridas_real) then 1 else 0 end)    as com_fracao,
    sum(case when qtd_corridas_real is null then 1 else 0 end)                        as nulos,
    max(qtd_corridas_real)                                                            as maior_valor
from gold.ml_forecast_demanda
where execucao = '20261116T233529Z'
  and tipo_rodada = 'backtest'
;

-- Q4: a mesma conta mês a mês, para saber se o desencontro está num mês só ou espalhado
-- (e para ter a tabela certa se o guia precisar da abertura por mês).
select
    mes_alvo,
    count(*)                                        as linhas,
    sum(cast(qtd_corridas_real as double))          as realizado,
    sum(cast(previsao as double))                   as previsto
from gold.ml_forecast_demanda
where execucao = '20261116T233529Z'
  and tipo_rodada = 'backtest'
group by mes_alvo
order by mes_alvo
;
