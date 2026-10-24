-- Reconciliação Silver × Gold da origem-destino: no mês processado, a fato tem exatamente as
-- corridas válidas da Silver.

{% set mes = var('source_month', '2025-01') %}

with silver as (
    select count_if(is_valid) as corridas
    from {{ ref('int_trips_enriched') }}
    where source_month = '{{ mes }}'
),

gold as (
    select coalesce(sum(qtd_corridas), 0) as corridas
    from {{ ref('fct_od_diario') }}
    where source_month = '{{ mes }}'
)

select '{{ mes }}' as mes, silver.corridas as corridas_silver, gold.corridas as corridas_gold
from silver
cross join gold
where silver.corridas <> gold.corridas
