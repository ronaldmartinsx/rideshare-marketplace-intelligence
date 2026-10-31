{{
    config(
        materialized         = 'incremental',
        incremental_strategy = 'append',
        partitioned_by       = ['source_month'],
        pre_hook             = "{% if is_incremental() %} delete from {{ this }} where source_month = '{{ var('source_month', '2025-01') }}' {% endif %}"
    )
}}

-- Demanda por hora × zona de origem × operadora (Gold). Peça ✍️ do Ronald na Fase 1.
-- Fase 3: incremental por source_month (F1), só corridas VÁLIDAS (nível corrida) e as somas
-- econômicas só das tarifas válidas (nível métrica), as duas marcas da int_trips_enriched.
-- Guarda componentes somáveis, nunca razões: o take rate é razão das SOMAS (Aula 1; meta no YAML).

{% set mes_referencia = var('source_month', '2025-01') %}

select
    pickup_hour                         AS hora_embarque,
    pulocationid                        AS zona_origem_id,
    hvfhs_license_num                   AS licenca_operadora,

    -- Demanda (todas as corridas válidas)
    count(1)                            AS qtd_corridas,
    sum(trip_miles)                     AS milhas_total,
    sum(trip_time)                      AS segundos_corrida_total,
    sum(tips)                           AS gorjetas_total,
    sum(cbd_congestion_fee)             AS taxa_cbd_total,
    count_if(shared_match_flag = 'Y')   AS qtd_corridas_compartilhadas,
    count_if(is_dropoff_cbd)            AS qtd_corridas_destino_cbd,

    -- Economia: só as corridas com tarifa válida (is_valid_economic_metrics), todas sobre o MESMO
    -- conjunto de corridas, para que take rate, receita por milha e repasse por hora usem
    -- numerador e denominador das mesmas corridas
    count_if(is_valid_economic_metrics)                                         AS qtd_corridas_tarifa_valida,
    sum(case when is_valid_economic_metrics then base_passenger_fare end)       AS tarifa_base_total,
    sum(case when is_valid_economic_metrics then driver_pay end)                AS repasse_motorista_total,
    sum(case when is_valid_economic_metrics then trip_miles end)                AS milhas_tarifa_valida_total,
    sum(case when is_valid_economic_metrics then trip_time end)                 AS segundos_tarifa_valida_total,

    '{{ mes_referencia }}'              AS source_month
from {{ ref('int_trips_enriched') }}
where source_month = '{{ mes_referencia }}'
  and is_valid
group by pickup_hour, pulocationid, hvfhs_license_num
