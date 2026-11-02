# Relatório de validação — Fase 4 (Power BI)

Evidências dos passos da Fase 4 (plano D1 a D6 e decisões P1 a P4). Em construção: cada passo entra aqui ao ser concluído. Datas: a partir de 31/10/2026.

---

## 1. Tarifa ≤ 0 por operadora (passo 1)

Pergunta herdada da Fase 3: a tarifa base ≤ 0 (`is_valid_economic_metrics = false`) é ruído ou um fenômeno de negócio? Medido na `silver.int_trips_enriched` de produção, só corridas válidas (31/10/2026).

**Por mês e operadora** (HV0003 = Uber, HV0005 = Lyft; meses selecionados):

| Mês | Uber zero | Uber negativa | Lyft zero | % do total |
|---|---|---|---|---|
| 2024-10 | 15.424 | 1.720 | 0 | 0,086% |
| 2024-12 | 444 | 1.971 | 31.424 | 0,161% |
| 2025-03 | 1.129 | 326 | 62.698 | 0,313% |
| 2025-08 | 1.803 | 707 | **183.494** | **0,965%** |
| 2026-01 | 29.672 | 29.845 | 40.814 | 0,479% |
| 2026-05 | 4.158 | 7.609 | 4 | 0,053% |
| 2026-08 | 292 | 1.038 | 3 | 0,007% |

Lyft negativa: entre 10 e 163 por mês em todo o período.

**Perfil das corridas** (meses de pico):

| Mês | Operadora | Tipo | Corridas | Repasse médio ao motorista | % com repasse > 0 | Milhas médias | Dias com casos |
|---|---|---|---|---|---|---|---|
| 2025-08 | Lyft | zero | 183.494 | US$ 19,94 | 100,0% | 5,15 | 10 |
| 2026-01 | Lyft | zero | 40.814 | US$ 19,96 | 100,0% | 5,18 | 22 |
| 2026-01 | Uber | zero | 29.672 | US$ 0,21 | 11,0% | 3,25 | 31 |
| 2026-01 | Uber | negativa | 29.845 | US$ 2,27 | 18,6% | 3,46 | 31 |
| 2024-10 | Uber | zero | 15.424 | US$ 0,37 | 13,3% | 4,93 | 27 |

Concentração da Lyft em ago/2025: 17/08 = 105.523, 18/08 = 57.544, 16/08 = 20.413 (183.480 de 183.494, 99,99% do mês em 3 dias).

**Leitura:**
- **Lyft:** a corrida aconteceu e o motorista recebeu o normal, mas a tarifa veio zerada, em dias específicos. Inferência (não confirmada pela TLC): falha de registro da tarifa.
- **Uber:** zeros e negativos com repasse quase nulo, espalhados pelo mês. Compatível com corridas canceladas cobradas, estornos ou promoções (hipótese, não verificada).
- **Decisão (aprovada pelo Ronald):** a regra fica como está. Nos dois casos a tarifa não mede a corrida. Sem ADR: a evidência não muda a decisão (spec 6.3, regra 2). A página de economia mostra o "% tarifa inválida".

## 2. Dimensões do período e OD mensal (passo 2)

Modelos novos (decisões D1 e D2): `dim_faixa_espera`, `dim_mes`, `dim_periodo_espera`, `periodo_id` na `dim_tempo_hora` e na `fct_espera_histograma`, e `fct_od_mensal`, com o teste `reconciliacao_od_mensal`. A `dbt_mes` passou de 34 para 51 tasks.

**Reconstrução de produção** (`dbt_build_prod`, `manual__2026-11-01T01:03:09`, 32 meses forçados): ✅ 32/32 verdes, em 3h44 (~7 min por mês), terminando às 04:47 UTC de 01/11/2026. O mês 2026-09 entrou pelo agendamento normal (motivo `manifesto`, 00:37 UTC), já com o código novo.

| Conferência (Athena, 01/11/2026) | Resultado |
|---|---|
| `fct_espera_histograma` com `periodo_id` | 14.404.307 linhas em 33 meses, **100%** com a chave |
| `fct_od_mensal` × `fct_od_diario` | 672.148.703 corridas nas duas; **0 meses divergentes** (corridas e tarifa, tolerância 0,01) |
| Linhas da `fct_od_mensal` | 3.659.444 (contra 55 milhões da diária) |
| Dimensões | `dim_mes` 36 · `dim_faixa_espera` 18 · `dim_periodo_espera` 2.376 · `dim_tempo_hora` 26.304 com `periodo_id` |
| Registro de construção | 32 meses `forcado` (2024-01 a 2026-08) + 2026-09 `manifesto` |
| Custo real no Athena | ~US$ 0,69 (3.760 consultas, 0,137 TB cobrados; estimativa era US$ 0,59) |

A exceção temporária `on_schema_change = 'append_new_columns'` do histograma (necessária para acrescentar a coluna `periodo_id` à tabela existente) foi removida depois da reconstrução: o model voltou ao padrão `fail`.

**Tamanho da Gold** (arquivos do snapshot atual, `"$files"`, 01/11/2026):

| Tabela | MB | Importada no Power BI |
|---|---|---|
| `fct_od_diario` | 818,9 | não (substituída pela mensal) |
| `fct_demanda_zona_hora` | 358,4 | sim |
| `fct_espera_histograma` | 79,0 | sim |
| `fct_od_mensal` | 60,1 | sim |
| 6 dimensões | 0,2 | sim |

## 3. Identidade de leitura do Power BI (passo 3)

Terraform (`iam_powerbi.tf` e `athena.tf`; plan do Claude Code, apply do Ronald em 01/11/2026): `Plan: 4 to add, 0 to change, 0 to destroy`.
- Workgroup `rideshare-bi`: limite de 1 GiB por consulta (a maior importação tem 358 MB), resultados em `bi/`, métricas no CloudWatch.
- Permission set `RideshareLeituraGold` (sessão de 8 h), com política inline de leitura da Gold, atribuído ao usuário `ronald` nesta conta.

**Matriz de testes** com o perfil `rideshare-bi` da AWS CLI (mesma sessão SSO do `rideshare-admin`, papel `AWSReservedSSO_RideshareLeituraGold_...`):

| # | Teste | Esperado | Obtido |
|---|---|---|---|
| 1 | `SELECT count(*) FROM gold.dim_mes` pelo `rideshare-bi` | OK | ✅ 36 linhas; resultado gravado em `bi/` |
| 2 | Fato Iceberg da Gold (`fct_od_mensal`, 2026-09) | OK | ✅ 111.248 linhas |
| 3 | Ler a Silver (`silver.stg_tlc__zones`) | negado | ✅ `Insufficient permissions` |
| 4 | Ler a Bronze (`bronze.open_meteo`) | negado | ✅ `Insufficient permissions` |
| 5 | Consultar pelo workgroup `rideshare` | negado | ✅ `AccessDeniedException` |
| 6 | Consultar pelo workgroup `primary` | negado | ✅ `AccessDeniedException` |
| 7 | `CREATE TABLE gold.teste_permissao_bi AS SELECT 1` | negado | ✅ `Insufficient permissions` |
| 8 | `glue:DeleteTable` na Gold (nome inexistente) | negado | ✅ `AccessDeniedException` |
| 9 | `PutObject` em `gold/` no lake | negado | ✅ `AccessDenied` |
| 10 | Listar `silver/` no lake | negado | ✅ `AccessDenied` |
| 11 | `GetObject` em `silver/` | negado | ✅ `AccessDenied` |
| 12 | `PutObject` fora de `bi/` no bucket de resultados | negado | ✅ `AccessDenied` |

**Listagem do catálogo** (estava "não verificado" no plano): `glue.get_databases` e `athena.list_databases` devolvem **só `['gold']`**. A listagem é filtrada pelas permissões, então o navegador do Power BI deve mostrar apenas a Gold (a confirmar no Desktop, passo 5).

Pendente para o passo 5 (Windows): trocar no DSN o Role name para `RideshareLeituraGold`, o workgroup para `rideshare-bi` e a saída para `.../bi/`. Se o Power BI pedir `ListDataCatalogs` ou `ListWorkGroups`, acrescentar à política com a evidência.

## 4. Conexão, importação e modelo (passo 5, Windows, 02/11/2026)

**DSN `rideshare-athena`** (conferido no registro do Windows antes e depois de cada mudança):

| Campo | Antes (Fase 1) | Agora |
|---|---|---|
| Database | `dev_gold` | `gold` |
| Workgroup | `rideshare` | `rideshare-bi` |
| S3 Output Location | `.../resultados/` | `.../bi/` |
| Role name | `AdministratorAccess` | `RideshareLeituraGold` → **`AdministratorAccess` provisório** (ver abaixo) |
| `UseSingleCatalogAndSchema` | `0` | `1` |

- **Administrador ODBC:** o botão Configurar fica cinza na janela de **32 bits**; o driver da Athena só existe em 64 bits (`C:\Windows\System32\odbcad32.exe`).
- **`athena:ListDataCatalogs` negado** ao papel de leitura (deixado de fora de propósito no passo 3):
  1. Driver **2.4.0.0** com `UseSingleCatalogAndSchema=1`: mesmo erro. As release notes da **2.5.0.0** (28/10/2026) dizem que só nela o modo de catálogo único deixou de chamar o Athena e o Glue para listar catálogos (✅ documentação oficial).
  2. Driver atualizado para **2.5.0.0** (instalador assinado pela Amazon; DSN preservado): o navegador passou a mostrar o catálogo e o banco `gold`, mas **listar as tabelas** do `gold` ainda chama `ListDataCatalogs` (motivo não documentado; não verificado).
  3. Decisão (B2): Role name **provisório** `AdministratorAccess`, mantendo banco, workgroup e saída do BI. O código M guarda só o nome do DSN (`AmazonAthena.Databases("rideshare-athena", null, [])`), então trocar o papel não muda o projeto.
  - **Pendente (Mac):** acrescentar `athena:ListDataCatalogs` ao `RideshareLeituraGold` (formato do `Resource` não verificado na referência do IAM), voltar o DSN para o papel de leitura e testar uma atualização completa.

**Importação (Import, 9 tabelas):** contagens idênticas à foto de 01/11/2026.

| Tabela | Linhas | Soma de `qtd_corridas` |
|---|---|---|
| `fct_demanda_zona_hora` | 11.905.597 | 672.148.703 |
| `fct_espera_histograma` | 14.404.307 | 664.669.321 |
| `fct_od_mensal` | 3.659.444 | 672.148.703 |
| `dim_tempo_hora` / `dim_periodo_espera` / `dim_mes` | 26.304 / 2.376 / 36 | — |
| `dim_faixa_espera` / `dim_zona` / `dim_operadora` | 18 / 265 / 4 | — |

**Relacionamentos:** o Desktop detectou 5 sozinho na carga. Um deles (`dim_tempo_hora[ano_mes] → dim_mes`) criava um segundo caminho de filtro e o Desktop **desativou em silêncio** a ligação `dim_tempo_hora → dim_periodo_espera`: filtros de hora do dia e tipo de dia não chegariam à demanda. Atalho apagado, cadeia ativada, detecção automática desligada no arquivo.
- Estado final: **13 relacionamentos**, todos 1 → N em direção única, incluindo a `dim_zona_destino` (Referência da `dim_zona` no Power Query; 265 zonas, 38 no CBD) ligada só à `fct_od_mensal`.
- Teste (jan/2025, um filtro na `dim_mes`): demanda 20.403.058 = OD 20.403.058; histograma 20.203.505 (só espera válida). Nenhuma linha órfã nas 6 chaves testadas.

**PBIP (ADR 0011):** TMDL e PBIR já são o padrão no Desktop. `cache.abf` de 523 MB e `localSettings.json` fora do Git; arquivos de texto em CRLF; `.gitattributes` restrito a `powerbi/`.

## 5. Medidas DAX (passo 6, 02/11/2026)

Escritas pelo Ronald; revisadas pelo Claude com pistas antes da correção. Formato fixo, pastas e descrições (descrições escritas pelo Claude, a pedido do Ronald).

| Medida | Valor (33 meses) | Conferência |
|---|---|---|
| Corridas | 672.148.703 | = guia |
| % tarifa invalida | 0,097% | 2024-10 0,086%, 2025-08 0,965%, 2026-01 0,479%: = seção 1 |
| Take rate | 23,00% | razão das somas calculada à parte: 23,00% |
| Receita por milha / por minuto | US$ 5,37 / US$ 1,35 | — |
| Repasse por hora de corrida | US$ 62,33 | — |
| Share da operadora | soma 100%; Lyft 2025-08 29,65% | conta direta: 29,65% |
| Corridas com destino no CBD | 147.874.858 (22,00%) | pela `fct_od_mensal`: 147.874.858 |
| Corridas entrando no CBD | 52.448.518 | `FILTER` linha a linha: 52.448.518 |
| Espera P50 / P90 (min) | 4,14 / 8,84 | P90 jan/2025 8,06 (= Fase 3) |

Lições registradas na revisão:
- `DIVIDE(..., 0)` afirma "0%" quando o denominador some; sem o terceiro argumento, devolve vazio. Nos dados de hoje não havia impacto (as somas vêm vazias, não 0).
- `CALCULATE` substitui o filtro do usuário na mesma coluna: com segmentação "origem no CBD", Corridas entrando no CBD mostrava 52.448.518 em vez de vazio. Corrigido com `KEEPFILTERS`.
- P50/P90: a escolha da faixa-alvo (`ADDCOLUMNS(ALL(dim_faixa_espera), ...)` + `MINX(FILTER(...))`) foi correção do Claude após duas pistas; total do recorte, acumulado e interpolação são do Ronald. Faixa 30+ devolve 30 (piso).

## 6. Reconciliação do P90 (passo 7, parcial)

| Recorte | DAX | Histograma em SQL (Fase 3) | Corrida a corrida (Fase 3) |
|---|---|---|---|
| Cidade, jan/2025 | 8,06 | 8,06 | 8,05 |
| Manhattan, 18h, dia útil, mai/2026 (319.506 corridas) | 9,30 | 9,30 | 9,25 |

Pendente: 7 recortes de mai/2026, inclusive células pequenas e faixas largas (15–20, 20–30 min), contra `approx_percentile` na Silver. Consulta pronta no guia `docs/guias/fase-4-continuar-no-windows.md` (seção 9).
