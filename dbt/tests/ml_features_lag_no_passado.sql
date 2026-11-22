-- O TESTE ANTIVAZAMENTO Nº 1: a foto nunca é tirada depois do corte.
--
-- A decisão D1 diz que os lags são medidos a partir do corte da previsão. Se a hora_lag_1 passar do
-- corte, o modelo está recebendo informação que não existiria no dia de valer — e isso não daria erro
-- nenhum: daria um WAPE MELHOR. É o perfil do vazamento (Aula 2): o sintoma é indistinguível de
-- sucesso, então a única defesa é um teste explícito.
--
-- Também confere que o alvo está sempre DEPOIS do corte (horizonte positivo). Horizonte zero ou
-- negativo significaria prever o passado.

select
    corte,
    hora_alvo,
    zona_id,
    hora_lag_1,
    horizonte_horas,
    date_diff('hour', hora_lag_1, corte) as idade_da_foto_em_horas
from {{ ref('ml_features_demanda') }}
where hora_lag_1 > corte       -- a foto é do futuro: vazamento
   or horizonte_horas <= 0     -- o alvo não está à frente do corte
