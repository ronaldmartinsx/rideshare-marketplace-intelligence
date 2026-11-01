# Guia — Fase 4: continuar no Windows (Power BI)

> **Para quem:** o Ronald, na máquina Windows, e o Claude Code que o acompanhar lá.
> **Por que este guia existe:** a memória do Claude Code fica no Mac e não vai para o Windows. **Este arquivo é a fonte do estado da Fase 4.** Combinados de trabalho: `CLAUDE.md`. Evidências: `docs/validacao/fase-4.md`. Spec: `docs/PROJECT_SPEC.md` (Seção 10 e Fase 4 na Seção 12).
> **Atualizado em:** 01/11/2026, ao parar no Mac.

## 1. Onde paramos

**Branch:** `fase-4-power-bi` (no GitHub). Último commit da engenharia no Mac: o que adicionou este guia.

**Plano aprovado (31/10/2026), decisões D1 a D6:**

| # | Decisão | Situação |
|---|---|---|
| D1 | Ligar o histograma a dimensões do grão dele: `dim_periodo_espera` (mês × hora do dia × tipo de dia) e `dim_faixa_espera` | ✅ feito (passo 2) |
| D2 | `fct_od_mensal` (3,7 milhões de linhas) no lugar da `fct_od_diario` (55 milhões) no Power BI | ✅ feito (passo 2) |
| D3 | Página 5 vira **"Uber × Lyft por zona"**; o Forecast vai para a Fase 5 (ajuste na spec, sem ADR) | a fazer (passo 8; spec no passo 10) |
| D4 | HTML Content (edição **certificada**) só para cartões de insight e antes × depois | a fazer (passo 8) |
| D5 | Identidade somente leitura do Power BI em Terraform | ✅ feito (passo 3) |
| D6 | ADR 0011: PBIP (TMDL + PBIR) em `powerbi/` | a fazer (passo 5) |

**Decisões do passo 3 (P1 a P4):** permission set do Identity Center (sem chave); workgroup próprio `rideshare-bi` (1 GiB por consulta, resultados em `bi/`); só o banco `gold`; sessão de 8 h.

**Passos:**

| # | Passo | Máquina | Situação |
|---|---|---|---|
| 0 | Branch e glossário das aulas 1 a 4 | Mac | ✅ |
| 1 | Tarifa ≤ 0 por operadora (regra mantida) | Mac | ✅ (validação, seção 1) |
| 2 | Modelos dbt novos + reconstrução dos 32 meses em produção | Mac | ✅ (validação, seção 2) |
| 3 | Papel de leitura `RideshareLeituraGold` + workgroup `rideshare-bi` | Mac | ✅ (validação, seção 3; 12/12 testes) |
| 4 | TopoJSON das zonas para o mapa | Mac **ou** Windows | **a fazer** |
| 5 | PBIP: atualizar o DSN, importar a Gold, relacionamentos, formatos; ADR 0011 | **Windows** | **a fazer: comece por aqui** |
| 6 | Medidas DAX ✍️ (o Ronald escreve; o Claude revisa com pistas antes da correção) | Windows | a fazer |
| 7 | Reconciliação DAX × Athena (P90 do histograma × `approx_percentile`) | Windows | a fazer |
| 8 | As 5 páginas, com um insight escrito em cada | Windows | a fazer |
| 9 | Prints, vídeo curto, README | Windows | a fazer |
| 10 | ADRs 0011, 0017 (dimensões do período) e 0018 (identidade de leitura); spec (D3, novas tabelas na 6.4); glossário; `docs/aprendizados/fase-4.md`; gate; PR | ambas | a fazer |

**Ordem recomendada no Windows:** passo 5 → 6 → 7. O passo 4 só é necessário para a página 2 (mapa) e precisa de Node.js. Faça no Windows se tiver Node (`node -v`); senão, fica para o Mac.

**Pendências pequenas:**
- Na política do papel de leitura ficaram de fora `athena:ListDataCatalogs` e `athena:ListWorkGroups` (menor privilégio). Se o Power BI reclamar deles no passo 5, anote o erro exato; a mudança é no Terraform, no Mac (plan do Claude, apply do Ronald).
- O `on_schema_change` do histograma já voltou para `fail` (commit `bb97a44`).

## 2. Puxar o código no Windows

Se o repositório **ainda não existe** no Windows:

```powershell
git clone https://github.com/ronaldmartinsx/rideshare-marketplace-intelligence.git
cd rideshare-marketplace-intelligence
git switch fase-4-power-bi
```

Se **já existe** (de fases anteriores):

```powershell
cd rideshare-marketplace-intelligence
git status                  # precisa estar limpo; se não estiver, pare e veja o que é
git fetch origin
git switch fase-4-power-bi  # cria a branch local a partir da remota
git pull
git log --oneline -5        # o primeiro commit deve ser o deste guia
```

Notas:
- O Git do Windows converte fim de linha (LF ↔ CRLF) por padrão. Os arquivos do PBIP serão criados lá; definir um `.gitattributes` para eles faz parte do passo 5 (ADR 0011).
- Antes de trocar de máquina de novo: `git push` no Windows e `git pull` no Mac. As duas máquinas na mesma branch, uma de cada vez.

## 3. Passo 5, parte 1: atualizar o DSN

O DSN `rideshare-athena` foi criado na Fase 1 (guia `docs/guias/fase-1-passo-12-power-bi.md`) com o papel de administrador e o banco `dev_gold`. Agora ele passa a usar o papel de leitura.

1. Menu Iniciar → **"Fontes de Dados ODBC (64 bits)"** → aba **DSN de Usuário** → `rideshare-athena` → **Configurar**.
2. Trocar quatro campos:

| Campo | Antes (Fase 1) | Agora |
|---|---|---|
| Database | `dev_gold` | **`gold`** |
| Workgroup | `rideshare` | **`rideshare-bi`** |
| S3 Output Location | `s3://rmartins-rideshare-athena-results/resultados/` | **`s3://rmartins-rideshare-athena-results/bi/`** |
| Role name (em **Authentication Options**) | `AdministratorAccess` | **`RideshareLeituraGold`** |

3. **Test** → o navegador abre → login `ronald` + MFA → sucesso.
4. **OK** (o Test não salva; quem grava é o OK).

O papel `RideshareLeituraGold` também aparece no AWS access portal, ao lado do `AdministratorAccess`.

## 4. Passo 5, parte 2: importar a Gold e conferir

**Obter dados → Amazon Athena → DSN `rideshare-athena` → modo Import → "Use Data Source Configuration".** No navegador, o esperado é ver **só o banco `gold`**: a listagem é filtrada pelas permissões (confirmado pela API; falta confirmar no Desktop).

Importar estas 9 tabelas e conferir. Os números são a foto de 01/11/2026: 33 meses, de 2024-01 a 2026-09. Se o Mac ingerir um mês novo, eles crescem.

| Tabela | Linhas | Soma de `qtd_corridas` |
|---|---|---|
| `fct_demanda_zona_hora` | 11.905.597 | 672.148.703 |
| `fct_espera_histograma` | 14.404.307 | 664.669.321 (só corridas com espera válida) |
| `fct_od_mensal` | 3.659.444 | 672.148.703 |
| `dim_tempo_hora` | 26.304 | — |
| `dim_periodo_espera` | 2.376 | — |
| `dim_mes` | 36 | — |
| `dim_faixa_espera` | 18 | — |
| `dim_zona` | 265 | — |
| `dim_operadora` | 4 | — |

**Não importar** a `fct_od_diario` (55 milhões de linhas, 819 MB; substituída pela mensal, D2).

Custo: cada atualização completa lê ~500 MB no Athena (~US$ 0,0025). O limite do workgroup (1 GiB por consulta) barra qualquer consulta maior.

## 5. Passo 5, parte 3: relacionamentos (estrela com a hierarquia de tempo)

Todos 1 → N, filtro em direção única (da dimensão para a fato). Fonte: os testes `relationships` em `dbt/models/marts/_gold.yml`.

| Dimensão (lado 1) | Coluna | Tabela (lado N) | Coluna |
|---|---|---|---|
| `dim_mes` | `ano_mes` | `dim_periodo_espera` | `ano_mes` |
| `dim_periodo_espera` | `periodo_id` | `dim_tempo_hora` | `periodo_id` |
| `dim_tempo_hora` | `hora` | `fct_demanda_zona_hora` | `hora_embarque` |
| `dim_periodo_espera` | `periodo_id` | `fct_espera_histograma` | `periodo_id` |
| `dim_faixa_espera` | `faixa_id` | `fct_espera_histograma` | `faixa_id` |
| `dim_mes` | `ano_mes` | `fct_od_mensal` | `source_month` |
| `dim_zona` | `zona_id` | as 3 fatos | `zona_origem_id` |
| `dim_operadora` | `operadora_id` | as 3 fatos | `licenca_operadora` |

**Decisão em aberto para o passo 5:** a `fct_od_mensal` tem **duas** zonas (origem e destino) e a `dim_zona` só pode ter um relacionamento ativo com ela. Opções: destino como relacionamento inativo + `USERELATIONSHIP` nas medidas, ou uma segunda tabela de zona ("Zona de destino"). Decidir com o Claude antes de montar.

Por que a hierarquia em cadeia (Aula 1 e D1): o histograma não tem hora real, então não pode ligar à `dim_tempo_hora`. Uma segmentação na `dim_mes` filtra as quatro fatos com o mesmo recorte. Sem isso, o P90 ignoraria o filtro de data **em silêncio** (o erro da pergunta rápida da Aula 1).

**Também no passo 5:**
- Salvar como **PBIP** em `powerbi/`. Conferir em Opções → Recursos de visualização se o formato TMDL e o PBIR ainda exigem ativação (não verificado na versão atual do Desktop).
- Ocultar as colunas de chave; definir formatos (moeda, milhar).
- Escrever o ADR 0011, incluindo o `.gitattributes`.

## 6. Passos 6 e 7: medidas DAX ✍️ e reconciliação

- **Definições das métricas:** Seção 2.5 da spec e o `meta` de cada coluna em `dbt/models/marts/_gold.yml` (consistência semântica, Aula 2).
- **Razão das somas:** take rate = soma do repasse / soma da tarifa, nunca a média das razões por linha (28,2% × 20% no exemplo da aula).
- **Economia:** só corridas com tarifa válida (`qtd_corridas_tarifa_valida`, `milhas_tarifa_valida_total`). Mostrar o "% tarifa inválida" na página de economia (passo 1).
- **P50/P90 pelo histograma** (Aula 3):
  1. somar as contagens por faixa no recorte;
  2. calcular o alvo (p × total);
  3. acumular as faixas em ordem até o alvo;
  4. interpolar: início + (alvo − acumulado anterior) / contagem da faixa × largura.
  - A faixa "30+" não tem fim: não interpola.
  - Num visual por faixa, remover o filtro **só** da coluna da faixa.
- **Reconciliação (passo 7):** comparar o P90 do DAX com `approx_percentile` no Athena para alguns recortes; registrar em `docs/validacao/fase-4.md`. Para consultar o Athena do Windows:
  - **pelo console:** AWS access portal → papel `RideshareLeituraGold` → Athena → workgroup `rideshare-bi`; ou
  - **pela AWS CLI:** `aws configure sso`, com sessão `rideshare`, região `us-east-1`, escopo `sso:account:access` e papel `RideshareLeituraGold`. A start URL está no `~/.aws/config` do Mac ou no console do Identity Center; ela **não vai para o repositório**.
  - O papel é só leitura: o Claude pode rodar consultas por ele sem risco de apagar nada.
  - O `scripts/athena_roda.py` usa o workgroup `rideshare` fixo; para usá-lo com este papel, ele precisa aceitar outro workgroup (pequena mudança, com plano antes).

## 7. Passo 4 (se for no Windows): TopoJSON

Ferramenta nova: o Claude apresenta o plano antes de rodar. Esboço:
1. Baixar o shapefile das zonas na página "TLC Trip Record Data" ("Taxi Zone Shapefile"), numa pasta própria, fora do repositório.
2. Abrir o `.prj` e confirmar o sistema de coordenadas (segundo fontes secundárias, NAD83 / NY Long Island em pés).
3. `npx mapshaper@<versão fixada>`: reprojetar para WGS84, simplificar sem sumir com zonas pequenas, manter o `LocationID`, exportar TopoJSON.
4. Salvar em `powerbi/mapas/`; conferir o número de formas (perto de 263; as zonas 264/265 não têm forma; não verificado) e o tamanho do arquivo.

No Shape Map, a chave é `LocationID` = `zona_id`, com o **mesmo tipo** dos dois lados (número × texto não casa).

## 8. Se travar

| Sintoma | Causa provável |
|---|---|
| `AccessDenied` / role not found no Test do DSN | Role name digitado diferente de `RideshareLeituraGold` |
| Consulta negada no Power BI | Workgroup no DSN ainda `rideshare` (o papel só consulta pelo `rideshare-bi`) |
| Erro de permissão ao gravar o resultado | S3 Output Location ainda em `resultados/` (o papel só grava em `bi/`) |
| Navegador vazio ou mostrando `dev_gold` | Database no DSN ainda `dev_gold` |
| Erro citando `ListDataCatalogs` ou `ListWorkGroups` | Permissão deixada de fora de propósito: anotar o erro e acrescentar no Terraform (Mac) |
| Consulta cancelada por limite | Passou de 1 GiB: provavelmente a `fct_od_diario`, que não deve ser importada |
| `git switch` reclama de alterações locais | Há mudanças não commitadas no Windows: pare e veja o que é antes de descartar |
