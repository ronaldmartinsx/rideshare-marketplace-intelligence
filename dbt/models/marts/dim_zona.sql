-- Dimensão de zonas (Gold). Grão: uma linha por zona de táxi da TLC (265 zonas).
-- Dimensão CONFORMADA: a mesma tabela serve às três fatos (demanda, espera e origem-destino),
-- e na fct_od_diario aparece em dois papéis, origem e destino (role-playing, Aula 1).
-- Aqui moram os ATRIBUTOS da zona; as marcas de qualidade das corridas ficam na Silver.

select
    z.location_id                                   as zona_id,
    z.borough,
    z.zona,
    z.service_zone,

    -- Dentro da Congestion Relief Zone pela lista oficial da MTA (ADR 0007), não pela taxa
    cbd.location_id is not null                     as is_cbd,

    -- JFK e LaGuardia ("Airports") e Newark ("EWR")
    z.service_zone in ('Airports', 'EWR')           as is_aeroporto,

    -- A 264 ("Unknown") é um local desconhecido: a corrida conta no total da cidade, mas não tem
    -- lugar no mapa. A 265 ("Outside of NYC") é um destino real, só que fora da cidade.
    z.location_id <> 264                            as is_zona_conhecida,

    -- Fora dos 5 boroughs de NYC: Newark (Nova Jersey) e a 265
    z.location_id in (1, 265)                       as is_fora_de_nyc

from {{ ref('stg_tlc__zones') }} as z
left join {{ ref('seed_zonas_cbd') }} as cbd
    on cbd.location_id = z.location_id
