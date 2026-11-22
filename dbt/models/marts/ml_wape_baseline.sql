{{
    config(
        materialized = 'table',
        tags         = ['ml']
    )
}}

with base as (
    select
        mes_alvo,
        mes_corte,
        count_if(previsao_baseline is not null)     as linhas_avaliadas,
        sum( 
            case 
                when previsao_baseline is not null then qtd_corridas
                end
            )                                      as corridas_reais,
        sum(previsao_baseline)                     as corridas_previstas,
        sum(abs(qtd_corridas - previsao_baseline)) as erro_absoluto_total,
        -- As duas colunas do descarte. Elas existem para que linha sem palpite NUNCA desapareça em
        -- silêncio: 5 linhas descartadas é pouco, mas 5 linhas com 4.000 corridas é muito, e só a
        -- segunda coluna revela a diferença.
        count_if(previsao_baseline is null)         as qtd_linhas_sem_baseline,
        -- O coalesce não é cosmético: count_if sobre conjunto vazio devolve 0, mas sum sobre conjunto
        -- vazio devolve NULO. Sem ele, as duas colunas descreveriam a mesma situação com respostas
        -- diferentes — uma dizendo "zero", a outra "não sei".
        coalesce(
            sum(
                case
                    when previsao_baseline is null then qtd_corridas
                end
            ),
            0
        )                                          as qtd_corridas_sem_baseline
    from {{ ref('ml_baseline_demanda') }}
    where tem_alvo
    group by mes_alvo, mes_corte
)

select
    mes_alvo,
    mes_corte,
    linhas_avaliadas,
    corridas_reais,
    corridas_previstas,
    erro_absoluto_total,
    qtd_linhas_sem_baseline,
    qtd_corridas_sem_baseline,
    round(100 * cast(erro_absoluto_total as double)
          / nullif(corridas_reais, 0), 2)          as wape_pct,
    round(100 * cast(corridas_previstas - corridas_reais as double)
          / nullif(corridas_reais, 0), 2)          as vies_pct
from base