{{
    config(
        materialized         = 'incremental',
        incremental_strategy = 'append',
        partitioned_by       = ['source_month'],
        pre_hook             = "{% if is_incremental() %} delete from {{ this }} where source_month = '{{ var('source_month', '2025-01') }}' {% endif %}"
    )
}}

-- Origem-destino por dia (Gold). Grão: dia × zona de origem × zona de destino × operadora.
-- A dim_zona aparece em DOIS PAPÉIS (role-playing, Aula 1): origem e destino. No Power BI, um dos
-- relacionamentos fica inativo e é ligado pela medida com USERELATIONSHIP.
-- Só corridas válidas; a economia segue a mesma regra da fct_demanda_zona_hora (tarifa válida).

{% set mes_referencia = var('source_month', '2025-01') %}

select
    cast(pickup_datetime as date)                                               AS data_embarque,
    pulocationid                                                                AS zona_origem_id,
    dolocationid                                                                AS zona_destino_id,
    hvfhs_license_num                                                           AS licenca_operadora,
    count(1)                                                                    AS qtd_corridas,
    sum(trip_miles)                                                             AS milhas_total,
    count_if(is_valid_economic_metrics)                                         AS qtd_corridas_tarifa_valida,
    sum(case when is_valid_economic_metrics then base_passenger_fare end)       AS tarifa_base_total,
    sum(case when is_valid_economic_metrics then trip_miles end)                AS milhas_tarifa_valida_total,
    '{{ mes_referencia }}'                                                      AS source_month
from {{ ref('int_trips_enriched') }}
where source_month = '{{ mes_referencia }}'
  and is_valid
group by cast(pickup_datetime as date), pulocationid, dolocationid, hvfhs_license_num
