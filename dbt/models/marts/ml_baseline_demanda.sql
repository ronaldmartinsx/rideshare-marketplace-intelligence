{{
    config(
        materialized   = 'table',
        partitioned_by = ['mes_corte'],
        tags           = ['ml']
    )
}}

-- O BASELINE SAZONAL INGÊNUO (Fase 5, passo 3). Grão: corte x hora-alvo x zona, o mesmo da prova.
--
-- Peça ✍️ do Ronald: a lógica é dele (o filter/reduce, a regra do nulo e o cast para double). O Claude
-- fez só o refactor pedido em 14/11/2026 — extrair o array para uma CTE, comentar e padronizar a caixa.
-- O resultado foi conferido como IDÊNTICO ao da versão original, pela impressão digital da tabela.
--
-- O que é: o palpite mais simples que ainda faz sentido — a média da demanda na MESMA hora da semana,
-- naquela zona, nas 4 semanas anteriores ao corte. Nenhum treino, nenhum parâmetro.
--
-- Para que serve: ser a RÉGUA. Sem baseline, "o modelo errou 13%" não é bom nem ruim, é só um número.
-- Com baseline, vira comparação. E aqui ele não é figurante: a spec 9.1 aceita as duas saídas da fase,
-- o modelo vencendo o baseline OU um relatório honesto de que não venceu.
--
-- O que quebra sem ele: a fase perde o critério de aprovação. Qualquer WAPE pareceria aceitável.
--
-- Por que os 4 lags já vêm prontos: a ml_features_demanda os calculou a partir do CORTE (decisão D1), e
-- o baseline herda essa garantia de graça. Não há janela nem PARTITION BY a escrever aqui.

with lags_validos as (

    select
        corte,
        hora_alvo,
        zona_id,
        qtd_corridas,
        tem_alvo,
        mes_corte,
        mes_alvo,
        lag_1_semana,
        lag_2_semanas,
        lag_3_semanas,
        lag_4_semanas,

        -- Os lags que REALMENTE existem, num array só.
        --
        -- Por que filtrar o nulo em vez de trocar por zero: nulo aqui significa "não tenho esse dado",
        -- e não "houve zero corrida". Trocar por zero empurraria o palpite para baixo e ensinaria uma
        -- demanda que nunca existiu. Acontece em 1.048 linhas do corte de março, quando o lag de 4
        -- semanas cai na 2h inexistente da virada do horário de verão (ADR 0009).
        --
        -- Por que o array e não a soma direta das colunas: em SQL, AVG() ignora nulo quando agrega
        -- LINHAS, mas aritmética entre COLUNAS propaga nulo. Então
        --     (lag_1 + lag_2 + lag_3 + lag_4) / 4
        -- devolveria nulo se qualquer um dos quatro fosse nulo — e não a média dos outros três.
        -- O array resolve isso: filtra primeiro, depois soma e conta o que sobrou.
        filter(
            array[lag_1_semana, lag_2_semanas, lag_3_semanas, lag_4_semanas],
            x -> x is not null
        ) as lags

    from {{ ref('ml_features_demanda') }}

)

select
    corte,
    hora_alvo,
    zona_id,
    qtd_corridas,
    tem_alvo,
    mes_corte,
    mes_alvo,
    lag_1_semana,
    lag_2_semanas,
    lag_3_semanas,
    lag_4_semanas,

    -- O PALPITE: soma dos lags existentes dividida pela quantidade deles.
    --
    -- reduce() soma o array: parte da semente, aplica (acumulado, item) -> acumulado + item a cada
    -- elemento, e a última função devolve o acumulado como está. É o equivalente de uma coluna
    -- personalizada do Power Query que percorre uma lista acumulando.
    --
    -- A semente é cast(0 as double) por um motivo que não é estético: em Trino, divisão entre INTEIROS
    -- é divisão inteira e TRUNCA. Os lags são bigint; com semente inteira, a soma sairia bigint, a
    -- divisão truncaria e o baseline viraria número redondo sem ninguém pedir. O double na semente é o
    -- que preserva as casas decimais (73% dos palpites são fracionários).
    --
    -- O nullif(..., 0) protege contra os 4 lags nulos ao mesmo tempo: hoje isso nunca acontece
    -- (medido), mas sem ele seria divisão por zero no dia em que acontecer.
    reduce(lags, cast(0 as double), (soma, item) -> soma + item, soma -> soma)
        / nullif(cardinality(lags), 0) as previsao_baseline

from lags_validos
