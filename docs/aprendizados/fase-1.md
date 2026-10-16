# Fase 1: Fatia vertical — registro de aprendizado

- **Período:** 12/10/2026 a 15/10/2026
- **Objetivo:** validar os três maiores riscos (custo por mês, incremental do dbt-athena com Iceberg, Power BI ↔ Athena) com 1 mês de dados, ponta a ponta.
- **Resultado:** os três riscos respondidos com evidência ([relatório de validação](../validacao/fase-1.md)); gate de domínio aprovado (com três reforços registrados).

---

## 1. O que foi construído

| Peça | Como | Onde |
|---|---|---|
| Arquivo 2025-01 na Bronze (468 MB, 20.405.666 linhas) | Download manual + upload para o S3 | `bronze/tlc_hvfhv/year=2025/month=01/ingest_ts=.../` |
| Tabela externa `bronze.tlc_hvfhv`, particionada por `year`/`month` | DDL no Athena + registro manual da partição | `scripts/fase-1/` |
| Projeto dbt (dbt-core 1.12.5 + dbt-athena 1.11.1), ambiente isolado com `uv` | `dbt_project.yml`, `profiles.yml` sem segredos, targets `dev`/`prod`, macro `generate_schema_name` | `dbt/` |
| `stg_tlc__hvfhv_trips` ✍️: Silver incremental em Iceberg | Model escrito pelo Ronald; `append` + `pre_hook` com delete do mês (ADR 0014) | `dev_silver` |
| `fct_demanda_zona_hora` ✍️: Gold mínima (hora × zona × operadora) | Model escrito pelo Ronald; materialização `table` em Iceberg | `dev_gold` |
| Primeiro visual no Power BI | Driver ODBC 2.4 + DSN com SSO + conector Athena (Import); PBIP de teste fora do repo | `docs/validacao/img/fase-1-powerbi-r3.png` |
| Relatório de validação | Medições e conferências de cada risco | `docs/validacao/fase-1.md` |

**Critérios de pronto:**

| Critério | Evidência |
|---|---|
| R1 (tamanho e custo) | ~470 MB e ~20 milhões de linhas por mês; a consulta mais cara (arquivo inteiro) custou ~US$ 0,0023 |
| R2 (incremental com Iceberg) | `insert_overwrite` bloqueado pelo adaptador → `append` + delete do mês; segunda execução manteve 20.405.666 linhas |
| R3 (Power BI ↔ Athena) | Desktop reproduz a Gold exatamente (364.630 linhas; 20.405.666 corridas; divisão por operadora). Service exige gateway: plano B |
| Hipóteses ⚠️ da Seção 3 | Atualizadas na spec (schema, operadoras, CBD, `on_scene_datetime`) |

---

## 2. O que aprendi, por tecnologia

- **Parquet:** formato colunar e comprimido; a consulta lê só as colunas que usa. Na Athena, que cobra por dado lido, isso é custo direto: `avg(trip_miles)` leu 36 MB de um arquivo de 468 MB. O rodapé guarda min/max por row group, e o motor só pula um bloco quando o intervalo inteiro fica fora do filtro.
- **Particionamento Hive:** pastas `coluna=valor`; o motor poda as pastas que não interessam (partition pruning), mas só com filtro na coluna de partição. Uma pasta nova é invisível até ser registrada no Glue: o resultado é um zero silencioso, sem erro.
- **Tabela externa × gerenciada:** a diferença é quem é dono dos arquivos. Externa (Bronze) = shortcut do Fabric: `DROP TABLE` remove só a definição. Gerenciada (Iceberg, Silver e Gold) = tabela Delta em Tables: `DROP TABLE` **apaga os dados**.
- **Iceberg:** formato de tabela sobre Parquet; o essencial é o commit atômico, que permite apagar um mês e regravá-lo sem leitores verem a tabela pela metade. Snapshot é a versão da tabela inteira num commit. Time travel só lê o passado; rollback o torna vigente. Evolução de schema não reescreve arquivos antigos (`cbd_congestion_fee` aparece como `null` antes de 2025).
- **dbt:** o "T" do ELT; monta o SQL e manda a Athena executar (não processa nem agenda). `source()` na fronteira, `ref()` cria o DAG e troca o banco por ambiente. `dbt build` roda seeds, models e testes em ordem, e pula os dependentes de um teste que falhou.
- **dbt-athena:** o adaptador decide o que o dbt pode fazer naquele banco. Não oferece `insert_overwrite` para Iceberg (a limitação é do adaptador, não do formato). A materialização `table` em Iceberg cria a tabela nova e troca o nome, por isso exige pasta única por versão.
- **ODBC e conector do Athena:** o driver traduz o padrão ODBC para a API da Athena; o DSN guarda a conexão com nome (User × System). Import porque a Athena cobra por dado lido e o DirectQuery cobraria a cada clique. O Service exige gateway com System DSN e uma identidade sem pessoa no navegador: fora da v1.
- **Reconciliação:** cada camada conferida contra a anterior (arquivo → Bronze → Silver → Gold → Power BI). Se um número diverge, sabe-se em que passagem o problema nasceu.

---

## 3. Erros cometidos (e o que ensinaram)

**Do Ronald:**
- Aspas em volta de `{{ }}` no SQL (erro recorrente na construção dos models): o Jinja troca o texto ao pé da letra, então `source_month = {{ var(...) }}` vira `= 2025-01`, que a Athena lê como a conta 2025 − 1. Acertou no gate (Q5).
- No gate: dizer que `DROP TABLE` numa tabela Iceberg não afeta os arquivos no S3 (afeta: apaga os dados). Corrigido na mini-checagem.
- No gate: não lembrar a limitação do dbt-athena (`insert_overwrite`) nem como a validação dos números foi feita. Recuperados na mini-checagem.
- No passo 12: fechar a janela do DSN depois do Test sem clicar em OK (o Test não salva).

**Do Claude Code (registrados por honestidade):**
- O guia do passo 12 pedia o driver "2.1 ou mais nova" sem conferir a versão atual (2.4.0.0), mostrava os campos de login como se estivessem na mesma tela (ficam em "Authentication Options") e sugeria "corridas por dia" sem saber que o modelo não teria hierarquia de data.
- Disparou a aceitação da licença do MCP e a primeira operação em paralelo; a segunda chegou antes do aceite e falhou.
- Dimensionou a matriz do visual de conferência baixa demais: a linha do HV0005 saiu cortada no primeiro print. Pego na revisão do print e corrigido.

> Os erros da construção feita no Mac (dias 12 a 14) estão aqui só no que ficou registrado nos commits e no guia. Se o Ronald lembrar de outros, entram nesta seção.

---

## 4. Decisões tomadas

| Decisão | Registro |
|---|---|
| Iceberg como formato da Silver e da Gold | [ADR 0002](../adr/0002-iceberg-silver-gold.md) |
| Prefixo no S3 = nome do banco no Glue (`dev_silver/`, `dev_gold/`) | [ADR 0013](../adr/0013-layout-dev-no-s3.md) (revisado) |
| Silver incremental com `append` + delete do mês | [ADR 0014](../adr/0014-estrategia-incremental-silver.md) |
| Gold com `s3_data_naming: schema_table_unique` (troca de nome do Iceberg) | `dbt_project.yml`; relatório, seção 7 |
| Interface do agente: Streamlit; Power BI segue como dashboard de negócio | ADR 0010 (antecipado; escrever na Fase 6) |
| Power BI: conector Athena em Import; atualização no Service fora da v1 | spec, seção 10 e risco R3 |
| Gate de domínio em formato híbrido: explicação em conversa (um item por vez), autoavaliação em quiz de múltipla escolha, entrevista aberta | esta página, seção 5 |

---

## 5. Gate de domínio

Formato escolhido pelo Ronald: **híbrido**. A explicação continuou com as próprias palavras, mas em conversa, um item por vez; as 5 perguntas viraram múltipla escolha (testam reconhecimento, com distratores plausíveis); a entrevista seguiu aberta.

### Explicação com as próprias palavras (resumo da avaliação)

| Tecnologia | Avaliação |
|---|---|
| Parquet e armazenamento colunar | Correto no essencial. Faltou o "por que aqui" (custo por dado lido), tipos preservados e estatísticas do rodapé |
| Particionamento Hive | Firme (incluiu custo e small files). Faltou: poda só com filtro na partição; registro da partição no Glue |
| Tabela externa × gerenciada | 🔁 Revisar: disse que `DROP TABLE` na gerenciada não apaga os dados. Revisado com a ponte shortcut × tabela Delta do Fabric |
| Iceberg | Correto no essencial; snapshot impreciso ("grava cada mudança nas linhas") |
| dbt | Firme. Impreciso: o motivo da Gold ser `table`. Faltou: `dbt build` roda testes e pula dependentes |
| dbt-athena | Parte 1 correta (ponte com conector do Power Query); 🔁 revisar a parte 2 (não lembrou o `insert_overwrite`) |
| ODBC e conector | Correto no essencial. Faltou: a resposta sobre o Service (gateway + System DSN) |

### Autoavaliação (quiz)

| # | Tipo | Resultado |
|---|---|---|
| 1 | Conceitual: row group com min/max cruzando o filtro | ✅ |
| 2 | Conceitual: time travel × rollback | ✅ |
| 3 | Aplicada: `merge` numa republicação com linhas removidas | ✅ |
| 4 | Aplicada: partição gravada no S3 e não registrada no Glue | ✅ |
| 5 | Diagnóstico: `TYPE_MISMATCH` por falta de aspas em volta do `{{ }}` | ✅ |

**Pergunta de entrevista:** "Você conectou o Power BI a um data lake na AWS. Como garantiu que os números batem com a origem, e que o custo não explode?" O custo veio certo, mas só com um controle (Import). Faltaram a Gold pré-agregada (7,7 MB × 468 MB), Parquet particionado e o limite do workgroup. A validação dos números ficou sem resposta.

**Revisão (mini-checagem):** A (`DROP TABLE` externa × Iceberg) ✅; B (por que não `insert_overwrite`) ✅, com o ajuste de que a limitação é do adaptador, não do Iceberg; C (como os números foram provados) ✅, faltando só o elo Gold → Power BI.

**Resultado:** ✅ Passou.

**Reforços para as próximas fases:**
1. Responder sempre o "por que aqui", e não só o "o que é".
2. Validação como narrativa: a cadeia de reconciliação vira testes do dbt na Fase 3, escritos pelo Ronald.
3. Localizar a limitação: ferramenta (dbt-athena) × formato (Iceberg) × motor (Athena).

---

## 6. Pendências e melhorias anotadas

- **Fase 2:** recalibrar o limite de 1 GiB do workgroup antes do backfill; decidir a credencial do Airflow; partition projection (ou registro automático) na Bronze; manifesto de ingestão × Bronze sem `DeleteObject` (ADR 0013); escrever o ADR 0008 (Airflow local); fuso horário dos timestamps (R5).
- **Fase 3:** `VACUUM`/`OPTIMIZE` na Silver (os arquivos do primeiro snapshot dobraram a pasta `data/`); `is_valid` na Silver; custo de reconstruir a Gold inteira com 30 meses na Silver; validar a política do Airflow com o dbt-athena.
- **Fase 4:** coluna de data para agrupar por dia (hierarquia de datas desligada); formato numérico com separador de milhar; identidade somente leitura da Gold para o Power BI (spec 11.5); ADR 0011 (PBIP).
- Máquina Windows: o DSN de exemplo `Amazon Athena` (System, workgroup `primary`) continua instalado; não usar.
