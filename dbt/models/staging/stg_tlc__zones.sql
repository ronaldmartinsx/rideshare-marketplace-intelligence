-- Zonas de táxi da TLC, só renomeadas e tipadas (staging: sem regra de negócio).
-- Os atributos de negócio (is_cbd, is_aeroporto) ficam na dim_zona (Gold).

select
    cast(LocationID as integer)  as location_id,
    Borough                      as borough,
    Zone                         as zona,
    service_zone                 as service_zone
from {{ ref('seed_zonas_tlc') }}
