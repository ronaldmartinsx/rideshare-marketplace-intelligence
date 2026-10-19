# Relatório de validação — Fase 2 (Bronze completa e ingestão automatizada)

Evidências de que a ingestão é idempotente, imutável e detecta republicação (o "pronto quando" da fase, spec seção 12), e das decisões D1 a D11 e W1 a W4. Datas: 16 a 18/10/2026.

- **Pronto quando 1, "rodar a DAG duas vezes não duplica nada":** ✅ no ambiente de teste (7 runs, 6 linhas no manifesto) e em produção (run manual depois do backfill: 32 meses ignorados).
- **Pronto quando 2, "uma republicação simulada gera uma nova versão e marca `is_current`":** ✅ no ambiente de teste (cenário 3: versão nova vira a vigente).
- **Ambiente:** Airflow 3.3.2 (Astro Runtime 3.3-9, Python 3.14), provider da Amazon 9.38.0, pyarrow 26.0.0, dbt-athena 1.11.1. 66 testes automatizados (`airflow/tests/`).

---

## 1. Bronze imutável (etapa 1; ADR 0003)

Política do bucket: nega `PutObject` sem `If-None-Match` em `bronze/*` e `teste_bronze/*`. Testado em `teste_bronze/`, com o perfil de **administrador**:

| Teste | Esperado | Resultado |
|---|---|---|
| `aws s3 cp` (sem o cabeçalho) | Negado | ✅ `AccessDenied ... with an explicit deny in a resource-based policy` |
| `put-object --if-none-match "*"` | Grava | ✅ |
| Mesmo caminho de novo | `412` | ✅ `PreconditionFailed` |

Com a role do Airflow e o código da etapa 6 (`gravar_sem_sobrescrever`): 1ª gravação `gravado`; retry com o mesmo conteúdo `ja_existia`; outro conteúdo no mesmo caminho `RuntimeError` sem sobrescrever; `PutObject` sem o cabeçalho `AccessDenied`.

Achado da etapa 0: o upload gerenciado do boto3 (`upload_file`) **não repassa** o `If-None-Match`; `put_object` e `complete_multipart_upload` repassam. A ingestão usa `put_object` (arquivos de ~500 MB, abaixo do limite de 5 GB) com `ChecksumSHA256`.

## 2. Partition projection (etapas 1 e 10; ADR 0015)

| Consulta em `bronze.tlc_hvfhv` | Resultado |
|---|---|
| Sem filtro de `ingest_ts` | `CONSTRAINT_VIOLATION: ... the WHERE clause must contain only static equality conditions` |
| Com a versão da Fase 1 (`20261012T230806`) | 20.405.666 (0 bytes lidos) |
| Com versão inexistente | 0, sem erro |
| `dbt compile` da Silver para mês sem versão vigente | Erro de compilação: "esperada 1 versão vigente ... encontradas 0" |
| `dbt build` em dev (Silver + Gold, 2025-01) | Silver 20.405.666 na versão `20261012T230806`; Gold 364.630 linhas e 20.405.666 corridas (igual à Fase 1) |

## 3. Identidade do Airflow (etapa 2; ADR 0008)

| Teste com a Connection `aws_default` | Esperado | Resultado |
|---|---|---|
| Identidade | Role do Airflow | ✅ `assumed-role/rideshare-airflow/airflow_aws_default` |
| Listar a Bronze | Permitido | ✅ |
| Listar o bucket do estado do Terraform | Negado | ✅ `AccessDenied` |
| Athena, workgroup `rideshare` | Permitido | ✅ |
| Athena, workgroup `primary` (sem limite de custo) | Negado | ✅ |

## 4. Schema da TLC no recorte (etapa 4; R4)

Rodapé dos 32 arquivos de 2024-01 a 2026-08 (DuckDB, só metadados), agrupados pelo hash da lista `nome:tipo`:

| De | Até | Meses | Colunas |
|---|---|---|---|
| 2024-01 | 2024-12 | 12 | 24 |
| 2025-01 | 2026-08 | 20 | 25 (+ `cbd_congestion_fee`) |

Fora do recorte, a TLC já mudou tipo (`PULocationID` INT64 em 2019-02 e 2022-01, INT32 depois) e publicou coluna de tipo "nulo" (`airport_fee` e `wav_match_flag` em 2019-02). O contrato (`airflow/include/contratos/tlc_hvfhv.yml`) usa o vocabulário do Athena porque o pyarrow lê texto como `large_string`.

Arquivo real de 2025-01 contra o contrato: `aceito`, sem alertas; 20.405.666 linhas (rodapé); `schema_hash` `6fa14a7e…`.

## 5. Fuso horário (R5; ADR 0009)

| Data | Hora local | Corridas | Mesmo horário, dia anterior |
|---|---|---|---|
| 09/03/2025 (relógio pula de 2h para 3h) | 2h | 85 | 20.601 |
| 02/11/2025 (a 1h acontece duas vezes) | 1h | 75.292 | 48.411 |

Conclusão: horário local de Nova York, sem fuso (`isAdjustedToUTC = false` em todos os meses lidos).

## 6. Cenários da ingestão no ambiente de teste (etapa 8)

"TLC de mentira" (nginx com ETag por data + tamanho e 403 para arquivo inexistente) servindo amostras de 1.000 corridas reais. `airflow dags test tlc_ingest` com `ambiente=teste` e `primeiro_mes=2026-06`:

| # | Fonte | DAG | Run |
|---|---|---|---|
| 1 | Publica 06, 07, 08 | Baixa os três (`aceito`); 09 `aguardar` | sucesso |
| 2 | Nada muda | Ignora tudo, sem download | sucesso |
| 3 | Republica 07 (conteúdo novo) | Nova versão `aceito`; a vigente de 07 muda | sucesso |
| 4 | `touch` em 06 (ETag novo, mesmo conteúdo) | `mesmo_conteudo`, nenhum arquivo novo | sucesso |
| 5 | Dia seguinte | 06 ignorado **sem download** (sem re-download eterno) | sucesso |
| 6 | 08 fora do contrato (`trip_miles` texto) | Quarentena (`rejeitado`), task vermelha sem retry | falho, de propósito |
| 7 | Dia seguinte, o mesmo arquivo | `erro` sem download | falho, de propósito |

Manifesto de teste depois dos 7 runs: 6 linhas, sem duplicatas. Vigentes: 06 = versão original (a conferência não muda a vigente); 07 = republicação; 08 = versão original aceita (a quarentena não muda a vigente). Bronze de teste de 07 vigente: 1.000 corridas.

Verificado no cenário 6: o `publicar` (`trigger_rule="all_done"`) recebe os resultados mesmo com um mês falho, e a task `tudo_certo` faz o run terminar como **falho**.

## 7. Clima (etapa 9; W1 a W4)

- Resposta real da API: sem ETag e sem Last-Modified; `generationtime_ms` muda a cada pedido; ponto da grade (40.808434, −74.0199) a ~4 km do pedido.
- Dois pedidos seguidos do mesmo mês: **mesmo SHA-256** do JSON canônico (`d0f59df7…`, 31.252 bytes).
- Teste (`ambiente=teste`): 1º run grava 3 meses `aceito`; 2º run, os 3 "sem mudança".
- Athena (`teste_bronze.open_meteo`, 2026-08): 768 horas (agosto + 01/09, em UTC), unidade °C, ponto da grade esperado; `UNNEST` das listas funciona.

## 8. Backfill em produção (etapa 11)

Ensaio só de leitura antes do backfill: próximo esperado `2025-02`; **31 meses a baixar** (14,3 GiB), `2025-01` ignorado (linha retroativa da Fase 1), `2026-09` aguardando.

| Item | Resultado |
|---|---|
| Run que fez o backfill | `scheduled__2026-10-18T09:00:00` (criado ao despausar: o "não verificado" do plano aconteceu) |
| Duração | ~13 min (20:09 → 20:22 UTC), 3 meses em paralelo |
| `ingerir_mes` | 31 de 31 com sucesso, **nenhum retry** |
| Run manual que ficou na fila | 32 meses `ignorar`, 2026-09 `aguardar`: idempotência em produção |
| `weather_ingest` | Disparada sozinha pelo Asset (`asset_triggered__…`); 32 meses `aceito` |

**Manifesto de produção** depois do backfill:

| Fonte | Status | Linhas | Vigentes |
|---|---|---|---|
| `tlc_hvfhv` | `aceito` | 32 | 32 (2024-01 a 2026-08) |
| `open_meteo` | `aceito` | 32 | 32 (2024-01 a 2026-08) |

**Reconciliação manifesto × Bronze:** para os 32 meses, o `row_count` registrado na ingestão é igual à contagem da Bronze na versão vigente (32/32; 0 bytes lidos, contagem pelo rodapé).

| Medida | Valor |
|---|---|
| Corridas na Bronze vigente | **651.246.843** (2024: 239.470.448; 2025: 243.589.684; 2026 até agosto: 168.186.711) |
| Menor / maior mês | 2024-08: 19.128.392 / 2026-05: 22.125.744 |
| Horas de clima | 24.144 (= (974 dias + 32 dias "do mês seguinte") × 24) |
| `bronze/tlc_hvfhv/` | 32 objetos, 14,73 GiB (~US$ 0,34/mês) |
| `bronze/open_meteo/` | 32 objetos, < 1 MB |
| `controle/` | **285 objetos** para 64 linhas (cada `INSERT` cria um snapshot Iceberg) |

## 9. Pendências (passam para a Fase 3)

- **Manutenção do manifesto:** 285 arquivos pequenos em `controle/` (small files). Rotina de `OPTIMIZE` + `VACUUM` (retenção de 90 dias já configurada).
- **DAG `dbt_build`** disparada pelos Assets, perguntando ao manifesto quais meses mudaram (vários eventos de Asset podem virar um run só); montar a Silver mês a mês (32 meses) e recalibrar o limite de 1 GiB do workgroup.
- **Silver do clima:** `UNNEST` das listas, conversão de UTC para `America/New_York`, recorte do mês local e agregação na hora repetida de novembro.
- **Horas de troca do horário de verão:** marcar; investigar as 85 corridas da hora inexistente de 09/03/2025.
- **Contrato:** conferir também a marcação `isAdjustedToUTC` (hoje só o tipo).
- **Tabela de zonas da TLC** (`tlc_zones`) e seeds.
- **Alerta de "aguardando" longo** (ex.: mês esperado há mais de 3 meses sem publicação).
- ⚠️ Não verificado: se um portfólio público sem anúncios se enquadra no uso "não comercial" do Open-Meteo; se o Open-Meteo revisa dados históricos (a ingestão detectaria pelo SHA-256).
