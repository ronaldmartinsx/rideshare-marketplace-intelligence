-- Fase 5, passo 1b: conferir o filtro semântico de zonas escolhido na decisão do N.
-- Só SELECT. Roda com:
--     AWS_PROFILE=rideshare-admin dbt/.venv/bin/python scripts/athena_roda.py scripts/fase-5/conferir_zonas_validas.sql

-- Q1: como as 263 zonas da dim_zona se distribuem nas duas marcas que vamos usar como filtro.
select
    is_zona_conhecida,
    is_fora_de_nyc,
    count(*) as qtd_zonas
from gold.dim_zona
group by is_zona_conhecida, is_fora_de_nyc
order by is_zona_conhecida, is_fora_de_nyc
;

-- Q2: quem são as zonas que o filtro EXCLUI, para a exclusão ser consciente e não silenciosa.
select
    z.zona_id,
    z.zona,
    z.borough,
    z.is_zona_conhecida,
    z.is_fora_de_nyc
from gold.dim_zona as z
where not z.is_zona_conhecida or z.is_fora_de_nyc
order by z.zona_id
;

-- Q3: a conta que importa. Quantas zonas entram, e quanta demanda dos últimos 12 meses elas cobrem.
with por_zona as (
    select zona_origem_id, sum(qtd_corridas) as corridas
    from gold.fct_demanda_zona_hora
    where source_month >= '2025-10'
    group by zona_origem_id
)
select
    count(*)                                                                   as zonas_no_filtro,
    sum(case when z.zona_id is null then 1 else 0 end)                         as zonas_sem_dim,
    sum(d.corridas)                                                            as corridas_cobertas,
    (select sum(corridas) from por_zona)                                       as corridas_total,
    round(100.0 * sum(d.corridas) / (select sum(corridas) from por_zona), 2)   as pct_coberto
from por_zona as d
left join gold.dim_zona as z
    on z.zona_id = d.zona_origem_id
where z.is_zona_conhecida
  and not z.is_fora_de_nyc
;

-- Q4: tamanho da tabela de features que esse filtro gera, para confirmar que é pequena.
-- Horas distintas em toda a Gold x zonas do filtro.
select
    (select count(*) from gold.dim_tempo_hora)                                      as horas_na_dim_tempo,
    (select count(*) from gold.dim_zona where is_zona_conhecida and not is_fora_de_nyc) as zonas_no_filtro,
    (select count(*) from gold.dim_tempo_hora)
        * (select count(*) from gold.dim_zona where is_zona_conhecida and not is_fora_de_nyc) as linhas_grade_completa
;
