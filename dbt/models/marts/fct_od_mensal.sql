{{
    config(
        materialized         = 'incremental',
        incremental_strategy = 'append',
        partitioned_by       = ['source_month'],
        pre_hook             = "{% if is_incremental() %} delete from {{ this }} where source_month = '{{ var('source_month', '2025-01') }}' {% endif %}"
    )
}}

-- Origem-destino por MÊS (Gold). Grão: mês × zona de origem × zona de destino × operadora.
-- Existe para o Power BI (Fase 4, D2): a fct_od_diario tem 55 milhões de linhas nos 32 meses, e a
-- página do CBD só precisa de "de onde vêm as corridas que entram no centro" por mês. O corte diário
-- do antes × depois (05/01/2025) sai da fct_demanda_zona_hora, que tem a hora.
-- Lê a própria Gold (fct_od_diario), não a Silver: soma de somas, as mesmas regras de validade.

{% set mes_referencia = var('source_month', '2025-01') %}

select
    zona_origem_id,
    zona_destino_id,
    licenca_operadora,
    sum(qtd_corridas)                AS qtd_corridas,
    sum(milhas_total)                AS milhas_total,
    sum(qtd_corridas_tarifa_valida)  AS qtd_corridas_tarifa_valida,
    sum(tarifa_base_total)           AS tarifa_base_total,
    sum(milhas_tarifa_valida_total)  AS milhas_tarifa_valida_total,
    '{{ mes_referencia }}'           AS source_month
from {{ ref('fct_od_diario') }}
where source_month = '{{ mes_referencia }}'
group by zona_origem_id, zona_destino_id, licenca_operadora
