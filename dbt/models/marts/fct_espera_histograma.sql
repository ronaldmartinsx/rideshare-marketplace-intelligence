{#
  on_schema_change temporário (Fase 4, D1): a coluna periodo_id é nova. "append_new_columns" a ADICIONA
  à tabela (ALTER TABLE ADD COLUMNS) em vez de parar o build; a reconstrução dos 32 meses preenche os
  meses antigos. Depois dela, volta ao padrão do projeto (fail).
#}
{{
    config(
        materialized         = 'incremental',
        incremental_strategy = 'append',
        partitioned_by       = ['source_month'],
        pre_hook             = "{% if is_incremental() %} delete from {{ this }} where source_month = '{{ var('source_month', '2025-01') }}' {% endif %}",
        on_schema_change     = 'append_new_columns'
    )
}}

-- Histograma do tempo de espera (Gold): a solução da Aula 5 para o percentil não aditivo.
-- Grão (decisão F4, ADR 0006): mês × hora do dia × tipo de dia × zona de origem × operadora × faixa.
-- Guarda CONTAGENS por faixa (aditivas): o P50/P90 de qualquer recorte sai somando as faixas do
-- recorte, acumulando até o percentil e interpolando dentro da faixa (passos no meta do YAML).
--
-- Só corridas válidas (nível corrida) E com espera válida (nível métrica: espera entre 0 e 2 h).
-- 18 faixas: 1 em 1 minuto até 15, depois 15–20, 20–30 e 30+ (P90 de jan/2025: 8,06 contra 8,05 real).

{% set mes_referencia = var('source_month', '2025-01') %}

with corridas as (

    select
        t.pulocationid,
        t.hvfhs_license_num,
        t.wait_time_s,
        d.hora_do_dia,
        d.tipo_dia,
        d.periodo_id  -- chave da dim_periodo_espera, lida da dim_tempo_hora (calculada só lá)
    from {{ ref('int_trips_enriched') }} as t
    -- LEFT join: uma hora sem par na dimensão vira tipo_dia nulo, e o teste not_null falha alto
    -- (com inner join, a corrida sumiria em silêncio do histograma)
    left join {{ ref('dim_tempo_hora') }} as d
        on d.hora = t.pickup_hour
    where t.source_month = '{{ mes_referencia }}'
      and t.is_valid
      and t.is_valid_wait_metric

),

com_faixa as (

    select
        *,
        case
            when wait_time_s < 900  then cast(floor(wait_time_s / 60) as integer)   -- 0..14: 1 min cada
            when wait_time_s < 1200 then 15                                         -- 15 a 20 min
            when wait_time_s < 1800 then 16                                         -- 20 a 30 min
            else 17                                                                 -- 30 min ou mais
        end as faixa_id
    from corridas

)

select
    hora_do_dia,
    tipo_dia,
    periodo_id,
    pulocationid                                    as zona_origem_id,
    hvfhs_license_num                               as licenca_operadora,
    faixa_id,
    -- Limites da faixa em minutos, para a interpolação no consumo (DAX, Fase 4)
    case faixa_id when 15 then 15 when 16 then 20 when 17 then 30 else faixa_id end      as faixa_inicio_min,
    case faixa_id when 15 then 20 when 16 then 30 when 17 then null else faixa_id + 1 end as faixa_fim_min,
    count(*)                                        as qtd_corridas,
    '{{ mes_referencia }}'                          as source_month
from com_faixa
-- periodo_id não muda o grão: no mês fixo, ele é função de hora_do_dia e tipo_dia
group by hora_do_dia, tipo_dia, periodo_id, pulocationid, hvfhs_license_num, faixa_id
