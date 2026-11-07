# Fase 4: Power BI — registro de aprendizado

- **Período:** 31/10/2026 a ⏳ (gate de domínio previsto para 08/11/2026)
- **Objetivo:** responder às 4 perguntas de negócio da Seção 2.4 da spec.
- **Resultado:** "pronto quando" cumprido. As 4 perguntas têm resposta visível e insight escrito, numa página única com raias (ADR 0019), publicada no Power BI Service como foto dos dados. Prints e vídeo em [`powerbi/README.md`](../../powerbi/README.md). ⏳ Gate de domínio: seção 5.

> **Rascunho (07/11/2026).** Tudo, menos o resultado do gate, está registrado. A seção 5 e o período entram depois do gate.

---

## 1. O que foi construído

| Peça | Como | Onde |
|---|---|---|
| Tarifa ≤ 0 por operadora | Dois fenômenos (Lyft: tarifa zerada com repasse normal; Uber: zeros e negativos com repasse quase nulo). Regra mantida | `docs/validacao/fase-4.md`, seção 1 |
| Dimensões do período e OD mensal | `dim_mes`, `dim_periodo_espera`, `dim_faixa_espera`, `periodo_id`, `fct_od_mensal` com teste de reconciliação; produção reconstruída (32 meses) | `dbt/models/marts/`; [ADR 0017](../adr/0017-dimensoes-do-periodo-e-od-mensal.md) |
| Identidade de leitura | Permission set `RideshareLeituraGold` + workgroup `rideshare-bi`; 12/12 testes | `infra/terraform/iam_powerbi.tf`, `athena.tf`; [ADR 0018](../adr/0018-identidade-de-leitura-do-power-bi.md) |
| Conexão | Driver ODBC da Athena 2.5.0.0, DSN `rideshare-athena` com Browser SSO e catálogo único | Windows (fora do Git) |
| Modelo semântico | Import de 9 tabelas, 13 relacionamentos 1 → N, `dim_zona_destino`, cultura `pt-BR` | `powerbi/.../SemanticModel/` (TMDL) |
| ✍️ Medidas DAX | 15 medidas de métrica (Blocos A, B e C), com formato, pasta e descrição | `fct_demanda_zona_hora.tmdl` e demais tabelas |
| Medidas de apresentação | Título, ficha dos dados, cartões de KPI em HTML, rodapé, período e nome da zona | pasta "Apresentacao" no modelo |
| Reconciliação do P90 | DAX × histograma em SQL × `approx_percentile` em 9 recortes | `docs/validacao/fase-4.md`, seção 6 |
| Mapa das zonas | TopoJSON das 263 zonas, reprojetado para WGS84 e simplificado | `powerbi/mapas/` |
| Relatório | Página única 1440 × 5000, 4 raias, tema próprio, HTML Content, 3 mapas | `powerbi/.../Report/` (PBIR); `_brief/report-spec.md` |
| Gerador da página | Script que monta os visuais a partir do contrato de desenho | `powerbi/gerador/gerar_pagina.js` |
| Publicação | Power BI Service, foto dos dados; 6 prints e vídeo de 40 s | `docs/img/relatorio/`, `powerbi/README.md` |
| Documentação | ADRs 0011, 0017, 0018 e 0019; spec (2.5, 6.4, 10, 11.5, 14); glossário; guia do Windows | `docs/` |

**Critérios de pronto:**

| Critério | Evidência |
|---|---|
| Cada pergunta de negócio tem resposta visível | 4 raias, uma por pergunta, com mapas, matriz, séries e tabela |
| Insight escrito | Resposta numa frase no topo de cada raia e nos cartões |
| Medidas DAX documentadas | Descrição em cada medida (TMDL) e fórmulas iguais ao `meta` do dbt |
| Prints e vídeo curto | `docs/img/relatorio/` e vídeo no README |

**Custo da fase (Athena):**
- reconstrução de produção com as tabelas novas: ~US$ 0,69;
- cada atualização completa do Power BI: ~500 MB lidos, ~US$ 0,0025;
- reconciliação do P90: menos de US$ 0,01.

---

## 2. O que aprendi, por tecnologia

> O gate (seção 5) confirma o que ficou dominado. Esta seção registra o que foi ensinado e praticado.

- **Conectar a um warehouse externo:** o Power BI fala com o Athena por um driver ODBC, configurado num DSN. O DSN guarda banco, workgroup, saída e forma de login; o projeto guarda só o nome do DSN. O administrador ODBC de 32 bits não enxerga um driver de 64 bits.
- **Import × DirectQuery com cobrança por dado lido:** no Athena, cada consulta é paga pelo volume lido. Import lê uma vez por atualização (~500 MB); DirectQuery leria a cada clique de cada pessoa. Por isso Import, e por isso a OD mensal no lugar da diária.
- **Identidade de leitura:** o permission set é o "papel" que se atribui a uma pessoa numa conta, como uma atribuição de função no Entra ID. Menor privilégio começa fechado e abre com evidência (o `ListDataCatalogs` que o driver pediu).
- **Modelagem com grãos diferentes:** fato sem relacionamento com a dimensão não recebe o filtro, e isso não dá erro. Dimensão encolhida e cadeia de tempo resolvem fatos de grãos diferentes. Dois caminhos ativos fazem o Desktop desativar um, em silêncio.
- **Consistência semântica:** a fórmula nasce no `meta` do dbt (spec 2.5) e é reproduzida no DAX. Razão das somas, nunca média das razões; economia só com tarifa válida.
- **DAX:**
  - `CALCULATE` **substitui** o filtro do usuário na mesma coluna; `KEEPFILTERS` **restringe**;
  - `DIVIDE` sem o terceiro argumento devolve vazio ("não se aplica"); com `0`, afirma um número que não existe;
  - `REMOVEFILTERS` para medidas que devem ignorar a segmentação (período dos dados);
  - formato fixo × dinâmico.
- **Percentil por histograma em DAX:** total do recorte → alvo (p × total) → acumular as faixas em ordem → achar a primeira faixa que passa do alvo → interpolar dentro dela. Faixa larga = estimativa mais grosseira (até 56 s na faixa de 20–30 min).
- **Mapa com TopoJSON:** shapefile oficial → reprojetar para WGS84 → simplificar sem sumir com zonas pequenas → TopoJSON. A chave do mapa precisa ter o mesmo tipo dos dois lados.
- **PBIP:** modelo em TMDL e relatório em PBIR, em texto no Git. O Desktop avisa quando os arquivos mudam por fora (Apply), e o que muda pelo MCP só vai para o disco com Ctrl+S.
- **Desenho do relatório:** página única com raias, pergunta → resposta → evidência; tema JSON; técnica de destaque; HTML Content para os cartões; medida de apresentação × medida de métrica.
- **Cultura do modelo:** só muda antes de o modelo ter objetos (ou com o cache removido). Mesmo em `pt-BR`, os números dos gráficos seguem a configuração regional de quem vê.
- **Gateway:** a atualização no Service de uma fonte ODBC exige gateway local com DSN de sistema. Ficou fora da v1; o relatório publicado é uma foto.

---

## 3. Erros cometidos (e o que ensinaram)

**Do Ronald:**
- **Aula 1:** na pergunta rápida, não previu que o P90 ignoraria o filtro de data **em silêncio** sem ligação do histograma ao tempo. Virou a decisão D1 (ADR 0017).
- ⏳ **Aulas 2 a 4 (dadas no Mac):** completar com o registro das perguntas rápidas que ficou na memória do Claude Code no Mac.
- **✍️ Bloco A/B:**
  - usou `DIVIDE(..., 0)`; chegou sozinho à versão sem o terceiro argumento depois da pista;
  - o `CALCULATE` das corridas entrando no CBD substituía a segmentação do usuário (52.448.518 com "origem no CBD"). A pista não bastou; o Claude explicou o `KEEPFILTERS`, e o Ronald acertou a pergunta de fixação sobre o share.
- **✍️ Bloco C (P50/P90):** total do recorte, acumulado e interpolação certos. A escolha da faixa-alvo não saiu depois de duas pistas e foi corrigida pelo Claude.
- **Desktop:** moveu sem querer a faixa do cabeçalho; percebeu e reposicionou.
- **Acertos de destaque:**
  - os refinamentos de desenho das revisões 3 e 4 (cartões com borda e ícone, raias sem "carnaval de cores", texto sem jargão para o usuário final, formatação condicional na tabela);
  - a pergunta "o usuário final quer saber sobre 'definições de métricas na spec'?", que tirou o jargão do rodapé;
  - o nome da zona no mapa, pedido por ele.

**Do Claude Code (registrados por honestidade):**
- **Varredura de segredos com saída filtrada:** um commit passou com a saída da varredura filtrada. Combinado: varredura separada antes de cada commit, sem filtrar `visual.json`.
- **Gradiente do mapa:** seguiu a regra do validador (paradas sem `expr`) e os mapas ficaram em branco. O formato nativo do Desktop renderiza; ficou como exceção consciente.
- **Cultura do modelo:** propôs trocar a cultura com o modelo carregado; o motor recusou. A troca só funcionou com o cache removido e o modelo atualizado do zero.
- **Atualizar tudo de uma vez:** não previu que cada tabela abriria um login SSO em paralelo. Solução: atualizar primeiro uma tabela pequena.
- **Codificação:** o `Set-Content` do PowerShell gravou o `model.tmdl` com BOM; removido.
- **Tema:** o nome interno não batia com o nome registrado (faltava o `.json`).
- **Ranking por medida:** o filtro TopN do PBIR não ordena por medida; o ranking virou "zonas com P90 de 12 min ou mais".
- **Ferramentas:** comandos de uma linha em Node e no shell quebraram por escape várias vezes; scripts no scratchpad resolveram.

### Quem escreveu o quê

| Peça | Quem desenhou | Quem escreveu o código |
|---|---|---|
| Medidas dos Blocos A e B (DAX) | Ronald | Ronald. Ajuste do `DIVIDE` pelo Ronald depois da pista; `KEEPFILTERS` explicado pelo Claude e aplicado |
| P50/P90 pelo histograma (DAX, Bloco C) | Passos da Aula 3; montagem da medida pelo Ronald | Ronald: total do recorte, acumulado e interpolação. Claude: a escolha da faixa-alvo (`ADDCOLUMNS(ALL(dim_faixa_espera))` + `MINX(FILTER(...))`), depois de duas pistas |
| Formatos, pastas e descrições das medidas | — | Claude, pelo MCP, a pedido do Ronald |
| Medidas de apresentação (HTML e texto) | Ronald (conteúdo e refinamentos) | Claude, pela exceção de 07/11/2026 do `CLAUDE.md` (só formatam métricas existentes) |
| Modelos dbt das dimensões do período e da OD mensal | Plano D1/D2 aprovado pelo Ronald | Claude |
| Terraform da identidade de leitura | Decisões P1 a P4 do Ronald | Claude (plan); apply do Ronald |
| Relacionamentos do modelo | Plano do Claude, auditado pelo Ronald | Claude, pelo MCP |
| Contrato de desenho e gerador da página | Contrato combinado; refinamentos das revisões 3 e 4 do Ronald | Claude (`gerar_pagina.js`); ajustes finos de posição pelo Ronald no Desktop |
| TopoJSON | Plano do Claude | Claude (mapshaper), com as conferências no README |

---

## 4. Decisões tomadas

| Decisão | Registro |
|---|---|
| Tarifa ≤ 0: regra mantida, "% tarifa inválida" no relatório | Validação, seção 1 (sem ADR) |
| D1: dimensões do período para o histograma | [ADR 0017](../adr/0017-dimensoes-do-periodo-e-od-mensal.md) |
| D2: `fct_od_mensal` no Power BI; diária no Athena | ADR 0017 |
| D3: a página do Forecast vira "Uber × Lyft por zona"; Forecast na Fase 5 | spec, Seção 10 |
| D4: HTML Content (edição certificada) para os cartões | `_brief/report-spec.md` |
| D5 e P1 a P4: identidade de leitura, workgroup `rideshare-bi`, só a Gold, sessão de 8 h | [ADR 0018](../adr/0018-identidade-de-leitura-do-power-bi.md) |
| B2: DSN com papel de administrador provisório até o `ListDataCatalogs` | ADR 0018; validação, seção 4 |
| D6: PBIP (TMDL + PBIR) em `powerbi/` | [ADR 0011](../adr/0011-pbip-no-repositorio.md) |
| D7: zona de destino como segunda tabela | ADR 0017; `_gold.yml` |
| D8: receita por minuto no contrato | spec 2.5; `_gold.yml` |
| D9: nomes do dbt nas tabelas; medidas com nome de negócio, sem acento | guia do Windows |
| D10: P50/P90 na faixa 30+ devolvem 30 (piso) | spec 2.5 |
| D11: aviso de P90 aproximado acima de 15 min | spec 2.5 e 10; relatório |
| D12: página única com raias | [ADR 0019](../adr/0019-relatorio-pagina-unica-com-raias.md) |
| Cultura `pt-BR` no modelo | `model.tmdl`; validação, seção 7 |
| Medidas de apresentação escritas pelo Claude | `CLAUDE.md` (exceção de 07/11/2026) |
| Publicação no Service como foto, sem atualização agendada | spec, Seção 10 |

---

## 5. Gate de domínio

⏳ **A preencher depois do gate** (formato do Apêndice C da spec).

Candidatos levantados durante a fase:
- P90 pelo histograma: por que não dá para tirar média, e os passos no DAX (reforço 4 da Fase 3);
- "substituir × restringir" no `CALCULATE` (`KEEPFILTERS`);
- cadeia de tempo e o relacionamento ambíguo desativado em silêncio;
- Import × DirectQuery com cobrança por dado lido;
- menor privilégio e o `ListDataCatalogs`;
- consistência semântica entre o dbt e o DAX;
- reforços herdados: "quem faz o quê na esteira" e "fechar com evidência medida".

---

## 6. Pendências e melhorias anotadas

- **Mac:**
  - `athena:ListDataCatalogs` no `RideshareLeituraGold` (plan do Claude, apply do Ronald); depois, DSN de volta ao papel de leitura e uma atualização completa como teste;
  - `dbt parse` para conferir o `_gold.yml` alterado na Fase 4 (receita por minuto e zona de destino).
- **Windows:** apagar a reserva do cache (`cache.abf` de 548 MB, fora do repositório) só com a confirmação do Ronald.
- **Fase 7:** versão do relatório em inglês (pedido do Ronald em 05/11/2026).
- **Limitações aceitas:** formato `en-US` dos números nos gráficos para quem tem o sistema em inglês; respostas escritas fixas com dados até set/2026; relatório publicado sem atualização agendada.
- **Herdadas da Fase 3:** corridas inválidas no maior mês perto do aviso de 5 mil; contrato conferindo `isAdjustedToUTC`; alerta de "aguardando" longo.
