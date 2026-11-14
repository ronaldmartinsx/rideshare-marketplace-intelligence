-- Fase 5, passo 2a: de onde vêm as 85 corridas que a reconciliação acusou em março/2026.
-- Hipótese: a fato tem corridas na 2h do 2º domingo de março, hora que NÃO EXISTE no relógio de NY
-- (ADR 0009), e a ml_demanda_hora_zona exclui essa hora da grade.
--     AWS_PROFILE=rideshare-admin dbt/.venv/bin/python scripts/athena_roda.py scripts/fase-5/conferir_hora_inexistente.sql

-- Q1: as corridas da fato que caem em horas marcadas como inexistentes na dim_tempo_hora.
select
    t.ano_mes,
    t.hora,
    t.hora_troca_horario_verao,
    count(*)                as linhas_na_fato,
    sum(f.qtd_corridas)     as corridas,
    count(distinct f.zona_origem_id) as zonas
from dev_gold.fct_demanda_zona_hora as f
join dev_gold.dim_tempo_hora as t
    on t.hora = f.hora_embarque
join dev_gold.dim_zona as z
    on z.zona_id = f.zona_origem_id
where t.hora_troca_horario_verao = 'inexistente'
  and z.is_zona_conhecida
  and not z.is_fora_de_nyc
group by t.ano_mes, t.hora, t.hora_troca_horario_verao
order by t.hora
;

-- Q2: para comparar a ordem de grandeza, o movimento das horas vizinhas no mesmo dia.
select
    t.hora,
    t.hora_do_dia,
    sum(f.qtd_corridas) as corridas
from dev_gold.fct_demanda_zona_hora as f
join dev_gold.dim_tempo_hora as t
    on t.hora = f.hora_embarque
join dev_gold.dim_zona as z
    on z.zona_id = f.zona_origem_id
where t.data = date '2026-03-08'
  and t.hora_do_dia between 0 and 5
  and z.is_zona_conhecida
  and not z.is_fora_de_nyc
group by t.hora, t.hora_do_dia
order by t.hora
;
