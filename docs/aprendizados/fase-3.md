# Fase 3: Silver e Gold — registro de aprendizado

- **Período:** 19/10/2026 a 28/10/2026 (gate de domínio pendente)
- **Objetivo:** modelos completos, testados e com o gate de qualidade.
- **Resultado:** "pronto quando" cumprido:
  - a reconciliação Silver × Gold bate nos 32 meses de produção (651.163.831 = 651.163.831);
  - o gate barrou um mês adulterado pela CLI (−49,5%) e pelo Airflow (+101,9%).

  Produção construída pelo Airflow em ~3h20 por US$ 0,59 ([relatório de validação](../validacao/fase-3.md)).

---

## 1. O que foi construído

| Peça | Como | Onde |
|---|---|---|
| Seeds | Zonas da TLC, 38 zonas do CBD (MTA), operadoras, feriados 2024–2026; Iceberg no lake | `dbt/seeds/` |
| Stagings | TLC (versão vigente pelo manifesto), zonas, clima (`UNNEST`, UTC → horário de NY, hora repetida agregada) | `dbt/models/staging/` |
| `int_trips_enriched` | Chave surrogate, colunas derivadas e ✍️ validade em dois níveis | `dbt/models/intermediate/` |
| Testes da Silver | 10 testes por mês com `where`, freshness no manifesto, ✍️ gate de volume (teste genérico) | `_intermediate.yml`, `tests/generic/volume_mensal.sql` |
| Gold | `dim_zona`, `dim_operadora`, `dim_tempo_hora`, `fct_demanda_zona_hora`, `fct_espera_histograma`, `fct_od_diario`; reconciliações; métricas no `meta` | `dbt/models/marts/` |
| `dbt docs` | Linhagem do manifesto até a Gold | `docs/validacao/img/fase-3-linhagem.png` |
| Ambiente do dbt no Airflow | venv do dbt na imagem; projeto `dbt/` montado | `airflow/Dockerfile`, `docker-compose.override.yml` |
| `dbt_mes_dev` / `dbt_mes_prod` | Cosmos: um mês, uma task por model, testes sem retry, registro no fim | `airflow/dags/dbt_mes.py` |
| Registro de construção | Iceberg só de acréscimo + view `_vigente` | `scripts/fase-3/controle_meses_construidos.sql`, `airflow/include/dbt_registro.py` |
| ✍️ Regra de pendência | Tabela de 8 cenários do Ronald → `decidir_mes` e `planejar_construcao` | `airflow/include/dbt_construcao.py` |
| `dbt_build_dev` / `dbt_build_prod` | Assets → planejar → um mês por vez → publicar `gold_demanda` | `airflow/dags/dbt_build.py` |
| `manutencao_iceberg` | `VACUUM` semanal em tudo; `OPTIMIZE` no `controle`; tabelas descobertas no Glue | `airflow/dags/manutencao_iceberg.py`, `airflow/include/manutencao.py` |
| IAM | Versões de tabela no Glue e metadados do catálogo no Athena; limite do workgroup de 1 para 3 GiB | `infra/terraform/` |
| Testes automatizados | 102 (36 novos na fase) | `airflow/tests/` |
| Documentação | ADRs 0004, 0005, 0006, 0007 e 0016; spec; glossário | `docs/` |

**Critérios de pronto:**

| Critério | Evidência |
|---|---|
| Todos os modelos da seção 6 | Silver e Gold completas; `ml_*` ficam para a Fase 5 |
| Testes da seção 8 | Fonte, Silver, gate e Gold, calibrados com 3 meses e conferidos em 32 |
| DAG `dbt_build` com o gate | `dbt_build` + `dbt_mes` (ADR 0016) |
| `dbt docs` | Linhagem com o manifesto |
| ADRs de chave surrogate, partição, histograma e CBD | 0004, 0005, 0006, 0007 (e 0016) |
| Reconciliação Silver × Gold | 32/32 meses em produção |
| Gate barra mês adulterado | Etapa 9, P1 e P2 |

**Custo da fase:**
- Build completo de produção: US$ 0,59 no Athena.
- Armazenamento: ~US$ 2,30/mês (~102 GiB, dev incluído).

---

## 2. O que aprendi, por tecnologia

- **Camadas e Kimball:** staging limpa e tipa; intermediate aplica regra de negócio; marts entregam o grão do consumo. O **grão** é a primeira decisão de uma fato ("uma linha por quê?"). A regra `is_valid` fica na `int`, e a Gold só **usa a marca** (marcar × usar a marca).
- **Chave surrogate:** sem chave natural, um hash do conteúdo. Poucas colunas colidem (27 casos); 25 colunas + ordem da cópia dão uma chave única e determinística. Hash não comprime: só se grava o que é usado.
- **Incremental e idempotência por partição:** delete + append do `source_month` (ADR 0014). A premissa "todo embarque é do mês do arquivo" virou teste, não suposição (ADR 0005). `--full-refresh` com pasta compartilhada apaga a tabela: `schema_table_unique`.
- **Testes, severidade e gate:** teste genérico × singular; `warn` alarma, `error` protege. O gate de volume é **proteção** (a Gold não é atualizada) e **alarme** (task vermelha). O mês barrado fica pendente no registro e volta sozinho no próximo run.
- **Freshness:** mede o atraso da fonte pelo manifesto. Só alarma: não impede construir os meses que já chegaram.
- **Jinja, macros e `meta`:** o Jinja gera SQL na compilação (o `{% if %}` some do SQL compilado). O `meta` guarda as definições das métricas para o DAX e para o agente. "SQL primeiro, Jinja quando doer".
- **Percentil não aditivo e histograma:** a média dos P90 erra pela **forma** das distribuições, não pelo tamanho. O histograma guarda contagens (aditivas); o P90 sai acumulando as faixas e interpolando. O tamanho vem das células pequenas, não do número de faixas.
- **Cosmos:** lê o projeto dbt e cria uma task por model, com os testes logo depois. Credencial pela Connection do Airflow (profile mapping). O dbt roda num venv próprio dentro da imagem.
- **Orquestração por mês:** `TriggerDagRunOperator` com `wait_for_completion`, uma task mapeada por mês, uma de cada vez, na ordem. `trigger_rule` decide quem roda depois de uma falha (`all_done`, `none_failed`).
- **Checkpoint do consumidor:** o manifesto diz o que a Bronze tem; o **registro** diz o que a Gold já usou. Comparar com a Silver falharia, porque a Silver pode estar atualizada com a Gold barrada. A regra decide **se** constrói; a macro decide **qual** versão.
- **Manutenção do Iceberg:** cada delete + append deixa arquivos antigos para o time travel; o `VACUUM` os apaga depois da retenção. O `OPTIMIZE` junta os arquivos minúsculos do manifesto. A retenção é por tabela: 90 dias no controle, 5 dias no que se reconstrói da Bronze.

---

## 3. Erros cometidos (e o que ensinaram)

**Do Ronald:**
- **Aula 1:** pôs a regra `is_valid` na `fct_` em vez da `int_`. Virou o conceito "marcar × usar a marca".
- **Aula 3:** confundiu o motivo do `warn_if`/`error_if` com a regra do gate de volume.
- **Aula 4:** não soube o que o `{% if %}` vira no SQL compilado.
- **Aula 5:** errou por que a média **ponderada** dos P90 erra (é a forma, não o tamanho). Os passos do P90 no DAX ficaram incompletos: faltaram acumular e interpolar.
- **✍️ `is_valid`:**
  - `trip_time` sem comparação;
  - faltou a espera negativa;
  - uma vírgula faltando virou um alias silencioso;
  - um nome renomeado num lugar só.

  Corrigiu tudo depois da revisão.
- **✍️ Gate de volume:** travou em subconsultas, NULL × 0 e tipos.
- **Regra de pendência, 1ª rodada:** errou os motivos das linhas 4 e 5, a decisão da linha 6 e as linhas 7 e 8. Acertou na 2ª rodada, com pistas.
- **Checagens:**
  - achou que o registro percebe mudança de código (nenhum dos dois percebe; resolve o `forcar_meses`);
  - achou que trocar a ordem dos meses construiria uma versão não vigente (a ordem importa por causa do gate; a versão vem da macro). Corrigido na 2ª rodada.
- **Acertos de destaque:**
  - Aulas 2 e 6 sem erro;
  - as duas previsões da etapa 9 (gate em erro; última task verde `int_trips_enriched.run`);
  - por que o 2026-05 forçado foi registrado como `manifesto`;
  - a frase "a regra decide SE, a macro decide QUAL";
  - o efeito de usar a taxa como marca do CBD.

**Do Claude Code (registrados por honestidade):**
- **Incidente do `--full-refresh`:** rodou um full-refresh de incremental Iceberg com pasta compartilhada e **apagou a `int_trips_enriched` de dev**. A correção foi `schema_table_unique` em todos os models e seeds.
- **F9:** o plano manteve o limite de 1 GiB sem medir a cópia da temporária para a final. Foi preciso revisar para 3 GiB no meio da fase.
- **Primeiro desenho da `dbt_build`:** o registro gravado pela própria `dbt_build` poderia anotar versões erradas, e um disparo manual da `dbt_mes` não registraria nada. O registro foi movido para a `dbt_mes`, com as versões lidas da Silver.
- **Primeiro desenho com um parâmetro `ambiente`:** o Cosmos monta as tasks na leitura do arquivo, antes de existir parâmetro. Virou uma DAG por ambiente.
- **Primeiro desenho de dev:** construiria os 32 meses em dev. Foi corrigido antes de rodar (dev como amostra, opção A).
- **Filtro da manutenção:** o filtro `__` excluía as stagings (`stg_tlc__hvfhv_trips`). Foi trocado pelos sufixos reais das temporárias, com teste.
- **Previsão errada:** previu motivo `forcado` para o 2026-05 em dev; era `manifesto` (linha 1). O Ronald explicou por quê.
- **Seleção do dbt na etapa 9:** o `--exclude` tirava os testes junto com o model.
- **Ferramentas:**
  - o script de monitoramento quebrou com os avisos da CLI do Airflow;
  - o `astro dev pytest` foi usado sem o projeto dbt montado;
  - o script auxiliar de consultas ficou de novo na pasta temporária e foi apagado entre sessões. Agora usamos o `scripts/athena_roda.py`, que é versionado.

**Nota de transparência sobre as peças ✍️:**

| Peça | Quem desenhou | Quem escreveu o código |
|---|---|---|
| `is_valid` (SQL) | Ronald (dois níveis: corrida × métrica) | Ronald, corrigido por ele depois da revisão |
| Gate de volume (SQL) | Ronald (média diária × média dos 3 meses anteriores) | Ronald na 1ª versão. A correção da 2ª rodada (`group by` + `avg`) foi **entregue pelo Claude Code** e colada por ele. A transformação em teste genérico com aviso e erro foi do Claude Code |
| Regra de pendência (Python) | Ronald (tabela de 8 cenários e 3 respostas: pedido impossível, precedência, ambiente) | Claude Code, a pedido dele (código e 13 testes), com explicação bloco a bloco e checagem de entendimento |

---

## 4. Decisões tomadas

| Decisão | Registro |
|---|---|
| F1: Gold incremental por `source_month` (delete + append) + teste "mês do embarque = `source_month`" | [ADR 0005](../adr/0005-particao-por-source-month.md), ADR 0014 |
| F2 e F3: chave = hash das 25 colunas + ordem; duplicata exata marcada | [ADR 0004](../adr/0004-chave-surrogate-e-duplicatas.md) |
| F4: histograma de 18 faixas, grão por hora do dia e tipo de dia | [ADR 0006](../adr/0006-percentis-via-histograma.md) |
| F5: `dbt_build` disparada pelos Assets, `dbt_mes` por mês | [ADR 0016](../adr/0016-registro-de-construcao-do-dbt.md) (revisou o F5) |
| F6 e F7: projeto `dbt/` montado; venv do dbt na imagem (dbt-core 1.12.5, dbt-athena 1.11.1) | `airflow/Dockerfile`, `airflow/docker-compose.override.yml` |
| F8: credencial do dbt pela Connection `aws_default` (profile mapping) | ADR 0008 |
| F9: limite do workgroup, revisado de 1 para 3 GiB | spec, seção 11.4 |
| F10: seeds (zonas, CBD pela MTA, operadoras, feriados) | [ADR 0007](../adr/0007-cbd-por-lista-de-zonas.md) |
| F11: Silver do clima no horário de NY; horas de troca do horário de verão marcadas | ADR 0009 |
| F12: freshness no manifesto (45/75 dias) + `manutencao_iceberg` | spec, seções 7 e 8 |
| B1 a B6: registro de construção, espera do clima, um mês por vez, freshness só alarma, `forcar_meses`, prod nos 32 meses | ADR 0016 |
| Dev como amostra (opção A) | ADR 0016, spec 11.2 |
| Manutenção: `VACUUM` em tudo, `OPTIMIZE` só no controle, tabelas descobertas no Glue, domingo 6h UTC | spec, seção 7 |
| Testes do dbt sem retry (28/10/2026) | `dbt_mes.py`; ADR 0016 (o mês pendente substitui o retry) |

---

## 5. Gate de domínio

*A preencher no item 11 da etapa 11.*

---

## 6. Pendências e melhorias anotadas

- **Fase 4:**
  - tarifa ≤ 0 por operadora: a hipótese da etapa 4, com 3 meses acima do aviso (2025-03, 2025-08, 2026-01);
  - tamanho da `fct_od_diario` no Power BI (55,3 milhões de linhas).
- **Acompanhar:** corridas inválidas no maior mês (4.854) perto do aviso de 5 mil.
- **Herdadas da Fase 2:** contrato conferindo `isAdjustedToUTC`; alerta de "aguardando" longo.
- **DAGs ligadas:**
  - `dbt_build_prod` (pelos Assets), `dbt_mes_prod` e `manutencao_iceberg` (domingo 6h UTC);
  - as de dev só rodam à mão.

  Tudo roda enquanto o Docker estiver ligado no Mac.
- ⚠️ Não verificado:
  - quanto o `VACUUM` de 01/11 vai liberar no `dev_silver`;
  - os preços de tabela do S3 e do Athena.
