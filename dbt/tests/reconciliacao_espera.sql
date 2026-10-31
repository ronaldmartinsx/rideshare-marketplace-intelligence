-- Reconciliação Silver × Gold do histograma: no mês processado, o histograma tem exatamente as
-- corridas válidas com espera válida da Silver (nenhuma perdida no join com a dimensão de tempo).

{% set mes = var('source_month', '2025-01') %}

with silver as (
    select count_if(is_valid and is_valid_wait_metric) as corridas
    from {{ ref('int_trips_enriched') }}
    where source_month = '{{ mes }}'
),

gold as (
    select coalesce(sum(qtd_corridas), 0) as corridas
    from {{ ref('fct_espera_histograma') }}
    where source_month = '{{ mes }}'
)

select '{{ mes }}' as mes, silver.corridas as corridas_silver, gold.corridas as corridas_gold
from silver
cross join gold
where silver.corridas <> gold.corridas
