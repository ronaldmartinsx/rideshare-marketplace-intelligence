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
