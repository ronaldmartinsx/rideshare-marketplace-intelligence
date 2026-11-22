-- Prova que o baseline é a média dos lags EXISTENTES, por um caminho diferente do usado no model.
--
-- O model calcula com array: filter() tira os nulos, reduce() soma, cardinality() conta.
-- Aqui a mesma média é recalculada com aritmética de coluna: coalesce para somar tratando nulo como
-- zero, e uma contagem explícita de quantos NÃO são nulos como divisor. São duas fórmulas distintas que
-- precisam dar o mesmo número — é isso que torna este teste uma verificação e não uma tautologia.
--
-- Por que o divisor não pode ser 4 fixo: nas 1.048 linhas em que o lag de 4 semanas é nulo, dividir por
-- 4 trataria o dado ausente como zero corrida e empurraria o palpite para baixo. O divisor é quantos
-- lags existem, não quantos poderiam existir.
--
-- Tolerância de 1e-6 por causa da ordem das somas em ponto flutuante.

with recalculado as (

    select
        corte,
        hora_alvo,
        zona_id,
        previsao_baseline,
        (
            coalesce(lag_1_semana,  0)
          + coalesce(lag_2_semanas, 0)
          + coalesce(lag_3_semanas, 0)
          + coalesce(lag_4_semanas, 0)
        ) * 1.0
        / nullif(
              (case when lag_1_semana  is null then 0 else 1 end)
            + (case when lag_2_semanas is null then 0 else 1 end)
            + (case when lag_3_semanas is null then 0 else 1 end)
            + (case when lag_4_semanas is null then 0 else 1 end)
          , 0) as media_independente
    from {{ ref('ml_baseline_demanda') }}

)

select
    corte,
    hora_alvo,
    zona_id,
    previsao_baseline,
    media_independente
from recalculado
where abs(previsao_baseline - media_independente) > 0.000001
   -- e um dos dois ser nulo sem o outro ser também é divergência
   or (previsao_baseline is null) <> (media_independente is null)
