{{
    config(
        materialized   = 'table',
        partitioned_by = ['mes_corte'],
        tags           = ['ml']
    )
}}

-- A TABELA DE FEATURES do modelo (Fase 5, passo 2b). Grão: CORTE x hora-alvo x zona.
--
-- Por que o grão tem três partes, e não duas (decisão D1):
--   Os lags são medidos a partir do CORTE da previsão, não da hora-alvo. Então o mesmo par
--   (hora, zona) tem valores de lag DIFERENTES dependendo de qual corte está sendo usado.
--
--   A analogia: no dia 30/09 você tira UMA foto da rua e guarda no bolso. Perguntam "e no dia 16/10?"
--   e você olha a foto. Perguntam "e no dia 30/10?" e você olha A MESMA foto, porque é a única que tem.
--   A foto não fica mais nova porque a pergunta é sobre um dia mais distante. O que muda é só quanto
--   ela ajuda — e isso é o horizonte_horas, que entra como feature.
--
-- Por que NÃO medir o lag da hora-alvo (o jeito fácil):
--   Daria para fazer, porque o histórico inteiro está no disco: para o alvo "sexta 15/05", bastaria dar
--   a "sexta 08/05", uma semana antes. Mas no dia de valer essa sexta fresquinha não existe — parado no
--   fim de abril, a sexta mais recente é 24/04, três semanas antes do alvo. O modelo treinado no jeito
--   fácil aprende "o número que me deram é quase a resposta" e aplica essa confiança a um número bem
--   mais velho. É desalinhamento treino-produção: vazamento disfarçado de inconsistência. A regra é
--   treinar com a MESMA informação que existirá no dia de valer, nem melhor nem pior.
--
-- O que quebra sem esta tabela: o treino usaria informação que a produção não tem, o WAPE sairia
-- otimista, e o modelo pareceria vencer o baseline por um motivo que não se sustenta na prática.
--
-- O último corte é o "dia de valer": o mês-alvo dele ainda não aconteceu, então qtd_corridas fica nula
-- e tem_alvo = false. É a previsão de verdade, a única que não dá para conferir.

with meses as (

    -- Os meses que existem de fato na série limpa (ela já resolveu o problema do mês fantasma)
    select distinct ano_mes
    from {{ ref('ml_demanda_hora_zona') }}

),

cortes as (

    -- Um corte por mês: a última hora do mês, e o mês seguinte como alvo.
    -- Lags de até 4 semanas (504 horas) cabem dentro do primeiro mês, então todo mês serve de corte.
    select
        d.ano_mes                                                                       as mes_corte,
        max(d.hora)                                                                     as corte,
        date_format(date_add('month', 1, date_parse(d.ano_mes || '-01', '%Y-%m-%d')), '%Y-%m') as mes_alvo
    from {{ ref('ml_demanda_hora_zona') }} as d
    join meses as m
        on m.ano_mes = d.ano_mes
    group by d.ano_mes

),

horas_base as (

    -- A grade de horas com a "hora da semana" (0 a 167): 0 = segunda 00h, 167 = domingo 23h.
    -- A dim_tempo_hora tem exatamente 24 linhas por dia, então subtrair 168 horas cai sempre na
    -- MESMA hora da semana, uma semana atrás. É isso que torna a aritmética de lag confiável.
    select
        hora,
        ano_mes,
        data,
        hora_do_dia,
        dia_da_semana,
        (dia_da_semana - 1) * 24 + hora_do_dia  as hora_da_semana,
        is_fim_de_semana,
        hora_troca_horario_verao,
        temperatura_c,
        precipitacao_mm,
        chuva_mm,
        neve_cm,
        vento_kmh
    from {{ ref('dim_tempo_hora') }}

),

ultima_ocorrencia as (

    -- Para cada corte e cada hora da semana: qual foi a ÚLTIMA vez que ela aconteceu antes do corte.
    -- É o "dia em que a foto foi tirada", por hora da semana.
    select
        c.mes_corte,
        c.corte,
        h.hora_da_semana,
        max(h.hora) as hora_lag_1
    from cortes as c
    join horas_base as h
        on h.hora <= c.corte
    group by c.mes_corte, c.corte, h.hora_da_semana

),

horas_dos_lags as (

    -- Desdobra em 4 linhas: 1, 2, 3 e 4 semanas antes daquela última ocorrência.
    -- Fica em formato alto (uma linha por semana) para a junção com a demanda ser uma só.
    select
        u.mes_corte,
        u.hora_da_semana,
        s.semanas,
        date_add('hour', -168 * (s.semanas - 1), u.hora_lag_1) as hora_do_lag
    from ultima_ocorrencia as u
    cross join unnest(array[1, 2, 3, 4]) as s (semanas)

),

lags as (

    -- Volta ao formato largo: uma linha por corte x hora da semana x zona, com as 4 colunas de lag.
    -- Nulo acontece quando o lag aponta para a 2h inexistente da virada de março, que a série limpa
    -- não tem (1 hora por ano). O LightGBM trata nulo nativamente, então fica nulo de propósito.
    select
        hl.mes_corte,
        hl.hora_da_semana,
        d.zona_id,
        -- A DATA DA FOTO. Guardada para o vazamento ser TESTÁVEL e não apenas afirmado: o teste
        -- ml_features_lag_no_passado prova que ela nunca passa do corte. As outras três são
        -- -168, -336 e -504 horas a partir dela.
        max(case when hl.semanas = 1 then hl.hora_do_lag  end) as hora_lag_1,
        max(case when hl.semanas = 1 then d.qtd_corridas end) as lag_1_semana,
        max(case when hl.semanas = 2 then d.qtd_corridas end) as lag_2_semanas,
        max(case when hl.semanas = 3 then d.qtd_corridas end) as lag_3_semanas,
        max(case when hl.semanas = 4 then d.qtd_corridas end) as lag_4_semanas
    from horas_dos_lags as hl
    join {{ ref('ml_demanda_hora_zona') }} as d
        on d.hora = hl.hora_do_lag
    group by hl.mes_corte, hl.hora_da_semana, d.zona_id

),

feriados_observados as (

    -- DECISÃO D2: o feriado vale no dia OBSERVADO, não no dia de calendário.
    -- A dim_tempo_hora liga por f.data (certo para o histograma de espera da Fase 3), mas para DEMANDA
    -- o que importa é o dia em que as pessoas não trabalharam. Caso real no período: 4/7/2026 cai num
    -- sábado e foi observado na sexta, 3/7. A dim_tempo_hora marca o sábado; aqui marcamos a sexta.
    -- Só os federais definem tipo de dia, mesma regra da dim_tempo_hora (os estaduais de NY flutuam).
    select data_observada as data, max(feriado) as feriado
    from {{ ref('seed_feriados') }}
    where esfera = 'federal'
    group by data_observada

),

zonas as (

    select zona_id
    from {{ ref('dim_zona') }}
    where is_zona_conhecida
      and not is_fora_de_nyc

),

alvos as (

    -- Para cada corte, todas as horas do mês-alvo x todas as zonas. O mês-alvo do último corte ainda
    -- não aconteceu: ele existe na dim_tempo_hora (que vai até dez/2026) mas não na série limpa.
    select
        c.mes_corte,
        c.corte,
        c.mes_alvo,
        h.hora                                          as hora_alvo,
        h.hora_da_semana,
        h.data,
        h.hora_do_dia,
        h.dia_da_semana,
        h.is_fim_de_semana,
        h.hora_troca_horario_verao,
        h.temperatura_c,
        h.precipitacao_mm,
        h.chuva_mm,
        h.neve_cm,
        h.vento_kmh,
        z.zona_id
    from cortes as c
    join horas_base as h
        on h.ano_mes = c.mes_alvo
        -- mesma regra da série limpa: a 2h da virada de março não existe no relógio de NY (ADR 0009)
        and coalesce(h.hora_troca_horario_verao, '') <> 'inexistente'
    cross join zonas as z

)

select
    a.corte,
    a.hora_alvo,
    a.zona_id,

    -- Quão velha está a foto. Feature legítima: o modelo aprende sozinho que previsão para 716 horas
    -- à frente merece menos confiança que para 380.
    date_diff('hour', a.corte, a.hora_alvo)             as horizonte_horas,

    -- ALVO. Nulo no último corte, cujo mês ainda não aconteceu ("dia de valer").
    d.qtd_corridas                                      as qtd_corridas,
    d.hora                                               is not null as tem_alvo,
    d.zero_por_ausencia                                 as alvo_zero_por_ausencia,

    -- A FOTO: os 4 lags, todos medidos antes do corte. A hora_lag_1 é a data em que a foto foi tirada,
    -- guardada para auditoria — é o que torna a ausência de vazamento uma coisa testável.
    l.hora_lag_1,
    l.lag_1_semana,
    l.lag_2_semanas,
    l.lag_3_semanas,
    l.lag_4_semanas,

    -- Calendário. Conhecido com anos de antecedência: é o que permite ANTECIPAR, e não só reagir.
    a.hora_do_dia,
    a.dia_da_semana,
    a.hora_da_semana,
    a.is_fim_de_semana,
    f.data                                               is not null as is_feriado_observado,
    f.feriado                                           as nome_feriado_observado,
    case
        when f.data is not null  then 'feriado'
        when a.is_fim_de_semana  then 'fim_de_semana'
        else 'util'
    end                                                 as tipo_dia_observado,
    month(a.data)                                       as mes_do_ano,

    -- CLIMA OBSERVADO. O prefixo clima_obs_ é de propósito: este é o vazamento ACEITO e documentado
    -- (spec 9.1, Aula 2). Em produção só existiria PREVISÃO do tempo, com erro. No backtest usamos o
    -- que de fato aconteceu, o que deixa o resultado otimista. O nome da coluna é a documentação que
    -- não se perde: ninguém vai confundir clima_obs_chuva_mm com previsão de chuva.
    a.temperatura_c                                     as clima_obs_temperatura_c,
    a.precipitacao_mm                                   as clima_obs_precipitacao_mm,
    a.chuva_mm                                          as clima_obs_chuva_mm,
    a.neve_cm                                           as clima_obs_neve_cm,
    a.vento_kmh                                         as clima_obs_vento_kmh,

    -- Hora repetida de novembro: soma o movimento de duas horas reais. Marcada para poder ser excluída.
    a.hora_troca_horario_verao = 'repetida'              as hora_dobrada,

    a.mes_alvo,
    a.mes_corte
from alvos as a
left join lags as l
    on  l.mes_corte      = a.mes_corte
    and l.hora_da_semana = a.hora_da_semana
    and l.zona_id        = a.zona_id
left join {{ ref('ml_demanda_hora_zona') }} as d
    on  d.hora    = a.hora_alvo
    and d.zona_id = a.zona_id
left join feriados_observados as f
    on f.data = a.data
