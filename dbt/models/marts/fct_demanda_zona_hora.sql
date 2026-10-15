select
    date_trunc('hour', pickup_datetime) AS hora_embarque,
    pulocationid                        AS zona_origem_id,
    hvfhs_license_num                   AS licenca_operadora,
    count(1)                            AS qtd_corridas,
    sum(trip_miles)                     AS milhas_total,
    sum(trip_time)                      AS segundos_corrida_total,
    sum(base_passenger_fare)            AS tarifa_base_total,
    sum(driver_pay)                     AS repasse_motorista_total,
    sum(tips)                           AS gorjetas_total,
    sum(cbd_congestion_fee)             AS taxa_cbd_total,
    count_if(shared_match_flag = 'Y')   AS qtd_corridas_compartilhadas
from {{ ref('stg_tlc__hvfhv_trips') }}
group by date_trunc('hour', pickup_datetime), pulocationid, hvfhs_license_num