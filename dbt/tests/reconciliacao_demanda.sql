-- Reconciliação Silver × Gold (Fase 3, "pronto quando" 1): no mês processado, a Gold tem exatamente
-- as corridas válidas da Silver, e a soma da tarifa é a mesma das corridas com tarifa válida.
-- Devolve uma linha se algo não bater (zero linhas = passou).

{% set mes = var('source_month', '2025-01') %}

with silver as (

    select
        count_if(is_valid)                                                       as corridas,
        sum(case when is_valid and is_valid_economic_metrics then base_passenger_fare end) as tarifa
    from {{ ref('int_trips_enriched') }}
    where source_month = '{{ mes }}'

),

gold as (

    select
        coalesce(sum(qtd_corridas), 0)  as corridas,
        sum(tarifa_base_total)          as tarifa
    from {{ ref('fct_demanda_zona_hora') }}
    where source_month = '{{ mes }}'

)

select
    '{{ mes }}'       as mes,
    silver.corridas   as corridas_validas_silver,
    gold.corridas     as corridas_gold,
    silver.tarifa     as tarifa_silver,
    gold.tarifa       as tarifa_gold
from silver
cross join gold
where silver.corridas <> gold.corridas
   or abs(coalesce(silver.tarifa, 0) - coalesce(gold.tarifa, 0)) > 0.01
