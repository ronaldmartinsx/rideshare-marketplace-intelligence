-- Dimensão "encolhida" do período do histograma de espera (Gold). Grão: mês × hora do dia × tipo de dia.
--
-- Por que existe (Fase 4, D1): a fct_espera_histograma não tem a hora real (grão do ADR 0006). Ligada
-- à dim_tempo_hora, um filtro de data seria ignorado em silêncio pelo P90. Esta dimensão tem só os
-- atributos que o histograma honra e filtra as duas fatos com o mesmo recorte: o histograma direto, e
-- a demanda passando pela dim_tempo_hora (dim_periodo_espera 1 → N dim_tempo_hora 1 → N fct_demanda).
--
-- Sai da própria dim_tempo_hora: a chave periodo_id é calculada num lugar só.

select distinct
    periodo_id,
    ano_mes,
    hora_do_dia,
    tipo_dia
from {{ ref('dim_tempo_hora') }}
