{{
    config(
        materialized         = 'incremental',
        incremental_strategy = 'append',
        partitioned_by       = ['source_month'],
        pre_hook             = "{% if is_incremental() %} delete from {{ this }} where source_month = '{{ var('source_month', '2025-01') }}' {% endif %}"
    )
}}


-- A macro ingest_ts_vigente consulta o manifesto na hora de rodar, e o dbt não enxerga isso ao
-- montar o grafo. Esta linha declara a dependência, para a linhagem (dbt docs) mostrá-la:
-- depends_on: {{ source('controle', 'manifesto_vigente') }}

{% set mes_referencia = var('source_month', '2025-01') %}
{% set ano, mes = mes_referencia.split('-') %}

select
  hvfhs_license_num,
  dispatching_base_num,
  originating_base_num,
  request_datetime,
  on_scene_datetime,
  pickup_datetime,
  dropoff_datetime,
  pulocationid,
  dolocationid,
  trip_miles,
  trip_time,
  base_passenger_fare,
  tolls,
  bcf,
  sales_tax,
  congestion_surcharge,
  airport_fee,
  tips,
  driver_pay,
  shared_request_flag,
  shared_match_flag,
  access_a_ride_flag,
  wav_request_flag,
  wav_match_flag,
  cbd_congestion_fee,
  year || '-' || month AS source_month,
  ingest_ts
from {{ source('tlc', 'hvfhv')}}

-- Sempre um mês por vez, e só a versão VIGENTE dele (Fase 2, D6). Vale também na primeira
-- construção: a projection da Bronze exige o ingest_ts escrito no SQL, e ler só a vigente
-- impede somar duas versões do mesmo mês.
where year      = '{{ ano }}'
  and month     = '{{ mes }}'
  and ingest_ts = '{{ ingest_ts_vigente('tlc_hvfhv', mes_referencia) }}'