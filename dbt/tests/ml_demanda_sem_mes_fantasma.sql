-- Barra o "mês fantasma": mês que entrou na grade sem existir na fato, e por isso aparece inteiro como
-- demanda zero.
--
-- Aconteceu de verdade em 14/11/2026, na primeira versão da ml_demanda_hora_zona: o recorte era
-- "ano_mes <= max(source_month)", que pressupõe nenhum buraco entre o primeiro mês e o último. Em
-- produção isso é verdade (33 partições), mas em dev, que é amostra de 4 meses (spec 11.2), a grade
-- inventou 25 meses de demanda zero. O modelo treinado nela aprenderia que a cidade parou.
--
-- A medição do passo 1 dá a régua: em produção, 3,3% das combinações hora x zona não têm corrida; em dev
-- deu 3,6 a 4,2%. O limite de 20% é folgado de propósito — ele não discute o número normal, só barra
-- o absurdo. Mês fantasma dá 100%; mês construído pela metade dá algo entre 40% e 60%.

select
    ano_mes,
    count(*)                                                                        as linhas,
    sum(case when zero_por_ausencia then 1 else 0 end)                              as linhas_sem_corrida,
    round(100.0 * sum(case when zero_por_ausencia then 1 else 0 end) / count(*), 1) as pct_sem_corrida
from {{ ref('ml_demanda_hora_zona') }}
group by ano_mes
having sum(case when zero_por_ausencia then 1 else 0 end) > 0.20 * count(*)
