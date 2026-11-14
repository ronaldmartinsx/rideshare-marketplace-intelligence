-- Reconciliação da série de ML contra a fato, mês a mês.
--
-- A ml_demanda_hora_zona soma as operadoras e completa a grade com zeros, então o TOTAL de corridas tem
-- de ser idêntico ao da fct_demanda_zona_hora restrita às MESMAS zonas (conhecidas e dentro de NYC).
-- Completar a grade com zero não cria corrida; somar operadoras não perde corrida.
--
-- Se este teste falhar, uma de duas coisas aconteceu: a grade perdeu hora que tinha corrida, ou o filtro
-- de zonas mudou de um lado só.
--
-- As DUAS pontas excluem a hora inexistente da virada de março (ADR 0009), e isso é proposital. A
-- primeira versão deste teste comparava a tabela SEM essa hora contra a fato COM ela, e falhou com 85
-- corridas de diferença em março/2026 (medido em 14/11/2026, dev). Investigado: a fato tem 85 corridas
-- carimbadas em 2026-03-08 02:00, hora que não existe no relógio de NY — as horas vizinhas têm ~30 mil.
-- É artefato de dado (0,0004% do mês), e quem vigia o tamanho dele é o teste de aviso
-- ml_demanda_hora_inexistente_aviso. Aqui a comparação é entre horas que EXISTEM, dos dois lados.

with ml as (

    select ano_mes, sum(qtd_corridas) as corridas
    from {{ ref('ml_demanda_hora_zona') }}
    group by ano_mes

),

fato as (

    select
        f.source_month as ano_mes,
        sum(f.qtd_corridas) as corridas
    from {{ ref('fct_demanda_zona_hora') }} as f
    join {{ ref('dim_zona') }} as z
        on z.zona_id = f.zona_origem_id
    join {{ ref('dim_tempo_hora') }} as t
        on t.hora = f.hora_embarque
    where z.is_zona_conhecida
      and not z.is_fora_de_nyc
      -- mesma regra do model: só horas que existem no relógio de NY
      and coalesce(t.hora_troca_horario_verao, '') <> 'inexistente'
    group by f.source_month

)

select
    coalesce(ml.ano_mes, fato.ano_mes) as ano_mes,
    ml.corridas                        as corridas_ml,
    fato.corridas                      as corridas_fato
from ml
full outer join fato
    on fato.ano_mes = ml.ano_mes
where ml.ano_mes is null
   or fato.ano_mes is null
   or ml.corridas <> fato.corridas
