-- Reconciliação da origem-destino mensal contra a diária: no mês processado, as somas batem (corridas,
-- milhas e tarifa). A diária já reconcilia com a Silver (reconciliacao_od), então a mensal herda a prova.

{% set mes = var('source_month', '2025-01') %}

with diaria as (
    select
        coalesce(sum(qtd_corridas), 0)      as corridas,
        coalesce(sum(milhas_total), 0)      as milhas,
        coalesce(sum(tarifa_base_total), 0) as tarifa
    from {{ ref('fct_od_diario') }}
    where source_month = '{{ mes }}'
),

mensal as (
    select
        coalesce(sum(qtd_corridas), 0)      as corridas,
        coalesce(sum(milhas_total), 0)      as milhas,
        coalesce(sum(tarifa_base_total), 0) as tarifa
    from {{ ref('fct_od_mensal') }}
    where source_month = '{{ mes }}'
)

select '{{ mes }}' as mes, diaria.corridas as corridas_diaria, mensal.corridas as corridas_mensal
from diaria
cross join mensal
where diaria.corridas <> mensal.corridas
   -- somas de decimais em ordens diferentes podem diferir na última casa: tolerância de 1 centavo/milha
   or abs(diaria.milhas - mensal.milhas) > 0.01
   or abs(diaria.tarifa - mensal.tarifa) > 0.01
