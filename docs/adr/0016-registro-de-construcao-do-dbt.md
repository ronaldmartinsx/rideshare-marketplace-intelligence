# ADR 0016: Registro de construção do dbt e regra de pendência por mês

- **Status:** Decidido e validado na Fase 3 (mês adulterado barrado na etapa 9; 32 meses de produção registrados na etapa 10)
- **Data:** 24 e 25/10/2026; escrito em 28/10/2026
- **Fase:** 3
- **Relacionado:** ADR 0003 (Bronze versionada), ADR 0005 (partição por `source_month`), ADR 0014 (incremental)

## Contexto

A DAG `dbt_build` precisa responder, a cada chegada de dado novo na Bronze: **quais meses devem ser construídos (ou reconstruídos) na Silver e na Gold?**

- O **manifesto** (`controle.manifesto_vigente`, Fase 2) responde "qual versão de cada mês é a vigente na Bronze?". Esse é o lado da ingestão.
- Falta o lado do consumidor: **"a Silver e a Gold deste ambiente já foram construídas, com sucesso, a partir dessa versão?"**

O plano (F5) previa comparar o `ingest_ts` vigente do manifesto com o `ingest_ts` gravado na Silver. Na etapa 8 apareceram três problemas:

1. **A Silver pode estar atualizada com a Gold barrada.** Quando o gate de volume reprova um mês, a `int_trips_enriched` já foi gravada com a versão nova, mas a Gold não (provado na etapa 9). Comparando com a Silver, o mês pareceria "em dia" e nunca seria tentado de novo.
2. **Dev e prod leem a mesma Bronze**, mas são construídos em momentos diferentes. A resposta precisa ser por ambiente.
3. **Não haveria histórico** de quando e por que cada mês foi construído: dado novo, pedido manual ou disparo à mão.

## Decisão

### O registro

A tabela Iceberg **`controle.dbt_meses_construidos`** recebe uma linha por construção que deu certo, só com INSERT:

```
ambiente | source_month | ingest_ts_tlc | ingest_ts_clima | motivo | construido_em | dag_run_id
```

- `motivo`: `manifesto` (versão nova na Bronze), `forcado` (pedido em `forcar_meses`) ou `manual` (disparo direto da `dbt_mes`).
- A view **`dbt_meses_construidos_vigente`** devolve a última construção de cada (ambiente, mês).
- Quem grava é a **última task da `dbt_mes`** (`registrar_construcao`). Ela só roda se **todas** as tasks do dbt ficarem verdes: models, testes, gate de volume e reconciliações.
- As versões gravadas são **lidas da Silver** (`max(ingest_ts)` das stagings do mês), não do manifesto. O registro diz o que o dbt de fato leu.

### A regra de pendência (desenhada pelo Ronald, 25/10/2026)

Para cada mês, nesta ordem:

| # | Condição | Decisão | Motivo |
|---|---|---|---|
| 1 | Falta a versão vigente da TLC ou do clima na Bronze | Não constrói (espera). Se o mês foi forçado, o run fica **vermelho** no fim | "sem versão vigente de …" |
| 2 | Registro ≠ versões vigentes, ou mês nunca construído | Constrói | `manifesto` |
| 3 | Mês pedido em `forcar_meses` | Constrói | `forcado` |
| 4 | Caso contrário | Não constrói | já em dia |

- **O manifesto tem precedência sobre o pedido manual:** um mês com TLC nova e forçado é registrado como `manifesto`, porque o dado mudou.
- **A regra decide SE o mês é construído.** A macro `ingest_ts_vigente` decide QUAL versão é lida.
- Os meses saem **do mais antigo para o mais novo, um por vez**: o gate de um mês compara com os 3 anteriores.

### Uma DAG por ambiente

- **`dbt_build_prod`** é disparada pelos Assets da Bronze (TLC ou clima) e avalia todos os meses do manifesto.
- **`dbt_build_dev`** só roda à mão e é uma **amostra**: avalia só os meses que já estão no registro de dev e os forçados.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Comparar o manifesto com o `ingest_ts` da Silver (plano F5) | Problema 1 acima: o mês barrado pelo gate ficaria "em dia" para sempre |
| Comparar com a Gold | A Gold não guarda `ingest_ts`. Mesmo com a coluna, a Gold pode estar gravada com uma reconciliação que falhou depois |
| Estado do Airflow (XCom, Variables, histórico de runs) | Não é consultável pelo Athena, e se perde se o Airflow local for recriado. O registro fica no lake, junto do manifesto |
| `dbt state:modified` / `dbt source freshness` | Detectam mudança de código ou atraso, não "qual versão do dado cada mês usou" |
| Reconstruir tudo a cada chegada | 32 meses ≈ 3h20 e ~US$ 0,59 por disparo, para mudar um mês |

## Consequências

**Ganhamos:**
- **Mês que falha volta sozinho:** sem linha nova no registro, ele continua pendente no próximo run. É o que substitui o retry nas tasks de teste (etapa 11).
- **Checkpoint auditável em SQL:** quem construiu, quando, com qual versão e por quê.
- Dev e prod independentes: construir um mês em dev não o marca como feito em prod.
- Evidência: na etapa 9, a Silver de dev foi atualizada e a Gold barrada, e o registro ficou intocado. Na etapa 10, os 32 meses de prod foram registrados com as versões iguais às do manifesto.

**Perdemos / cuidados:**
- **Mudança de código do dbt não é detectada:** registro e manifesto continuam iguais. Reconstruir exige `forcar_meses` (linha 3), e esse pedido manual é responsabilidade de quem muda o código.
- Rodar o dbt pela CLI, fora da `dbt_mes`, não grava registro. No próximo run o mês é reconstruído. É seguro (idempotente, ADR 0014), mas custa uma construção.
- Uma tabela a mais para manter: ela recebe OPTIMIZE + VACUUM semanal na DAG `manutencao_iceberg` (banco `controle`, retenção de 90 dias).
