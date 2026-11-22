-- Fase 5, passo 1: medir a demanda para decidir o N das top zonas e o desenho da tabela de features.
-- Só SELECT, nada é alterado. Roda com:
--     AWS_PROFILE=rideshare-admin dbt/.venv/bin/python scripts/athena_roda.py scripts/fase-5/medir_demanda.sql
--
-- Recorte dos rankings: últimos 12 meses (2025-10 a 2026-09). O filtro por source_month usa a
-- partição, então o Athena lê só esses meses.

-- Q1: o período disponível, mês a mês. Confirma os 33 meses e mostra se algum mês está fora do padrão.
select
    source_month,
    count(*)                            as linhas,
    sum(qtd_corridas)                   as corridas,
    count(distinct zona_origem_id)      as zonas_com_corrida,
    count(distinct licenca_operadora)   as operadoras
from gold.fct_demanda_zona_hora
group by source_month
order by source_month
;

-- Q2: ranking das zonas por volume nos últimos 12 meses, com a cobertura acumulada.
-- É a consulta que decide o N: mostra quanto do total as primeiras zonas já explicam.
with por_zona as (
    select zona_origem_id, sum(qtd_corridas) as corridas
    from gold.fct_demanda_zona_hora
    where source_month >= '2025-10'
    group by zona_origem_id
),
classificado as (
    select
        zona_origem_id,
        corridas,
        row_number() over (order by corridas desc)                                                as posicao,
        sum(corridas) over ()                                                                     as total,
        sum(corridas) over (order by corridas desc rows between unbounded preceding and current row) as acumulado
    from por_zona
)
select
    posicao,
    zona_origem_id,
    corridas,
    round(100.0 * corridas  / total, 3) as pct_do_total,
    round(100.0 * acumulado / total, 2) as pct_acumulado
from classificado
where posicao <= 60
order by posicao
;

-- Q3: a mesma cobertura, resumida nos marcos de N que interessam para a decisão.
with por_zona as (
    select zona_origem_id, sum(qtd_corridas) as corridas
    from gold.fct_demanda_zona_hora
    where source_month >= '2025-10'
    group by zona_origem_id
),
classificado as (
    select
        corridas,
        row_number() over (order by corridas desc)                                                as posicao,
        sum(corridas) over ()                                                                     as total,
        sum(corridas) over (order by corridas desc rows between unbounded preceding and current row) as acumulado
    from por_zona
)
select
    posicao                              as n_zonas,
    round(100.0 * acumulado / total, 2)  as pct_acumulado
from classificado
where posicao in (10, 20, 30, 40, 50, 75, 100, 150, 200)
order by posicao
;

-- Q4: continuidade do histórico. Quantas zonas aparecem em todos os 12 meses, e quantas têm buraco.
-- Zona com histórico furado é risco: o lag não existe onde o mês falta.
select
    meses_presentes,
    count(*) as qtd_zonas
from (
    select zona_origem_id, count(distinct source_month) as meses_presentes
    from gold.fct_demanda_zona_hora
    where source_month >= '2025-10'
    group by zona_origem_id
)
group by meses_presentes
order by meses_presentes desc
;

-- Q5: densidade real contra a grade completa, em setembro de 2026, já somando as operadoras.
-- A fato só tem linha onde HOUVE corrida. A diferença entre as duas contagens é a quantidade de
-- horas com demanda zero que estão AUSENTES, e não gravadas como zero. Isso decide se a tabela de
-- features precisa de uma grade completa (dim_tempo_hora x zonas) com left join.
with agregado as (
    select hora_embarque, zona_origem_id, sum(qtd_corridas) as corridas
    from gold.fct_demanda_zona_hora
    where source_month = '2026-09'
    group by hora_embarque, zona_origem_id
)
select
    count(*)                                                        as combinacoes_existentes,
    count(distinct zona_origem_id)                                  as zonas,
    count(distinct hora_embarque)                                   as horas,
    count(distinct zona_origem_id) * count(distinct hora_embarque)  as grade_completa,
    count(distinct zona_origem_id) * count(distinct hora_embarque) - count(*) as ausentes_zero_implicito
from agregado
;
