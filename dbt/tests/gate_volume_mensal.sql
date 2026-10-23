{{ config(severity = 'error') }}

{% set mes = var("source_month", "2025-01") %}

with p1 as (
    -- o mês processado
    select
        count_if(is_valid)                              as total_corridas_validas,
        day(last_day_of_month(date('{{ mes }}-01')))    as total_dias,
        date('{{ mes }}-01')                            as mes_referencia,
        0.3                                             as limite
    from {{ ref('int_trips_enriched') }}
    where source_month = '{{ mes }}'
),

historico as (
    -- média diária de cada um dos até 3 meses anteriores QUE EXISTEM na tabela
    select
        source_month,
        cast(count_if(is_valid) as double) / day(last_day_of_month(date(source_month || '-01'))) as media_diaria
    from {{ ref('int_trips_enriched') }}
    where source_month between date_format(date_add('month', -3, date('{{ mes }}-01')), '%Y-%m')
                           and date_format(date_add('month', -1, date('{{ mes }}-01')), '%Y-%m')
    group by source_month
),

p4 as (
    -- a referência: avg() só sobre os meses que vieram; count(*) diz quantos foram
    select
        avg(media_diaria)                                              as media_referencia,
        count(*)                                                       as qtd_meses_referencia,
        array_join(array_agg(source_month order by source_month), ', ') as meses_referencia
    from historico
),

p5 as (
    select
        p1.mes_referencia,
        cast(p1.total_corridas_validas as double) / p1.total_dias                         as media_diaria_mes,
        p4.media_referencia,
        p4.qtd_meses_referencia,
        p4.meses_referencia,
        (cast(p1.total_corridas_validas as double) / p1.total_dias) / p4.media_referencia - 1 as desvio,
        p1.limite
    from p1
    cross join p4
)

select *
from p5
where qtd_meses_referencia > 0                 -- sem referência: passa (sua decisão 1b)
  and (desvio < -limite or desvio > limite)    -- fora da faixa: devolve a linha, e o teste falha
