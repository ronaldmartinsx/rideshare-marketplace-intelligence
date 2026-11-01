-- Dimensão de mês (Gold). Grão: um mês (36: 2024 a 2026, o período da dim_tempo_hora).
-- Topo da hierarquia de tempo no Power BI (Fase 4, D2):
--   dim_mes 1 → N dim_periodo_espera 1 → N dim_tempo_hora
--   dim_mes 1 → N fct_od_mensal
-- Uma segmentação de mês aqui filtra as quatro fatos com o mesmo recorte.

select distinct
    ano_mes,
    ano,
    mes,
    cast(ano_mes || '-01' as date) as mes_inicio  -- eixo de data dos gráficos de tendência
from {{ ref('dim_tempo_hora') }}
