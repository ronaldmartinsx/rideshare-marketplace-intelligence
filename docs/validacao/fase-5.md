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
