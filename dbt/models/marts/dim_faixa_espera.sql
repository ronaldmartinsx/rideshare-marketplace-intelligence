-- Dimensão das faixas de espera (Gold). Grão: uma faixa (18 linhas).
-- Os mesmos limites do CASE da fct_espera_histograma (ADR 0006): de 1 em 1 minuto até 15, depois
-- 15–20, 20–30 e 30+. Serve ao eixo dos gráficos (rótulo ordenado pelo faixa_id) e à medida do
-- percentil, que percorre as faixas em ordem (Fase 4). O teste de relacionamento da fato garante
-- que toda faixa gravada no histograma existe aqui.

with minuto_a_minuto as (

    select
        cast(f as integer)     as faixa_id,
        cast(f as integer)     as faixa_inicio_min,
        cast(f + 1 as integer) as faixa_fim_min
    from unnest(sequence(0, 14)) as t (f)

),

largas as (

    select *
    from (
        values
            (15, 15, 20),
            (16, 20, 30),
            (17, 30, cast(null as integer))  -- sem fim: o percentil que cair aqui é ">= 30 min"
    ) as t (faixa_id, faixa_inicio_min, faixa_fim_min)

),

faixas as (

    select * from minuto_a_minuto
    union all
    select * from largas

)

select
    faixa_id,
    faixa_inicio_min,
    faixa_fim_min,
    case
        when faixa_fim_min is null then cast(faixa_inicio_min as varchar) || '+ min'
        else cast(faixa_inicio_min as varchar) || '–' || cast(faixa_fim_min as varchar) || ' min'
    end as rotulo
from faixas
