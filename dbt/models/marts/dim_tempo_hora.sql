-- Dimensão de tempo por hora LOCAL de Nova York (Gold). Grão: uma hora do relógio de parede de NY.
-- Junta: calendário, feriados (seed), tipo de dia (o grão do histograma, F4), clima (Silver) e a
-- marcação das horas de troca do horário de verão (F11; ADR 0009).
--
-- Cobre 2024-01-01 a 2026-12-31, o período do seed de feriados. Quando chegarem corridas de 2027, os
-- testes de relacionamento das fatos falham alto: é o aviso para estender o seed e este intervalo.

with dias as (

    -- sequence() do Athena aceita no máximo 10.000 elementos: gerar DIAS (1.096) e não horas (26.304)
    select dia
    from unnest(sequence(date '2024-01-01', date '2026-12-31', interval '1' day)) as t (dia)

),

horas as (

    select
        date_add('hour', h, cast(d.dia as timestamp)) as hora,
        cast(d.dia as date)                           as data,
        h                                             as hora_do_dia
    from dias as d
    cross join unnest(sequence(0, 23)) as t (h)

),

feriados_federais as (

    -- Só os federais definem o tipo de dia "feriado" (os estaduais de NY costumam ser flutuantes)
    select data, feriado
    from {{ ref('seed_feriados') }}
    where esfera = 'federal'

),

calendario as (

    select
        h.hora,
        h.data,
        date_format(h.data, '%Y-%m')                    as ano_mes,
        year(h.data)                                    as ano,
        month(h.data)                                   as mes,
        h.hora_do_dia,
        day_of_week(h.data)                             as dia_da_semana,   -- 1 = segunda ... 7 = domingo
        day_of_week(h.data) in (6, 7)                   as is_fim_de_semana,
        f.feriado is not null                           as is_feriado,
        f.feriado                                       as nome_feriado,
        case
            when f.feriado is not null           then 'feriado'
            when day_of_week(h.data) in (6, 7)   then 'fim_de_semana'
            else 'util'
        end                                             as tipo_dia,

        -- Horas de troca do horário de verão em NY (regra dos EUA desde 2007):
        -- 2º domingo de março, 2h: não existe (o relógio pula para 3h);
        -- 1º domingo de novembro, 1h: acontece duas vezes (soma o movimento de duas horas reais).
        case
            when month(h.data) = 3 and day_of_week(h.data) = 7 and day(h.data) between 8 and 14
                 and h.hora_do_dia = 2 then 'inexistente'
            when month(h.data) = 11 and day_of_week(h.data) = 7 and day(h.data) between 1 and 7
                 and h.hora_do_dia = 1 then 'repetida'
        end                                             as hora_troca_horario_verao
    from horas as h
    left join feriados_federais as f
        on f.data = h.data

)

select
    c.*,
    -- Chave do período do histograma de espera (Fase 4, D1): mês × hora do dia × tipo de dia.
    -- Calculada SÓ aqui: a dim_periodo_espera e a fct_espera_histograma a leem desta tabela.
    c.ano_mes || '|' || lpad(cast(c.hora_do_dia as varchar), 2, '0') || '|' || c.tipo_dia as periodo_id,
    -- Clima da hora local (nulo onde a Silver do clima ainda não tem o mês)
    w.temperatura_c,
    w.precipitacao_mm,
    w.chuva_mm,
    w.neve_cm,
    w.vento_kmh
from calendario as c
left join {{ ref('stg_open_meteo__weather_hourly') }} as w
    on w.hora_local = c.hora
