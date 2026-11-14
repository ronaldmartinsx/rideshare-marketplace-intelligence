{{
    config(
        materialized   = 'table',
        partitioned_by = ['ano_mes'],
        tags           = ['ml']
    )
}}

-- A SÉRIE LIMPA que o ML prevê (Fase 5, passo 2a). Grão: hora local de NY x zona de origem.
--
-- Por que esta tabela existe, se a fct_demanda_zona_hora já tem quase isso:
--   1. A fato tem grão hora x zona x OPERADORA, e o alvo da spec 9.1 é "todas as operadoras". Somar aqui,
--      uma vez, evita que cada consumidor (features, baseline, Power BI) some do seu jeito.
--   2. A fato só tem linha ONDE HOUVE CORRIDA. Hora sem corrida é linha AUSENTE, não linha zerada
--      (medido no passo 1: 3,3% das combinações em set/2026). Treinar só nas linhas existentes ensinaria ao
--      modelo que demanda zero não acontece. Aqui a grade é completa e o ausente vira zero DE VERDADE.
--   3. Fixa o recorte de zonas da fase num lugar só (ver "zonas" abaixo).
--
-- O que quebra sem ela: o modelo nunca veria uma hora de demanda zero, e o WAPE seria calculado apenas
-- sobre as horas movimentadas — um resultado bonito e falso.
--
-- Materialização table (não incremental): são ~6,3 milhões de linhas e a reconstrução é barata. A tabela é
-- reconstruída pela DAG ml_forecast (tag 'ml'), não pela dbt_mes, porque a Fase 5 lê o histórico inteiro.

with zonas as (

    -- Recorte SEMÂNTICO, não estatístico (passo 1, decisão do N): "zonas conhecidas e dentro de NYC".
    -- Exclui exatamente 3 zonas — 1 (Newark Airport, Nova Jersey), 264 (N/A) e 265 (Outside of NYC) —
    -- ao custo de 0,005% da demanda, cobrindo 99,99%. Critério semântico não pode vazar; "top N por
    -- volume" poderia, porque exigiria olhar o volume do período de teste para escolher.
    select zona_id
    from {{ ref('dim_zona') }}
    where is_zona_conhecida
      and not is_fora_de_nyc

),

meses_com_dado as (

    -- Quais meses a fato REALMENTE tem. Não é "até o último mês": é a lista dos meses existentes.
    --
    -- A primeira versão usava "ano_mes <= max(source_month)", que pressupõe que todo mês entre o
    -- primeiro e o último tem dado. Em produção isso é verdade (33 partições sem buraco, medido no
    -- passo 1), mas em dev é FALSO: dev é amostra de 4 meses (spec 11.2), e a grade inventou 25 meses
    -- de demanda zero — 100% das linhas marcadas como zero_por_ausencia. O teste de fumaça em dev pegou
    -- o bug que a produção teria escondido.
    --
    -- Com a lista explícita, a grade cobre exatamente os meses que existem, em qualquer ambiente, e
    -- um mês que venha a faltar em produção não vira silenciosamente um mês de demanda zero.
    select distinct source_month as ano_mes
    from {{ ref('fct_demanda_zona_hora') }}

),

horas as (

    select hora, ano_mes, hora_troca_horario_verao
    from {{ ref('dim_tempo_hora') }}
    where ano_mes in (select ano_mes from meses_com_dado)
      -- A 2h do 2º domingo de março NÃO EXISTE no relógio de NY (ADR 0009). Mantê-la na grade criaria uma
      -- hora de demanda zero que nunca aconteceu. A hora "repetida" de novembro fica, porque ela existe
      -- (e carrega o movimento de duas horas reais; é por isso que vai marcada).
      and coalesce(hora_troca_horario_verao, '') <> 'inexistente'

),

grade as (

    -- O produto cartesiano é o ponto da tabela: toda hora x toda zona, exista corrida ou não.
    select
        h.hora,
        h.ano_mes,
        h.hora_troca_horario_verao,
        z.zona_id
    from horas as h
    cross join zonas as z

),

demanda as (

    -- O alvo: corridas somadas sobre as operadoras (hoje Uber e Lyft)
    select
        hora_embarque  as hora,
        zona_origem_id as zona_id,
        sum(qtd_corridas) as qtd_corridas
    from {{ ref('fct_demanda_zona_hora') }}
    group by hora_embarque, zona_origem_id

)

select
    g.hora,
    g.zona_id,

    -- O alvo da previsão. coalesce: a ausência na fato é demanda zero, e aqui ela fica explícita.
    coalesce(d.qtd_corridas, 0)                     as qtd_corridas,

    -- Marca de onde o zero veio. Zero medido e zero por ausência são indistinguíveis depois do coalesce,
    -- e essa diferença importa para auditar a tabela (e para explicar o número numa entrevista).
    d.zona_id is null                               as zero_por_ausencia,

    -- Hora que acontece duas vezes na virada do horário de verão: o valor soma duas horas reais de
    -- movimento. É 1 hora em 26.304; fica marcada para poder ser tratada ou excluída no treino.
    g.hora_troca_horario_verao = 'repetida'          as hora_dobrada,

    g.ano_mes
from grade as g
left join demanda as d
    on  d.hora    = g.hora
    and d.zona_id = g.zona_id
