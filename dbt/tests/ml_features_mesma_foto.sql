-- O TESTE ANTIVAZAMENTO Nº 2: a mesma foto para todas as horas-alvo da mesma hora da semana.
--
-- Dentro de um corte, uma zona e uma hora da semana, TODAS as horas-alvo do mês têm de receber
-- exatamente os mesmos quatro lags. Se receberem valores diferentes, o lag está sendo medido a partir
-- da hora-alvo (o "jeito fácil") e não a partir do corte — exatamente o desalinhamento
-- treino-produção que a decisão D1 existe para impedir.
--
-- A intuição: você tirou UMA foto no fim do mês. Perguntam sobre a sexta do dia 16 e sobre a sexta do
-- dia 30, e você olha a MESMA foto nas duas vezes. Se a foto muda conforme a pergunta, ela não é uma
-- foto — é uma espiada no futuro.
--
-- Medido em 14/11/2026 (dev): 44.016 combinações por corte (168 horas da semana x 262 zonas), todas
-- com 1 valor distinto por lag.

select
    mes_corte,
    zona_id,
    hora_da_semana,
    count(distinct coalesce(cast(lag_1_semana  as varchar), 'NULO')) as valores_lag_1,
    count(distinct coalesce(cast(lag_2_semanas as varchar), 'NULO')) as valores_lag_2,
    count(distinct coalesce(cast(lag_3_semanas as varchar), 'NULO')) as valores_lag_3,
    count(distinct coalesce(cast(lag_4_semanas as varchar), 'NULO')) as valores_lag_4,
    count(distinct hora_lag_1)                                       as datas_da_foto
from {{ ref('ml_features_demanda') }}
group by mes_corte, zona_id, hora_da_semana
having count(distinct coalesce(cast(lag_1_semana  as varchar), 'NULO')) > 1
    or count(distinct coalesce(cast(lag_2_semanas as varchar), 'NULO')) > 1
    or count(distinct coalesce(cast(lag_3_semanas as varchar), 'NULO')) > 1
    or count(distinct coalesce(cast(lag_4_semanas as varchar), 'NULO')) > 1
    or count(distinct hora_lag_1) > 1
