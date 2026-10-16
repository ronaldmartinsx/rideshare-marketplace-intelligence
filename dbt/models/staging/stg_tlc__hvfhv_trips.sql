{{
    config(
        materialized         = 'incremental',
        incremental_strategy = 'append',
        partitioned_by       = ['source_month'],
        pre_hook             = "{% if is_incremental() %} delete from {{ this }} where source_month = '{{ var('source_month', '2025-01') }}' {% endif %}"
    )
}}


{% set ano, mes = var('source_month', '2025-01').split('-') %}

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


{% if is_incremental() %}
  where year  = '{{ ano }}'
    and month = '{{ mes }}'
{% endif %}