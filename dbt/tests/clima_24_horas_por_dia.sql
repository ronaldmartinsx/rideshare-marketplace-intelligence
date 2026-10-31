-- Clima na Silver: cada dia LOCAL do mês tem 24 horas (Fase 3, F11).
-- Exceção: o domingo da troca para o horário de verão (2º domingo de março) tem 23, porque a 2h não existe.
-- O domingo da volta (1º de novembro) continua com 24: a 1h repetida vira uma linha só (qtd_horas_utc = 2).
-- Também confere que o mês tem todos os dias. Devolve uma linha por problema (zero linhas = passou).

{% set mes_referencia = var('source_month', '2025-01') %}

with horas_por_dia as (

    select date(hora_local) as dia, count(*) as horas
    from {{ ref('stg_open_meteo__weather_hourly') }}
    where source_month = '{{ mes_referencia }}'
    group by 1

),

problemas_por_dia as (

    select cast(dia as varchar) as onde, horas as encontrado
    from horas_por_dia
    where horas <> 24
      and not (
          horas = 23
          and month(dia) = 3
          and day_of_week(dia) = 7          -- domingo
          and day(dia) between 8 and 14     -- 2º domingo do mês
      )

),

dias_faltando as (

    select 'mês inteiro' as onde, count(*) as encontrado
    from horas_por_dia
    having count(*) <> day(last_day_of_month(date('{{ mes_referencia }}-01')))

)

select * from problemas_por_dia
union all
select * from dias_faltando
