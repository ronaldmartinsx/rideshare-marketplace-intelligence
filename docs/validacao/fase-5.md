# Validação — Fase 5 (previsão de demanda)

Evidência medida, não suposta. Cada seção diz o que foi consultado, o resultado e o que a decisão virou.

---

## 1. Medição da demanda e escolha das zonas (passo 1)

**Data:** 14/11/2026
**Consultas:** [`scripts/fase-5/medir_demanda.sql`](../../scripts/fase-5/medir_demanda.sql) e
[`scripts/fase-5/conferir_zonas_validas.sql`](../../scripts/fase-5/conferir_zonas_validas.sql)
**Custo:** 70,2 MB lidos em 9 consultas ≈ **US$ 0,00033**

### 1.1 O que existe

33 meses sem buraco, de 2024-01 a 2026-09. Entre 19 e 22 milhões de corridas por mês, 261 a 263 zonas de origem
com corrida, **2 operadoras** (Uber e Lyft). Total de 672.148.703 corridas, igual à foto da Fase 4.

### 1.2 História por zona: completa

| Meses presentes (nos últimos 12) | Zonas |
|---|---|
| 12 | 261 |
| 10 | 1 |

Praticamente nenhuma zona tem buraco no histórico, então as features de defasagem não correm o risco de ficar
sem o mês de origem.

### 1.3 Densidade: os dados são densos, não esparsos

Em setembro de 2026, já somando as operadoras:

| Medida | Valor |
|---|---|
| Combinações hora × zona existentes | 182.402 |
| Grade completa (262 zonas × 720 horas) | 188.640 |
| Ausentes (demanda zero implícita) | 6.238 — **3,3%** |

A `fct_demanda_zona_hora` só tem linha onde houve corrida, então hora sem corrida é linha **ausente**, não linha
zerada. A expectativa do Claude era de muitas ausências; a medição mostrou 3,3%. A consequência prática continua
valendo, mas é pequena: a tabela de features parte de uma **grade completa** (`dim_tempo_hora` × zonas) com
`left join` na fato, para essas 3,3% virarem zero de verdade e o modelo aprender que demanda zero existe.

### 1.4 A descoberta: a demanda NÃO é concentrada

Cobertura acumulada por número de zonas, ordenadas por volume dos últimos 12 meses:

| N zonas | % da demanda |
|---|---|
| 10 | 12,6% |
| 20 | 22,2% |
| 30 | 30,4% |
| 40 | 38,0% |
| **50** | **44,6%** |
| 75 | 58,5% |
| 100 | 70,1% |
| 150 | 86,4% |
| 200 | 96,6% |

A zona líder (138, LaGuardia) é **1,95%** do total; a segunda (132, JFK), 1,59%.

Isso contraria o pressuposto da spec 9.1, que sugeria "top N zonas por volume (ex.: 50)" — com N = 50 o projeto
preveria **44,6% do mercado e ignoraria 55,4%**. A curva não é de Pareto.

**Interpretação:** HVFHV não é táxi amarelo. Táxi amarelo concentra em Manhattan e aeroportos; Uber e Lyft em Nova
York são majoritariamente deslocamento de bairro (Brooklyn, Queens, Bronx), o que espalha a demanda de forma
bem distribuída por quase todas as zonas.

### 1.5 Decisão: filtro semântico, não estatístico

O critério deixa de ser "top N por volume" e passa a ser **"zonas conhecidas e dentro de NYC"**, usando as marcas
que a `dim_zona` já tem desde a Fase 3: `is_zona_conhecida` e `not is_fora_de_nyc`.

O filtro exclui exatamente 3 zonas:

| Zona | Nome | Borough | Motivo |
|---|---|---|---|
| 1 | Newark Airport | EWR | Fora de NYC (Nova Jersey) |
| 264 | N/A | Unknown | Zona desconhecida |
| 265 | Outside of NYC | N/A | Fora de NYC |

Resultado medido:

| Medida | Valor |
|---|---|
| Zonas no filtro | 262 (260 com corrida nos últimos 12 meses) |
| Corridas cobertas | 253.366.719 |
| Corridas no período | 253.379.534 |
| **Cobertura** | **99,99%** |
| Linhas da grade completa | 6.891.648 (26.304 horas × 262 zonas) |

Excluir as três custa 12.815 corridas em 253 milhões: **0,005%** da demanda.

**Três razões para a troca de critério:**

1. **O modelo é global** (decisão da spec 9.1): um modelo só, com a zona como feature. Incluir 262 zonas em vez de
   50 custa praticamente o mesmo — uma tabela de ~6,3 milhões de linhas é pequena para o LightGBM.
2. **O WAPE é ponderado por volume.** Zona minúscula não distorce a métrica principal, que era o medo por trás do
   "top N". A proteção já está na métrica escolhida.
3. **Elimina o vazamento de seleção** (Aula 2, vazamento nº 4). Escolher "top N por volume" exige olhar o volume,
   e olhar o período de teste para escolher é vazamento. Um critério **semântico** não tem o que vazar; um
   critério **estatístico** tem.

Divergência da letra da spec, que a própria spec deixou aberta com ⚠️ "Definir N com os dados". Registrada em ADR.

---

## 2. A série limpa: `ml_demanda_hora_zona` (passo 2a)

**Data:** 14/11/2026
**Arquivos:** [`dbt/models/marts/ml_demanda_hora_zona.sql`](../../dbt/models/marts/ml_demanda_hora_zona.sql),
3 testes singulares em `dbt/tests/`, documentação e testes genéricos em `_gold.yml`
**Construído em:** dev (amostra de 4 meses, fev a mai/2026)
**Custo:** 11,6 MB nas consultas de conferência; as 3 construções em dev não reportam bytes, mas a Gold de dev
é pequena e o passo inteiro ficou em centavos

### 2.1 Dois defeitos encontrados, os dois pelo teste em dev

**Defeito 1 — meses fantasmas.** A primeira versão recortava a grade com `ano_mes <= max(source_month)`, que
pressupõe nenhum buraco entre o primeiro mês e o último. A construção em dev saiu com **5.545.230 linhas** quando
o esperado eram ~754 mil:

| Meses | Corridas | % zero por ausência |
|---|---|---|
| 2024-01 a 2026-01 (25 meses) | **0** | **100%** |
| 2026-02 a 2026-05 (os 4 reais do dev) | 19,9 a 22,1 M | 3,6 a 4,2% |

Os 25 primeiros eram inventados pela grade. Em produção o bug **não apareceria**, porque as 33 partições existem
sem buraco (passo 1) — é um caso em que o ambiente de dev, por ser amostra e não cópia reduzida, exercita um
caminho que o prod não exercita.

**Conserto:** a grade passou a usar `ano_mes in (select distinct source_month from fct)`. Depois dele, dev saiu com
**754.298 linhas** = 176.064 + 194.666 + 188.640 + 194.928, exatamente os 4 meses reais. Travado pelo teste
`ml_demanda_sem_mes_fantasma`, que falha se algum mês passar de 20% de linhas sem corrida (a referência medida é
3,3% em prod e 3,6 a 4,2% em dev).

**Defeito 2 — o teste de reconciliação estava errado, não o model.** Ele acusou 85 corridas de diferença em
março/2026 (22.054.702 na fato × 22.054.617 na tabela). Investigado: a fato tem 85 corridas carimbadas em
**2026-03-08 02:00**, hora que não existe no relógio de NY (o relógio pula de 1h59 para 3h, ADR 0009). As horas
vizinhas do mesmo dia:

| Hora | Corridas |
|---|---|
| 0h | 43.306 |
| 1h | 34.794 |
| **2h** | **85** (59 zonas, ~1,4 por zona) |
| 3h | 27.698 |
| 4h | 19.668 |

Uma hora normal naquele horário tem ~30 mil. As 85 são artefato de dado (relógio de aparelho errado ou registro
gravado durante a virada): **0,0004% do mês**. A exclusão feita pelo model está correta — incluir essa hora criaria
demanda falsa para o modelo aprender.

**Conserto:** o teste passou a aplicar a mesma regra nas duas pontas, comparando só horas que existem. E o artefato
deixou de ser silencioso: o teste `ml_demanda_hora_inexistente_aviso` (severidade **warn**) reporta o volume
descartado e falha só se passar de 1.000 corridas — se um dia virar milhares, deixou de ser artefato e passou a ser
problema de fuso na Silver.

### 2.2 Duas coisas que a medição confirmou funcionando

| O que | Evidência |
|---|---|
| Filtro semântico de zonas | Nos meses reais a soma fica 999 a 1.181 corridas abaixo da fato. Em fev/2026: 999 em 19,87 M = **0,005%**, exatamente o custo medido no passo 1 de excluir Newark, 264 e 265 |
| Exclusão da hora inexistente | Todo março tem 194.666 linhas em vez de 194.928. A diferença é 262 = 1 hora × 262 zonas |

### 2.3 Cobertura de testes

11 nós pelo seletor `tag:ml` (1 model + 10 testes), todos verdes, zero avisos:

| Teste | O que garante |
|---|---|
| `unique_combination_of_columns` (hora, zona_id) | O grão declarado é real |
| `not_null` em hora, zona_id, qtd_corridas, ano_mes | Nenhuma chave nula |
| `accepted_range` em qtd_corridas (≥ 0) | Demanda negativa não passa |
| `relationships` zona_id → dim_zona | Nenhuma zona órfã |
| `reconciliacao_ml_demanda` | Nenhuma corrida perdida na soma de operadoras nem na grade |
| `ml_demanda_sem_mes_fantasma` | O defeito 1 não pode voltar |
| `ml_demanda_hora_inexistente_aviso` (warn) | O artefato do horário de verão não cresce em silêncio |

**Detalhe de seleção:** o teste de aviso lê a fato direto, sem `ref()` do model, então o seletor
`ml_demanda_hora_zona+` não o alcançava e ele não rodava. Resolvido com a etiqueta `ml`, a mesma que a DAG
`ml_forecast` vai usar — e por isso a conferência final foi feita com `--select tag:ml`, a seleção de verdade.

---

## 3. A tabela de features: `ml_features_demanda` (passo 2b)

**Data:** 14/11/2026
**Arquivos:** [`dbt/models/marts/ml_features_demanda.sql`](../../dbt/models/marts/ml_features_demanda.sql),
2 testes antivazamento em `dbt/tests/`, documentação e testes genéricos em `_gold.yml`
**Construído em:** dev (4 meses → 4 cortes), **766.874 linhas**, 12,8 s
**Custo:** 3,3 MB nas consultas de conferência

### 3.1 O grão tem três partes, e isso é consequência da decisão D1

Os lags são medidos a partir do **corte**, não da hora-alvo. Então o mesmo par (hora, zona) tem lags diferentes
conforme o corte usado, e o grão precisa ser **corte × hora-alvo × zona**, com `horizonte_horas` como feature.

A intuição que ficou: no fim do mês você tira **uma** foto da rua. Perguntam sobre o dia 16 e sobre o dia 30, e
você olha a **mesma** foto nas duas vezes. O que muda é só quanto ela ajuda.

O alternativa — medir o lag da hora-alvo — é possível, porque o histórico inteiro está no disco. Mas treinaria o
modelo com informação mais fresca do que a produção tem: parado no fim de abril, a sexta mais recente é 24/04, três
semanas antes do alvo de 15/05, e não a sexta de 08/05. Isso é **desalinhamento treino-produção**, vazamento
disfarçado de inconsistência.

### 3.2 Os cortes, medidos

| `mes_corte` | Corte | `mes_alvo` | Linhas | Horizonte | Com alvo | Sem alvo |
|---|---|---|---|---|---|---|
| 2026-02 | 2026-02-28 23:00 | 2026-03 | 194.666 | 1 a 744 | 194.666 | 0 |
| 2026-03 | 2026-03-31 23:00 | 2026-04 | 188.640 | 1 a 720 | 188.640 | 0 |
| 2026-04 | 2026-04-30 23:00 | 2026-05 | 194.928 | 1 a 744 | 194.928 | 0 |
| 2026-05 | 2026-05-31 23:00 | 2026-06 | 188.640 | 1 a 720 | **0** | **188.640** |

O último corte é o **"dia de valer"**: o mês-alvo não existe na amostra de dev, então `tem_alvo` é falso em todas
as linhas. O caminho da previsão de verdade ficou exercitado em dev, antes de produção.

### 3.3 A prova de que não há vazamento

Duas evidências independentes, as duas viraram teste:

**1. A mesma foto** (`ml_features_mesma_foto`). Para cada corte × zona × hora da semana, o número de valores
**distintos** de cada lag é exatamente **1**:

| `mes_corte` | Combinações | Valores distintos de `lag_1` | de `lag_4` |
|---|---|---|---|
| 2026-02 a 2026-05 | 44.016 cada | 1 | 1 |

As 44.016 combinações são 168 horas da semana × 262 zonas. Se o lag tivesse vindo da hora-alvo, haveria mais de um
valor por combinação.

**2. A foto está no passado** (`ml_features_lag_no_passado`). A coluna `hora_lag_1` guarda a data em que a foto foi
tirada, justamente para que a afirmação seja testável e não apenas declarada. O teste falha se `hora_lag_1 > corte`
ou se `horizonte_horas <= 0`. Passou.

Os dois testes foram rodados por nome, para confirmar que a seleção os alcança.

### 3.4 Os nulos têm explicação exata

| `mes_corte` | Nulos em `lag_4_semanas` | Linhas |
|---|---|---|
| 2026-03 | **1.048** | 188.640 |
| os outros 3 | 0 | — |

A conta: o corte é 31/03 23h; a última ocorrência de "domingo 2h" antes dele é 29/03; voltando 4 semanas cai em
**2026-03-08 02:00**, a hora que não existe no relógio de NY (ADR 0009, seção 2.1 deste documento). Abril tem 4
domingos, então 4 horas-alvo × 262 zonas = **1.048**. Nenhum outro nulo em nenhum lag.

Fica nulo de propósito: o LightGBM trata nulo nativamente, e virar zero ensinaria demanda falsa.

### 3.5 Calendário e clima

| Item | Evidência |
|---|---|
| Feriado observado (D2) | Memorial Day (segunda, 25/05) e Juneteenth (sexta, 19/06) marcados com 24 horas × 262 zonas. O caso com data deslocada (4/7/2026, sábado, observado na sexta 3/7) está fora da amostra de dev e será conferido em produção |
| Clima | Colunas com prefixo `clima_obs_*`, deliberado: é o vazamento **aceito** da spec 9.1. Em produção só existiria previsão do tempo, com erro; aqui usamos o observado, o que deixa o resultado otimista |

### 3.6 Sanidade do alvo contra os lags

| `mes_corte` | Média do alvo | Média `lag_1` | Média `lag_4` | Máx. do alvo |
|---|---|---|---|---|
| 2026-02 | 113,29 | 99,13 | 118,32 | 1.465 |
| 2026-03 | 111,29 | 111,31 | 113,99 | 1.563 |
| 2026-04 | 113,49 | 116,72 | 106,12 | 1.686 |
| 2026-05 | — (dia de valer) | 107,11 | 114,65 | — |

Mesma ordem de grandeza em todas as colunas, como esperado: a demanda não muda de escala de um mês para o outro.

### 3.7 Cobertura de testes

24 nós pelo seletor `tag:ml` (2 models + 22 testes), todos verdes, zero avisos. Os 12 da `ml_features_demanda`:
grão único em (corte, hora-alvo, zona); não-nulos nas chaves, em `horizonte_horas`, `tem_alvo`, `mes_corte` e
`mes_alvo`; `horizonte_horas` entre 1 e 744; relacionamento de zona; e os dois antivazamento.

---

## 4. O baseline: `ml_baseline_demanda` (passo 3, ✍️ Ronald)

**Data:** 14/11/2026
**Autoria:** lógica do Ronald (array filtrado, regra do nulo, cast para double). Refactor pedido por ele e feito
pelo Claude: CTE, comentários e padronização de caixa — sem mudança de resultado, provado abaixo.
**Construído em:** dev, **766.874 linhas** (idêntico à tabela de features: o grão foi preservado)

### 4.1 Os cinco cenários, auditados

| # | Cenário | Decisão | Medido |
|---|---|---|---|
| 1 | 4 lags preenchidos | média simples dos quatro | 765.826 linhas, **todas** conferem |
| 2 | 1 lag nulo | média dos **três** que existem | 1.048 linhas, **todas** conferem |
| 3 | 4 lags nulos | nulo, protegido por `nullif` | não ocorre (0 linhas), proteção mantida |
| 4 | média fracionária | não arredondar | 562.391 de 766.874 fracionários (73%) |
| 5 | linhas do "dia de valer" | entram | 188.640 linhas com palpite e sem gabarito |

765.826 + 1.048 = 766.874: toda linha auditada.

### 4.2 A armadilha de SQL que o cenário 2 esconde

`AVG()` ignora nulos quando agrega **linhas**, mas aritmética entre **colunas** propaga nulo. Então
`(lag_1 + lag_2 + lag_3 + lag_4) / 4` devolveria **nulo** sempre que um dos quatro fosse nulo, e não a média dos
outros três. A solução usada: montar um array, filtrar os nulos, somar com `reduce()` e dividir por
`cardinality()`.

E um detalhe que não é estético: a semente do `reduce` é `cast(0 as double)` porque, em Trino, **divisão entre
inteiros trunca**. Os lags são `bigint`; com semente inteira o baseline viraria número redondo sem ninguém pedir.
Os 73% de valores fracionários são a prova de que o cast está fazendo trabalho.

### 4.3 O refactor não mudou o resultado

Impressão digital da tabela antes e depois, idêntica em todos os agregados:

| Medida | Antes | Depois |
|---|---|---|
| Linhas | 766.874 | 766.874 |
| Nulos | 0 | 0 |
| Soma | 86.263.334,8333 | 86.263.334,8333 |
| Média | 112,48697287 | 112,48697287 |
| Soma em milésimos | 86.263.334.852 | 86.263.334.852 |

A soma em milésimos é a medida sensível: qualquer valor alterado em qualquer linha mudaria esse inteiro.

### 4.4 O WAPE do baseline — e por que isso muda o enquadramento da fase

Medição exploratória (o cálculo oficial é o passo 4, peça ✍️ do Ronald):

| Mês previsto | WAPE do baseline |
|---|---|
| mar/2026 | **14,37%** |
| abr/2026 | **13,18%** |
| mai/2026 | **13,08%** |

**Este é um baseline forte.** Prever demanda por hora e por zona, um mês à frente, errando 13% — com a média de
quatro números e nada mais. A série tem sazonalidade semanal muito regular e nível estável, e a janela de 4 semanas
captura quase tudo isso.

É exatamente o cenário anunciado na Aula 1: em muitas séries reais o baseline ganha. A barra para o LightGBM está
alta, e a possibilidade de o modelo **não** vencer é concreta. A spec 9.1 já prevê essa saída, e o entregável nesse
caso é o relatório honesto, não um modelo forçado.

### 4.5 Cobertura de testes

35 nós pelo seletor `tag:ml` (3 models + 32 testes), todos verdes. O teste central do baseline é
`ml_baseline_e_media_dos_lags`: ele recalcula a média por uma fórmula **diferente** da do model (aritmética de
coluna com `coalesce` e contagem explícita de não-nulos, em vez de array) e exige o mesmo número. Duas fórmulas
distintas chegando ao mesmo resultado é verificação; a mesma fórmula repetida seria tautologia.

---

## 5. O WAPE do baseline: `ml_wape_baseline` (passo 4, ✍️ Ronald)

**Data:** 15/11/2026
**Grão:** `mes_alvo` — uma linha por rodada do backtest
**Autoria:** fórmula, agregações condicionais e a coluna `vies_pct` do Ronald. O Claude revisou, apontou os erros
e aplicou o `coalesce` e os comentários a pedido dele.

### 5.1 O resultado

| `mes_alvo` | Linhas avaliadas | `corridas_reais` | `erro_absoluto_total` | `wape_pct` | `vies_pct` |
|---|---|---|---|---|---|
| 2026-03 | 194.666 | 22.054.617 | 3.169.491,0 | **14,37** | −1,42 |
| 2026-04 | 188.640 | 20.993.068 | 2.767.758,2 | **13,18** | +2,20 |
| 2026-05 | 194.928 | 22.122.269 | 2.894.305,5 | **13,08** | −0,66 |

Linhas e corridas descartadas por falta de palpite: **0** nas três rodadas.

### 5.2 O que o `vies_pct` revelou — e isso muda a leitura da fase

Coluna acrescentada pelo Ronald **fora do contrato pedido**, e é a informação mais importante desta seção.

O WAPE é absoluto, então não distingue dois mundos muito diferentes: errar **sempre 13% para cima** (viés
sistemático, fácil de corrigir) de errar **13% para lá e para cá** (dispersão, difícil de corrigir).

Medido: −1,42%, +2,20%, −0,66%. Viés pequeno e **alternando de sinal**. O baseline é praticamente **não
enviesado**, e portanto aqueles 13% não são um desvio esquecido de calibrar — são **ruído intrínseco do grão
hora × zona**.

Consequência prática: se o viés fosse +10% constante, o LightGBM ganharia fácil só aprendendo a subtrair. Com viés
de 1% e sinal trocando, os 13% são a variabilidade real da demanda naquele grão. **A barra é mais alta do que o
WAPE sozinho sugeria.**

### 5.3 O bug encontrado na revisão: numerador e denominador em desacordo

Na primeira versão, se `previsao_baseline` fosse nulo numa linha:

| Peça | Comportamento com nulo |
|---|---|
| `count(*)` | **conta** a linha |
| `sum(qtd_corridas)` | **soma** o real → denominador cresce |
| `sum(abs(qtd_corridas - previsao_baseline))` | expressão vira nula → `sum` **ignora** → numerador **não** cresce |

Denominador maior, numerador igual: **WAPE artificialmente menor**. Sem erro, sem teste vermelho, e com a métrica
parecendo **melhor** — a assinatura do vazamento descrita na Aula 2.

A raiz: das quatro agregações, a única que **não mencionava** `previsao_baseline` era `sum(qtd_corridas)`. As
outras três já se restringiam sozinhas às linhas com palpite, porque expressão com nulo vira nula e o `sum`
ignora. O bug estava exatamente no único ponto de assimetria.

Hoje não ocorre (0 nulos), mas foi corrigido por dois motivos: as previsões do modelo vêm do Python no passo 5,
onde nulo é plausível; e esta lógica será reaproveitada na `ml_backtest_metricas` do passo 6.

**Conserto:** agregações condicionais nos dois lados, mais duas colunas que tornam o descarte visível —
`qtd_linhas_sem_baseline` e `qtd_corridas_sem_baseline`. Cinco linhas descartadas é pouco; cinco linhas com 4.000
corridas é muito, e só a segunda coluna distingue os dois casos.

### 5.4 Três tropeços do percurso, registrados porque ensinam

| Tropeço | O que ensinou |
|---|---|
| `countif` em vez de `count_if` | O Athena respondeu `FUNCTION_NOT_FOUND` e resolveu sozinho |
| `count_if(previsao_baseline)` e `case when previsao_baseline then` | `previsao_baseline` é **número**, não booleano. Vinha de copiar a forma de `count_if(is_dropoff_cbd)` da Fase 3, onde o argumento já era uma marca `is_*`. Em SQL não existe `sumif`: a condição vai **dentro** do argumento, com `case when` |
| As duas colunas de descarte calculadas na CTE e ausentes do `select` final | Uma CTE só entrega o que a consulta de fora pede. E a ironia: as colunas cujo trabalho era impedir que algo desaparecesse em silêncio desapareceram em silêncio |

E uma assimetria do SQL que virou `coalesce`: `count_if` sobre conjunto vazio devolve **0**, mas `sum` sobre
conjunto vazio devolve **nulo**. Sem o `coalesce`, as duas colunas descreveriam a mesma situação com respostas
diferentes — uma dizendo "zero", a outra "não sei".

### 5.5 Cobertura de testes

45 nós pelo seletor `tag:ml` (4 models + 41 testes), todos verdes, zero avisos.

---

## 6. As tabelas em produção e o baseline sobre 32 rodadas (passo 5.0)

**Data:** 15/11/2026
**Comando:** `dbt build --select tag:ml --target prod`, com autorização explícita do Ronald
**Resultado:** 45 nós verdes em **2 min 08 s**, zero avisos. Nenhuma tabela existente foi tocada
**Tamanhos:** `ml_demanda_hora_zona` e `ml_features_demanda` ~6,3 M linhas; `ml_baseline_demanda` 6.312.366;
`ml_wape_baseline` **32 rodadas avaliáveis**

### 6.1 As 6 rodadas do backtest — a barra oficial

| Mês previsto | WAPE | Viés |
|---|---|---|
| 2026-04 | 13,18% | +2,20 |
| 2026-05 | 13,08% | −0,66 |
| 2026-06 | 14,16% | +1,55 |
| 2026-07 | 14,90% | +3,63 |
| 2026-08 | 13,13% | +1,73 |
| 2026-09 | 16,09% | −6,46 |

**Média das seis: 14,09%.** Linhas sem palpite nas 32 rodadas: **0**.

**Correção de um número dado antes.** Com as 3 rodadas de dev (seção 5.2) o viés absoluto médio parecia ~1,4%.
Sobre as 32 rodadas de produção ele é **3,03%** — três vezes maior. A conclusão qualitativa se mantém (o sinal
alterna, a maior parte do erro é dispersão e não desvio), mas o número anterior estava otimista por amostra pequena.

### 6.2 O achado: o erro do baseline é SAZONAL e se repete ano a ano

Sobre as 32 rodadas, o WAPE do baseline não é ruído — tem calendário:

| Mês previsto | 2024 | 2025 | 2026 |
|---|---|---|---|
| **dezembro** | **20,60%** | **20,86%** | — |
| **janeiro** | — | **19,37%** | **23,15%** |
| novembro | 16,15% | 16,61% | — |
| setembro | 15,74% | 16,46% | 16,09% |
| julho | 15,98% | 15,32% | 14,90% |
| abril | 13,57% | 12,15% | 13,18% |
| outubro | 12,46% | 12,96% | — |

Faixa completa: mínimo **12,15%** (abr/2025), máximo **23,15%** (jan/2026), média **15,09%**.

A repetição entre anos é o que dá confiança ao padrão: dezembro deu 20,60 e 20,86; novembro, 16,15 e 16,61;
setembro, 15,74 / 16,46 / 16,09.

**A explicação é a frase da Aula 1:** *o baseline reage, nunca antecipa.* As quatro semanas anteriores ao Natal
não contêm nenhum Natal. O baseline chega em 25 de dezembro olhando quatro quintas-feiras comuns e prevê um dia
comum. Erra muito, e erra **todo ano no mesmo lugar**.

### 6.3 A consequência para o desenho do experimento

O modelo tem `is_feriado_observado` e `nome_feriado_observado` como features: ele **pode** aprender o
comportamento do Natal olhando os dezembros anteriores. É exatamente a brecha estrutural onde ele vence o baseline.

Mas as 6 rodadas que a spec 9.1 define são **abril a setembro de 2026** — nenhum dezembro, nenhum janeiro. Por
acidente de onde os dados terminam, a avaliação oficial cai justamente nos meses em que o baseline está no seu
melhor (13 a 16%) e o modelo tem o menor espaço para ganhar.

**Decisão (15/11/2026):** manter as **6 rodadas da spec como resultado oficial** da fase e reportar, **além**
delas, o WAPE das 32 rodadas com a quebra por mês do ano. Custa quase nada, porque a tabela de features já cobre
os 32 cortes, e é onde a informação interessante está: não "o modelo é melhor?", mas "**onde** o modelo é melhor?".

Sem ADR: a spec não é contrariada, apenas complementada.

---

## 7. A leitura do Athena para o pandas: medição dos modos (passo 5, decisão B)

**Data:** 15/11/2026
**Arquivos:** [`airflow/include/ml/dados.py`](../../airflow/include/ml/dados.py),
[`scripts/fase-5/medir_leitura.py`](../../scripts/fase-5/medir_leitura.py)
**Tabela medida:** `gold.ml_features_demanda`, **6.312.366 linhas**, 24 colunas

### 7.1 O resultado

| modo | segundos | memória | efeito colateral |
|---|---|---|---|
| csv | 159,5 | 421,4 MB | nenhum |
| **unload** | **27,6** | **421,4 MB** | nenhum no catálogo |
| ctas | não medido | — | **cria tabela temporária no banco da consulta** |

**Escolhido: `unload` — 5,8x mais rápido, mesma memória, dado idêntico.** O `ctas`, que é o padrão da
biblioteca, não foi medido de propósito: ele criaria tabela temporária no `gold` de **produção**, e catálogo de
produção não é lugar de rascunho para benchmark. Como o `unload` entrega o mesmo Parquet sem tocar o catálogo, o
`ctas` ficou irrelevante.

Verificação de equivalência embutida no script: as duas leituras devolvem o **mesmo número de linhas** e a **mesma
soma do alvo**. Modo de transporte não pode mudar conteúdo.

### 7.2 Três obstáculos do UNLOAD, e o que cada um ensinou

| # | Erro | Causa | Conserto |
|---|---|---|---|
| 1 | `NOT_SUPPORTED: Incorrect timestamp precision for timestamp(6)` | O Iceberg cria `timestamp(6)` (microssegundo) e o UNLOAD do Athena só exporta Parquet até **milissegundo** | `cast(hora_alvo as timestamp(3))` na consulta. Sem perda: é hora cheia |
| 2 | `HIVE_PATH_ALREADY_EXISTS` | O UNLOAD exige pasta de destino **vazia**, e o local de resultados do workgroup já tem arquivos | Um prefixo único por leitura, apagado depois (`keep_files=False`) |
| 3 | `NotImplementedError: dictionary<values=int32, indices=int32>` | Pedir `zona_id` (número) como categoria na leitura: o leitor de Parquet não converte dicionário de inteiros | O parâmetro `categories` passa a receber **só texto**. O `zona_id` fica `int32` e é declarado categórico direto ao LightGBM |

### 7.3 O achado sobre as categorias

O parâmetro `categories` do awswrangler é **respeitado no modo csv e ignorado no modo unload**. No unload o texto
voltava como `string`:

| Coluna | Como `string` | Como `category` |
|---|---|---|
| `mes_corte` | 91,1 MB | desprezível |
| `mes_alvo` | 91,1 MB | desprezível |
| `tipo_dia_observado` | 89,0 MB | desprezível |
| `nome_feriado_observado` | 51,3 MB | desprezível |

Total: **322 MB** de texto, que levavam o unload de 421 MB para **719,7 MB**.

**Conserto:** a conversão para categoria passou a ser garantida **depois** da leitura, em `aplicar_tipos`, e não
apenas pedida nela. Com isso os dois modos terminam com os mesmos tipos e o mesmo tamanho — o modo de transporte
não muda o conteúdo **nem a forma**. A conversão é feita coluna por coluna de propósito: um `astype` do DataFrame
inteiro criaria uma segunda cópia completa antes de liberar a primeira, e pico de memória é o que mata contêiner.

### 7.4 Memória: a estimativa estava boa

Estimado na Aula 4 a partir dos dtypes escolhidos: **457 MB**. Medido: **415,4 MB** (erro de 9%).

Duas colunas foram cortadas no caminho, com a medição na mão:

| Decisão | Economia |
|---|---|
| Não ler a coluna `corte` (timestamp): existe um corte por mês e o `mes_corte` já o identifica | **48,2 MB** |
| `zona_id` como `int32` simples em vez do `Int32` anulável do pandas (ele nunca é nulo, tem teste) | **6,0 MB** |

Conferido ao fim: **nenhum dtype anulável** sobrou no DataFrame. O LightGBM lida mal com os tipos de extensão do
pandas, e isso evita uma conversão silenciosa na hora do treino.

### 7.5 Correção ao passo 0: o LightGBM não carrega no macOS sem `libomp`

No passo 0 eu conferi que **existe wheel** do `lightgbm` para o Python 3.14 e declarei o risco inexistente. Estava
**incompleto**: verifiquei que o pacote instala, não que ele carrega.

No Mac, o import falha:

```
OSError: Library not loaded: @rpath/libomp.dylib
  tried: '/opt/homebrew/opt/libomp/lib/libomp.dylib' (no such file)
```

O LightGBM depende de uma biblioteca nativa de paralelismo (OpenMP) que no macOS não vem no pacote. Conserto no
Mac: `brew install libomp`.

No Linux da imagem do Airflow o OpenMP costuma já estar presente, mas isso está **NÃO VERIFICADO** — será
conferido antes de afirmar. O ambiente de execução de verdade é o contêiner (spec 9.1), então o Mac só importa
para desenvolvimento.

**Lição:** "a wheel existe para esta versão de Python" e "a biblioteca carrega nesta máquina" são duas perguntas
diferentes. A primeira se responde no PyPI; a segunda só com um `import`.
