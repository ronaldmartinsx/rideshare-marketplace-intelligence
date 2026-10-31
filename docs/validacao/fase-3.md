# Relatório de validação — Fase 3 (Silver e Gold)

Evidências de que a Silver e a Gold estão completas, testadas e protegidas pelo gate (o "pronto quando" da fase, spec seção 12), e das decisões F1 a F12 e B1 a B6. Datas: 19 a 28/10/2026.

- **Pronto quando 1, "a reconciliação entre Silver e Gold bate":** ✅ em produção, nos 32 meses (seção 8): 651.163.831 corridas válidas na Silver = 651.163.831 na Gold.
- **Pronto quando 2, "o gate barra um mês adulterado de propósito":** ✅ em dev, pela CLI do dbt e pelo Airflow (seção 7): desvio −49,5% e +101,9%; Gold e registro intocados.
- **Ambiente:** dbt-core 1.12.5, dbt-athena 1.11.1, dbt-utils 1.4.1, Astronomer Cosmos 1.15.1, Airflow 3.3.2 (Astro Runtime 3.3-9, Python 3.14). 102 testes automatizados (`airflow/tests/`).

---

## 1. O dado antes das regras (jan/2025 e perfil de 3 meses)

Medido em `dev_silver` antes de escrever as regras de qualidade (20 e 21/10/2026):

| Pergunta | Evidência | Virou |
|---|---|---|
| Existe chave natural? | Não. Licença + horários + zonas: **27 colisões** (corridas compartilhadas, tarifas diferentes). 25 colunas: 0 colisões | ADR 0004 |
| Há duplicatas exatas? | 0 nos 3 meses de dev (em produção: 17, seção 8) | ADR 0004 |
| Corridas na virada do mês? | 100% das corridas do arquivo de janeiro embarcaram em janeiro | Teste "mês do embarque = `source_month`" (ADR 0005) |
| Espera negativa (embarque antes do pedido)? | ~1% das corridas (184 mil a 276 mil por mês): a maior categoria | `is_valid_wait_metric` (nível métrica) |
| Zonas 264/265 (Unknown / Outside NYC)? | ~4% das corridas, viagens reais | `is_zona_conhecida` na `dim_zona`, sem invalidar |
| Tarifa ≤ 0? | 633 / 17.204 / 11.921 nos 3 meses | `is_valid_economic_metrics` (nível métrica) |
| Milhas ≤ 0 / velocidade > 100 mph / espera > 2 h | ~2,4 mil / ≤ 9 / ~25 por mês | `is_valid` (corrida) / `is_valid` / `is_valid_wait_metric` |

## 2. Achados técnicos que mudaram o código

| Achado | Evidência | Correção |
|---|---|---|
| Conversão de fuso no Athena | `cast(ts AT TIME ZONE 'America/New_York' AS timestamp)` **não converte** (devolve a hora UTC); `date_format` + `date_parse` converte | Staging do clima com `date_format` + `date_parse` (ADR 0009) |
| `--full-refresh` em incremental Iceberg com pasta compartilhada | Apagou a `int_trips_enriched` de dev: o rename + drop do `__bkp` apaga a pasta, que era a mesma da tabela nova (**incidente, erro do Claude Code**) | `+s3_data_naming: schema_table_unique` em todos os models e seeds |
| Seeds no bucket de resultados | Seeds Hive iam para o local imposto pelo workgroup, que expira em 7 dias | Seeds viraram Iceberg no lake |
| `on_schema_change: ignore` | Coluna nova no model foi descartada em silêncio na tabela incremental | `+on_schema_change: fail` |
| Limite de 1 GiB por consulta (F9) | O incremental copia o mês inteiro da temporária para a final; um mês da `int` tem ~1,3 GB | Limite revisado para **3 GiB** (apply do Ronald). Maior consulta do build de produção: 1,46 GiB |
| `--exclude` de um model no dbt | Leva junto os testes do model (seleção indireta): o gate nem rodaria | Seleção explícita: `"int_trips_enriched,resource_type:test" "fct_*+"` |
| `astro dev pytest` | Sobe um container sem a pasta `dbt/` montada: o Cosmos não acha o `dbt_project.yml` | Testes da `dbt_mes` rodam dentro do scheduler |

## 3. Testes da Silver e o gate de volume (etapa 5)

- **Freshness** no manifesto (último `aceito` da TLC): aviso com 45 dias, erro com 75. PASS.
- **Testes da `int_trips_enriched`:** 10, todos com `where` do mês. Limites calibrados com os 3 meses de dev e conferidos nos 32 de produção (seção 8).
- **Clima:** 24 horas por dia (teste do teste: falha quando um dia é cortado).
- **✍️ Gate de volume do Ronald** (`dbt/tests/generic/volume_mensal.sql`): média diária de corridas válidas × média dos até 3 meses anteriores existentes. Aviso com ±20%, erro com ±30%.
  - Calibração: desvio normal de −7,0% (2024-07) a +8,3% (2025-10), medido nos 32 meses de produção. Nenhum mês chegou ao aviso.
  - Primeiro cenário em dev (2026-05 contra 2026-02 a 04): +0,94%.

## 4. Gold (etapa 6)

| Model | Evidência |
|---|---|
| `fct_demanda_zona_hora` | Reconciliação em dev (2026-05): 22.123.450 = 22.123.450 |
| `fct_espera_histograma` | P90 de Manhattan, 18h de dia útil, mai/2026: **9,30** pelo histograma × **9,25** pelas corridas. Tamanho: tabela da seção 9 |
| `fct_od_diario` | Dimensão de zona em dois papéis (origem e destino). 55,3 milhões de linhas nos 32 meses (a maior tabela da Gold) |
| `dim_tempo_hora` | 2024–2026 por hora local; a hora "inexistente" de março existe de propósito (85 corridas em 09/03/2025) |

## 5. dbt docs (etapa 7)

Linhagem do manifesto declarada nas stagings (`-- depends_on: {{ source('controle', 'manifesto_vigente') }}`), porque a macro `ingest_ts_vigente` o lê fora do `ref`/`source` normal. Print do grafo: `docs/validacao/img/fase-3-linhagem.png`.

## 6. Orquestração (etapa 8)

| Teste | Esperado | Resultado |
|---|---|---|
| `dbt_mes_dev` com 2026-05 | Verde, uma task por model | ✅ 33 tasks, 52 testes PASS (antes do `registrar_construcao`) |
| `dbt_build_dev` forçando `2026-05` e `2205-01` (mês inexistente) | Constrói 2026-05; run vermelho pelo pedido impossível | ✅ 2026-05 construído com motivo `manifesto` (nunca estava no registro de dev); `tudo_certo` vermelho: "2205-01 (sem versão vigente de TLC e clima na Bronze)" |
| `dbt_build_dev` de novo, sem forçar | Nada a construir; verde | ✅ |
| `manutencao_iceberg` (1º run) | Todas as tabelas Iceberg, barato | ✅ 15 tabelas, 0,07 MB lidos; manifesto de 64 arquivos para 1 (`OPTIMIZE`); `stg_tlc` de dev −1,07 GB |
| Ordem dos meses mapeados | Do mais antigo para o mais novo, um por vez | ✅ O scheduler ordena por `map_index` (conferido em `scheduler_job_runner.py`); confirmado nas etapas 9 e 10 |
| Retry nas tasks de teste (etapa 11) | 0 nos testes; ≥ 2 nos models | ✅ `dbt_mes_prod`: 34 tasks, 23 de teste com 0 retries; models com 2, registro com 3 |

Permissões que faltavam na role do Airflow (descobertas no 1º run do Cosmos): `glue:GetTableVersions` e afins, e `athena:GetDataCatalog` / `athena:ListTableMetadata`. Aplicadas pelo Ronald (`infra/terraform/iam_airflow.tf`).

## 7. Mês adulterado (etapa 9, "pronto quando" 2)

**P1, pela CLI do dbt:** metade das corridas de 2026-05 apagada na `int_trips_enriched` de dev; depois `dbt build` dos testes da `int` e da Gold.

| Item | Resultado |
|---|---|
| Gate de volume | **FAIL**, desvio **−49,5%** |
| Gold | **SKIP**: não foi atualizada |

**P2, pelo Airflow:** metade de 2026-02, 03 e 04 apagada; `dbt_build_dev` forçando 2026-05. A referência do gate ficou pela metade, então 2026-05 parece o dobro.

| Item | Previsão do Ronald | Resultado |
|---|---|---|
| Gate | Erro, desvio maior que 30% | ✅ **FAIL, +101,9%** |
| Última task verde | `int_trips_enriched.run` | ✅ |
| Run da `dbt_build_dev` | — | Vermelho |
| Gold e registro de construção | — | Intocados |

**Restauração:** `dbt_build_dev` forçando 2026-02 a 05. Rodou em ordem, ~6 min por mês, verde. Registro: 02 a 04 com motivo `manifesto` (nunca construídos em dev), 05 com `forcado`.

| Mês | Válidas na Silver = corridas na Gold |
|---|---|
| 2026-02 | 19.873.659 |
| 2026-03 | 22.055.790 |
| 2026-04 | 20.994.086 |
| 2026-05 | 22.123.450 |

## 8. Produção: 32 meses (etapa 10, "pronto quando" 1)

| Item | Resultado |
|---|---|
| Run | `dbt_build_prod`, `manual__2026-10-27T23:05:49`: **verde**, 32 de 32 meses, 0 falhas |
| Duração | 23:05 → 02:27 UTC (~3h20, ~6,3 min por mês) |
| Registro (`ambiente = 'prod'`) | 32 linhas, 32 com motivo `manifesto`, **32 com as versões iguais às do manifesto**, 32 runs da `dbt_mes` |
| Bronze (`row_count` do manifesto) × `int_trips_enriched` | **32/32 meses iguais**: 651.246.843 |
| Válidas na Silver × Gold (`fct_demanda_zona_hora`) | **32/32 meses iguais**: 651.163.831 (99,99%) |
| Athena | 2.683 consultas, todas `SUCCEEDED`; 121,78 GiB lidos; maior consulta 1,46 GiB; **US$ 0,59** |

**Corridas inválidas nos 32 meses (nível corrida):**

| Motivo | Corridas | Meses com ocorrência |
|---|---|---|
| `milhas_insuficientes` | 82.785 | 32 |
| `velocidade_impossivel` | 209 | 32 |
| `duplicata_exata` | 17 (Uber: 15 em 2025-10, 1 em 2025-12, 1 em 2026-03) | 3 |
| `tempo_corrida_insuficiente` | 1 | 1 |

**Nível métrica** (corridas válidas, mas fora de uma medida):

| Marca | Total | Maior mês | Limite do teste |
|---|---|---|---|
| Espera inválida | 7.229.721 | 294.672 | aviso > 400 mil |
| Tarifa inválida | 636.406 | 186.022 (2025-08) | aviso > 40 mil: **passou do aviso em 2025-03 (64.208), 2025-08 (186.022) e 2026-01 (100.361)** |
| Corridas inválidas | 83.012 | 4.854 (2026-06) | aviso > 5 mil (perto do limite) |

Os avisos de tarifa não barram o mês, como combinado. Eles reforçam a hipótese da etapa 4 (cada operadora mudou a forma de registrar descontos e estornos), que fica para a Fase 4 (seção 11).

## 9. Evidências dos ADRs (consultas de 28/10/2026)

**ADR 0006, tamanho do histograma em jan/2025:**

| Grão | Linhas |
|---|---|
| Spec: hora do relógio × zona × operadora × 6 faixas | 1.552.010 |
| Hora do relógio × zona × operadora × 18 faixas | 2.986.630 |
| **Adotado** (hora do dia × tipo de dia, 18 faixas) | **473.497** |

Produção: 343.839 a 510.616 linhas por mês (média 434.762); 13,9 milhões no total. P90 da cidade em jan/2025: real 8,05; adotado 8,06; faixas da spec 8,81.

**ADR 0007, lista do CBD contra a cobrança da taxa** (corridas válidas, por zona de destino):

| Período | Menor % pagando, entre as 38 zonas da lista | Maior % pagando, fora da lista |
|---|---|---|
| 05 a 31/01/2025 | 96,2% | 88,2% (sem a zona 105: 3 corridas, todas pagando) |
| ago/2026 | 95,6% | 89,4% |

## 10. Armazenamento e custo (28/10/2026)

| Prefixo | Objetos | GiB |
|---|---|---|
| `bronze/` | 64 | 14,73 |
| `silver/` | 670 | 58,71 |
| `gold/` | 414 | 1,18 |
| `dev_silver/` | 428 | 26,81 |
| `dev_gold/` | 251 | 0,37 |
| `controle/` | 506 | 0,01 |

Total ~102 GiB: ~**US$ 2,30/mês** a US$ 0,023/GB (preço de tabela ⚠️ não conferido na fonte oficial nesta fase). O `dev_silver` guarda arquivos das reconstruções da etapa 9, ainda dentro da retenção de 5 dias. ⚠️ Não verificado: quanto o `VACUUM` de domingo (01/11) vai liberar.

## 11. Pendências (passam para as próximas fases)

- **Tarifa ≤ 0 por operadora** (Fase 4): testar a hipótese mês a mês por operadora (Lyft com zeros em jan/2025, Uber com negativos em 2026) antes de usar a economia no Power BI. Os 3 meses acima do aviso são o ponto de partida.
- **Tamanho da `fct_od_diario`** (Fase 4): 55,3 milhões de linhas é a maior tabela da Gold. Decidir no Power BI: Import com agregação, recorte ou DirectQuery.
- **Limite de corridas inválidas:** o maior mês (4.854) ficou perto do aviso (5 mil). Acompanhar; não recalibrar sem evidência.
- **Herdadas da Fase 2, ainda abertas:**
  - contrato conferindo também `isAdjustedToUTC`;
  - alerta de "aguardando" longo.
- **Da Fase 2, resolvidas aqui:** manutenção do manifesto (`manutencao_iceberg`); `dbt_build` pelos Assets; Silver do clima; horas de troca do horário de verão (`hora_troca_horario_verao`); zonas e seeds; limite do workgroup.
- **Mudança de código do dbt** não é detectada pelo registro: reconstruir exige `forcar_meses` (ADR 0016).
