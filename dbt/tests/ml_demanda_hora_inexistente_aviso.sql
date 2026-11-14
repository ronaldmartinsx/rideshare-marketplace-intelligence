{{ config(severity = 'warn', tags = ['ml']) }}

-- A etiqueta 'ml' existe porque este teste NÃO faz ref() da ml_demanda_hora_zona: ele lê a fato direto,
-- para medir o que a tabela descartou. Sem a etiqueta, o seletor "ml_demanda_hora_zona+" não o alcança
-- e ele nunca roda (aconteceu na primeira versão, em 14/11/2026).

-- AVISO, não erro. Vigia o tamanho do artefato das horas que não existem no relógio de Nova York.
--
-- Na virada para o horário de verão, no 2º domingo de março, o relógio pula de 1h59 para 3h: a 2h não
-- acontece (ADR 0009). Mesmo assim a fato tem corridas carimbadas nessa hora — relógio de aparelho
-- errado ou registro gravado durante a virada. A ml_demanda_hora_zona exclui essa hora da grade, porque
-- incluí-la criaria uma hora de demanda falsa para o modelo aprender.
--
-- Medido em 14/11/2026 (dev): 85 corridas em 2026-03-08 02:00, espalhadas por 59 zonas, contra ~30 mil
-- nas horas vizinhas. São 0,0004% do mês.
--
-- Por que AVISO e não erro: descartar 85 corridas em 22 milhões é decisão consciente e correta. O que
-- não pode passar em silêncio é esse número CRESCER — se um dia aparecerem milhares de corridas nessa
-- hora, deixou de ser artefato e virou problema de fuso na Silver, e aí a decisão precisa ser revista.
-- O limite de 1.000 é folgado: hoje o valor é 85, e uma hora normal naquele horário tem ~30 mil.

select
    t.ano_mes,
    t.hora,
    sum(f.qtd_corridas)                 as corridas_descartadas,
    count(distinct f.zona_origem_id)    as zonas
from {{ ref('fct_demanda_zona_hora') }} as f
join {{ ref('dim_tempo_hora') }} as t
    on t.hora = f.hora_embarque
join {{ ref('dim_zona') }} as z
    on z.zona_id = f.zona_origem_id
where t.hora_troca_horario_verao = 'inexistente'
  and z.is_zona_conhecida
  and not z.is_fora_de_nyc
group by t.ano_mes, t.hora
having sum(f.qtd_corridas) > 1000
