{{
    config(
        materialized         = 'incremental',
        incremental_strategy = 'append',
        partitioned_by       = ['source_month'],
        pre_hook             = "{% if is_incremental() %} delete from {{ this }} where source_month = '{{ var('source_month', '2025-01') }}' {% endif %}"
    )
}}

{#
  Corridas enriquecidas: chave surrogate, colunas derivadas e a MARCA de qualidade (Fase 3).
  Qualidade se marca, não se apaga: toda corrida da staging chega aqui; as inválidas ganham
  is_valid = false e o motivo. Quem decide não contá-las é a Gold (Aula 1: marcar × usar a marca).
#}

{% set mes_referencia = var('source_month', '2025-01') %}

{# As 25 colunas da corrida: juntas, distinguem duas corridas reais (F2; 27 colisões com só 5) #}
{% set colunas_da_corrida = [
    'hvfhs_license_num', 'dispatching_base_num', 'originating_base_num',
    'request_datetime', 'on_scene_datetime', 'pickup_datetime', 'dropoff_datetime',
    'pulocationid', 'dolocationid', 'trip_miles', 'trip_time',
    'base_passenger_fare', 'tolls', 'bcf', 'sales_tax', 'congestion_surcharge', 'airport_fee',
    'tips', 'driver_pay', 'shared_request_flag', 'shared_match_flag', 'access_a_ride_flag',
    'wav_request_flag', 'wav_match_flag', 'cbd_congestion_fee'
] %}

with corridas as (

    select *
    from {{ ref('stg_tlc__hvfhv_trips') }}
    where source_month = '{{ mes_referencia }}'

),

com_chave_de_conteudo as (

    select
        *,
        -- Mesmo conteúdo -> mesma chave (hash). Trata NULL sem zerar a chave (dbt-utils)
        {{ dbt_utils.generate_surrogate_key(colunas_da_corrida) }} as chave_conteudo
    from corridas

),

com_ordem as (

    select
        *,
        -- Duplicata exata (todas as 25 colunas iguais): 1 para a primeira cópia, 2, 3... para as demais (F3)
        row_number() over (partition by chave_conteudo order by chave_conteudo) as ordem_duplicata
    from com_chave_de_conteudo

),

derivadas as (

    select
        *,
        -- Chave final: conteúdo + ordem. Única mesmo com duplicatas exatas (ADR 0004)
        {{ dbt_utils.generate_surrogate_key(['chave_conteudo', 'ordem_duplicata']) }} as corrida_id,

        -- Espera: pedido -> embarque (spec 2.5; NÃO usar on_scene_datetime, só a Uber o preenche)
        date_diff('second', request_datetime, pickup_datetime)                as wait_time_s,

        -- Velocidade média em milhas por hora (trip_time está em segundos)
        case when trip_time > 0 then trip_miles / (trip_time / 3600.0) end    as speed_mph,

        -- Take rate da corrida (spec 2.5). Na Gold, sempre como razão das SOMAS, nunca média disto
        case when base_passenger_fare > 0
             then (base_passenger_fare - driver_pay) / base_passenger_fare end as take_rate,

        -- Destino dentro do CBD pela LISTA de zonas da MTA, não pela taxa (ADR 0007)
        dolocationid in (select location_id from {{ ref('seed_zonas_cbd') }}) as is_dropoff_cbd,

        date_trunc('hour', pickup_datetime)                                     as pickup_hour
    from com_ordem

),

com_motivo as (

    select
        *,
        case
            -- Decidida no plano (F3): a segunda cópia em diante de uma duplicata exata
            when ordem_duplicata > 1 then 'duplicata_exata'
            when trip_miles <= 0 then 'milhas_insuficientes'
            when trip_time <= 0 then 'tempo_corrida_insuficiente'
            when speed_mph > 100 then 'velocidade_impossivel'
            else null
        end as invalid_reason,
        case
            when wait_time_s >= 7200 or wait_time_s < 0 then false
            else true
        end as is_valid_wait_metric,
        case
            when base_passenger_fare <= 0 then false
            else true
        end as is_valid_economic_metrics
    from derivadas

)

-- Colunas listadas (e não "select *") para NÃO gravar a chave_conteudo: ela é só um passo para a
-- corrida_id, e um hash é texto aleatório que não comprime (~0,6 GB por mês à toa).
select
    corrida_id,
    ordem_duplicata,
    {{ dbt_utils.star(from=ref('stg_tlc__hvfhv_trips')) }},
    wait_time_s,
    speed_mph,
    take_rate,
    is_dropoff_cbd,
    pickup_hour,
    is_valid_wait_metric,
    is_valid_economic_metrics,
    invalid_reason,
    invalid_reason is null as is_valid
from com_motivo
