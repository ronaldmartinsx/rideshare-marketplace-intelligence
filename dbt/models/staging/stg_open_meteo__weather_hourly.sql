{{
    config(
        materialized         = 'incremental',
        incremental_strategy = 'append',
        partitioned_by       = ['source_month'],
        pre_hook             = "{% if is_incremental() %} delete from {{ this }} where source_month = '{{ var('source_month', '2025-01') }}' {% endif %}"
    )
}}

{#
  Clima hora a hora no horário LOCAL de Nova York (Fase 3, decisão F11; ADR 0009).
  O arquivo da Bronze traz o mês + o dia 1 seguinte em UTC, com as horas em listas (arrays).
  Aqui: desdobrar as listas -> converter UTC para NY -> recortar o mês local -> uma linha por hora local.
  Na hora repetida de novembro (a 1h acontece duas vezes), as duas horas UTC viram uma só:
  média da temperatura e do vento, soma da chuva e da neve. A 2h de março não existe e não aparece.
#}

{% set mes_referencia = var('source_month', '2025-01') %}
{% set ano, mes = mes_referencia.split('-') %}

with arquivo as (

    -- Uma linha: o JSON do mês, na versão vigente do manifesto (a projection exige o ingest_ts)
    select hourly, ingest_ts
    from {{ source('open_meteo', 'weather') }}
    where year      = '{{ ano }}'
      and month     = '{{ mes }}'
      and ingest_ts = '{{ ingest_ts_vigente('open_meteo', mes_referencia) }}'

),

horas_utc as (

    -- UNNEST com várias listas: desdobra lado a lado (o 1º item de cada lista na mesma linha)
    select
        h.hora_texto,
        h.temperatura_c,
        h.precipitacao_mm,
        h.chuva_mm,
        h.neve_cm,
        h.vento_kmh,
        arquivo.ingest_ts
    from arquivo
    cross join unnest(
        hourly.time, hourly.temperature_2m, hourly.precipitation,
        hourly.rain, hourly.snowfall, hourly.wind_speed_10m
    ) as h (hora_texto, temperatura_c, precipitacao_mm, chuva_mm, neve_cm, vento_kmh)

),

horas_ny as (

    select
        -- UTC -> horário de NY, com as regras do horário de verão.
        -- ATENÇÃO: "cast(... at time zone 'America/New_York' as timestamp)" NÃO converte neste Athena
        -- (testado em 20/10/2026: devolve a hora UTC). Formatar como texto no fuso de NY e converter
        -- de volta para timestamp funciona.
        date_parse(
            date_format(
                with_timezone(date_parse(hora_texto, '%Y-%m-%dT%H:%i'), 'UTC') at time zone 'America/New_York',
                '%Y-%m-%d %H:%i'
            ),
            '%Y-%m-%d %H:%i'
        ) as hora_local,
        temperatura_c,
        precipitacao_mm,
        chuva_mm,
        neve_cm,
        vento_kmh,
        ingest_ts
    from horas_utc

)

select
    hora_local,
    avg(temperatura_c)    as temperatura_c,
    sum(precipitacao_mm)  as precipitacao_mm,
    sum(chuva_mm)         as chuva_mm,
    sum(neve_cm)          as neve_cm,
    avg(vento_kmh)        as vento_kmh,
    count(*)              as qtd_horas_utc,   -- 2 só na hora repetida de novembro
    '{{ mes_referencia }}' as source_month,
    max(ingest_ts)        as ingest_ts
from horas_ny
-- Recorte do mês LOCAL: as primeiras horas UTC do arquivo ainda são do mês anterior em NY
where date_format(hora_local, '%Y-%m') = '{{ mes_referencia }}'
group by hora_local
