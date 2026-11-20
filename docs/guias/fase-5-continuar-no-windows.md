# Guia — Fase 5: a raia "Previsto × realizado" no Windows (Power BI)

> A memória do Claude Code fica no Mac. **Este arquivo é a fonte do estado** para trabalhar no Windows.

---

## ⏭️ Retomar aqui (próxima sessão no Windows)

1. **Prints** `01-cabecalho.png` (substitui), `07-raia5-previsao.png` e `08-hover-previsao.png` em
   `docs/img/relatorio/`. O `powerbi/README.md` já os referencia e está **sem commit**, esperando as imagens.
2. **Pendência nova: textos dinâmicos** (abaixo).
3. Depois: Mac, passo 9 (`fase-5.md` e gate).

### Pendência: textos dinâmicos (pedido do Ronald, 20/11/2026)

> "Nenhum texto pode ser chumbado; todos os textos devem conter valores dinâmicos. À medida que mais dados
> chegarem, não precisamos nos preocupar em fazer ajustes."

**Isso reverte a revisão 4 da Fase 4** ("o texto é fixo; o período fica explícito"), então pede ADR.

Inventário dos textos fixos no `gerar_pagina.js` (32 linhas com número ou mês):

| Onde | Exemplos | Dificuldade |
|---|---|---|
| 5 cartões de resposta do cabeçalho | "P90 de 8,1 para 10,1 min", "Leitura com dados até set/2026" | Número: fácil. Comparação "2024 × último período" precisa de regra de período |
| 5 parágrafos de abertura das raias | "receita por milha +9% (US$ 5,16 → 5,65)", "Breezy Point, City Island" | Números e rankings dinâmicos são viáveis; frases qualitativas precisam de regra |
| Subtítulos dos gráficos | "Breezy Point lidera, com P90 de 19 min", "a maior vantagem é em setembro (Labor Day)" | Líder e máximo: viáveis com `TOPN`/`MAXX` |
| Nota da raia 1 e textos alternativos | "Acima de 15 min…", descrição dos visuais | Fatos de método: podem ficar fixos (decidir) |

**A tensão a resolver junto:** número dinâmico é fácil; **afirmação** dinâmica não é. "A queda veio do resto de
Manhattan" ou "puxado pela Uber" podem deixar de ser verdade com dados novos. Para cada frase há três caminhos:
(a) calcular o sujeito (quem lidera, o sinal, o maior); (b) trocar por uma frase que vale para qualquer resultado;
(c) tirar. E as comparações precisam de **períodos definidos por regra** (ex.: "primeiro ano completo × últimos
12 meses"), não por datas fixas. Medidas de apresentação são do Claude; se faltar métrica, ela é ✍️ do Ronald.

---

## Progresso no Windows: passo 8 FECHADO (19 e 20/11/2026)

**Depois da pendência acima: voltar ao Mac para o passo 9** (`docs/aprendizados/fase-5.md` e o gate de domínio).
O registro abaixo é a matéria-prima dos dois.

| Bloco | Estado |
|---|---|
| A. Importar as 2 tabelas | ✅ Ronald |
| B. Auditoria | ✅ contagens e somas batem (ver nota abaixo) |
| C. 3 relacionamentos (seção 5) | ✅ Claude via MCP; 0 chaves órfãs; filtro de mês chega nas duas tabelas |
| C2. `dim_execucao` (não previsto no guia) | ✅ Claude via MCP: refinamento da decisão 3.1 (abaixo) |
| D. 12 medidas ✍️ | ✅ Ronald; `WAPE` (DAX) = `wape_modelo` (Python) nos 6 meses, até a 14ª casa |
| E. Acabamento | ✅ Claude: nomes, formatos (`0.00%`, `0.00 "pp"`), pastas, descrições, chaves escondidas |
| F. Raia 5 na página | ✅ gerador revisão 5 (commit `3e86e2a`); contrato em `_brief/report-spec.md`, "Revisão 5" |
| G. README e prints | ✅ README; prints `01`, `07`, `08` em `docs/img/relatorio/` |

### Refinamento da decisão 3.1: a `dim_execucao`

A coluna `execucao` existe nas duas tabelas de ML, mas elas não se ligam entre si. Uma segmentação feita com
`ml_forecast_demanda[execucao]` deixaria a `ml_backtest_metricas` somando as duas execuções (setembro duas vezes).
Solução: `dim_execucao` (Referência da `ml_backtest_metricas` no Power Query, uma linha por execução), ligada às
duas tabelas (N → 1, direção única). Não muda a decisão, então não abre ADR. Quem notou: o Claude, ao revisar onde
o `HASONEVALUE` do Ronald ia perguntar.

### Quem escreveu o quê (para o `fase-5.md`)

| Peça | Quem desenhou | Quem escreveu |
|---|---|---|
| Regras das medidas (6 cenários) | Ronald | — |
| 12 medidas que calculam métrica (DAX) | Ronald | Ronald. O filtro de backtest nas medidas de métricas foi esquecido e corrigido por ele depois da pista ("só uma está errada hoje; uma herda") |
| `dim_execucao` e 5 relacionamentos | Claude, aprovado pelo Ronald | Claude, pelo MCP |
| Formatos, pastas, descrições, renomeações | Plano aprovado pelo Ronald | Claude, pelo MCP |
| Medidas de apresentação (`HTML Execucao no Ar`, `HTML Limitacoes`, `HTML Cartoes Previsao`, `Texto Rodadas Vencidas`; `HTML Titulo`) | Conteúdo aprovado pelo Ronald; cartões HTML a pedido dele | Claude (exceção de 07/11) |
| Raia 5 no gerador | 4 decisões do Ronald (recomendações aceitas); revisão 5b a pedido dele | Claude |
| Textos da raia | Rascunhos do Claude, aceitos pelo Ronald | Claude. O baseline do rascunho ("um ano antes") estava errado e foi corrigido pelo código antes de entrar |

### O que o Ronald acertou e errou (para o gate)

| Ponto | Resultado |
|---|---|
| Cenário 1: função que percorre linha a linha | ✅ `SUMX` |
| Cenário 2: produção sem realizado | ✅ Regra ("ignorar"). ⚠️ Motivo impreciso: disse "meses que ainda estão por vir"; outubro já passou, o dado é que não chegou (atraso da TLC) |
| Mecanismo do cenário 2 | ✅ "BLANK é igual a 0 no DAX" (numa conta). Não fez a conta do WAPE contaminado (30,5%); o Claude mostrou |
| Cenário 3: nenhuma execução | ✅ Duas camadas: seleção única no visual + `HASONEVALUE`, com a justificativa certa ("não contar com uma camada só") |
| Cenário 4: realizado zero | ❌ Primeiro respondeu que não precisava de proteção. Depois da pista: ✅ distinção excelente entre **0** (não houve corrida) e **BLANK** (desconhecido), e `DIVIDE` |
| Cenário 5: linha de produção nas métricas | ✅ "Ignoram", filtro dentro da medida |
| Cenário 6: régua do cartão | ✅ Média dos meses dos dois lados (maçã com maçã) |
| Checagem: por que `HASONEVALUE` em todas as medidas de métricas | ✅ "Nenhuma reaproveita a outra". Parcial: a dele mesmo, `Rodadas Vencidas`, reaproveita `Rodadas Testadas` e herda a proteção |
| `Ganho (pp)` ÷ 100 | ⚠️ Dividiu por 100 (mostraria "1,18%"); voltou para pontos depois da pergunta sobre o leitor |
| Escala do WAPE das métricas (12,35 × 0,1235) | ✅ Resolveu sozinho com ÷ 100 |

**Pontos para o gate:** WAPE agrupado × média dos meses (12,91% × 12,92%) e quando cada um vale; BLANK × 0 numa
conta e numa divisão; por que a `dim_execucao` existe (filtro que precisa alcançar duas tabelas, como a
`dim_zona_destino`); pp × %.

**Do Claude (por honestidade):** o gerador rodou com o Desktop ainda aberto, porque a checagem estava no mesmo
comando, em vez de vir antes. Nada se perdeu (o modelo já estava salvo; o Ronald fechou sem salvar). Combinado:
conferir que o Desktop fechou **antes** de rodar o gerador.

**Nota da auditoria:** o Power BI soma `qtd_corridas_real` do backtest oficial em **126.277.028**, não 126.277.020.
Nenhuma linha tem fração, então a soma em Double é exata. Hipótese (não verificada): no Athena a coluna é `REAL`
(32 bits), a soma sai `REAL` e é exibida como `1.2627702E8`, com 8 dígitos significativos. Para confirmar no Mac:
`sum(cast(qtd_corridas_real as double))`. Não muda decisão; corrigir o número aqui e na validação.

**O 12,92% é a média dos 6 WAPEs mensais.** O WAPE agrupado (Σ erro ÷ Σ real) dá **12,91%**. O viés de −2,38% é
agrupado (a média mensal dá −2,39%). O baseline (14,09%) só existe como média mensal.

**Cenários extras para o bloco D:**
- 5: na `ml_backtest_metricas` a coluna é `tipo` (não `tipo_rodada`), e a linha de outubro tem
  `venceu_baseline = FALSE` e WAPE nulo — "venceu X de Y" sem filtro dá "6 de 7".
- 6: o cartão do modelo mostra 12,91% (agrupado) ou 12,92% (média mensal)? A comparação com o baseline tem de
  usar a mesma régua.

---

## 0. Comece por aqui (estado em 20/11/2026)

A Fase 5 tem **8 dos 10 passos fechados**. Falta este (passo 8) e o gate (passo 9).

**O que já existe e está em produção:**

| Peça | Estado |
|---|---|
| 4 tabelas dbt de ML na Gold | ✅ construídas, 45 nós verdes |
| O modelo LightGBM | ✅ **venceu o baseline em 6 de 6 rodadas** |
| DAG `ml_forecast` | ✅ roda ponta a ponta no contêiner |
| `gold.ml_forecast_demanda` | ✅ 1.345.632 + 383.568 linhas |
| `gold.ml_backtest_metricas` | ✅ 7 + 2 linhas |

**O resultado da fase, em uma linha:** o modelo errou **12,92%** contra **14,09%** do baseline nas 6 rodadas
oficiais, vencendo em todas, e prevê **22.156.449 corridas para outubro de 2026**.

**O que FALTA aqui:** a raia 5 do relatório, "Previsto × realizado". Ela foi tirada da Fase 4 (decisão D3) e
adiada para cá, porque dependia de o modelo existir.

---

## 1. Puxar o código no Windows

A branch `fase-5-ml` foi empurrada em 20/11/2026 com 25 commits. No Windows:

```powershell
cd <repositorio>
git fetch origin
git checkout fase-5-ml
git pull
```

Confira que chegou: `git log --oneline -1` deve mostrar `a268a5c`.

**O DSN não precisa de nada.** Ele já está no papel `RideshareLeituraGold` desde 09/11, e as tabelas novas estão
no banco `gold`, que esse papel já lê. **Nenhuma mudança de IAM é necessária para este passo.**

---

## 2. As duas tabelas novas

### `gold.ml_forecast_demanda` — a previsão linha a linha

Grão: **hora-alvo × zona × execução**.

| Coluna | Tipo | O que é |
|---|---|---|
| `hora_alvo` | timestamp | a hora prevista |
| `zona_id` | int | a zona |
| `previsao` | double | o palpite do modelo |
| `qtd_corridas_real` | float | **o que de fato aconteceu** (nulo na previsão de produção) |
| `intervalo_inferior` / `_superior` | double | **sempre nulos nesta versão** (decisão D4; exigiria regressão quantílica) |
| `versao_modelo` | string | qual modelo produziu a linha |
| `tipo_rodada` | string | `backtest` (tem real) ou `producao` (não tem) |
| `execucao` | string | identifica a execução inteira do backtest |
| `mes_alvo` | string | mês previsto (partição) |

**A simplificação que importa:** o `qtd_corridas_real` está **na mesma tabela** que o `previsao`. Então
"previsto × realizado" se faz dentro de uma tabela só, sem juntar com a `fct_demanda_zona_hora`.

### `gold.ml_backtest_metricas` — uma linha por rodada

Grão: **execução × mês previsto**. Traz `wape_modelo`, `wape_baseline`, `ganho_pp`, `vies_modelo`,
`vies_baseline`, `venceu_baseline`, `linhas_treino`, `segundos_treino`, `versao_modelo`.

**O baseline vem na mesma linha de propósito:** métrica de modelo sem a régua ao lado é número solto.

---

## 3. As TRÊS decisões de modelagem, já resolvidas

Leia antes de importar. As três são armadilhas reais, não detalhes.

### 3.1 ⚠️ Filtre UMA execução, sempre

A tabela tem **duas execuções** hoje:

| `execucao` | O que é | Rodadas de backtest |
|---|---|---|
| `20261116T233529Z` | a do veredito oficial (Mac) | **6** |
| `20261120T024657Z` | teste da DAG no contêiner | 1 |

As duas têm a **mesma previsão de produção** para outubro. Somar as duas **duplica** setembro e outubro.

**Decisão:** uma **segmentação de dados por `execucao`** na raia, com `20261116T233529Z` selecionada, e um
**cartão mostrando qual execução está no ar**. A segmentação existe porque o histórico de execuções é um recurso
(é o versionamento de modelo funcionando), não um estorvo — mas medida aditiva sobre várias execuções dá número
errado, e o cartão evita que isso passe em silêncio.

### 3.2 ⚠️ NÃO relacione `mes_alvo` com a `dim_mes`

A cadeia de tempo do modelo é `dim_mes` → `dim_periodo_espera` → `dim_tempo_hora` (ADR 0017). Ligar a
`ml_forecast_demanda` pela `hora_alvo` na `dim_tempo_hora` **já faz o filtro de mês chegar nela** por essa cadeia.

Ligar `mes_alvo` direto na `dim_mes` criaria um **segundo caminho** — exatamente o "atalho que desativa a cadeia
em silêncio" que você pegou na Fase 4. O Power BI desativaria um dos relacionamentos sem avisar de forma clara.

**Para a `ml_backtest_metricas` é diferente:** ela não tem hora, só mês. Ali `mes_alvo` → `dim_mes.ano_mes` é o
relacionamento certo, e não cria caminho duplo porque ela não se liga à `dim_tempo_hora`.

### 3.3 ⚠️ `tipo_rodada` separa duas perguntas diferentes

| Pergunta da raia | Filtro |
|---|---|
| "O modelo acerta?" (previsto × realizado) | `tipo_rodada = "backtest"` |
| "Quantas corridas em outubro?" | `tipo_rodada = "producao"` |

Misturar os dois num visual soma um mês sem gabarito com seis que têm.

---

## 4. Importar e conferir

No Power BI Desktop, com o DSN `rideshare-athena`, importe as duas tabelas. **Desligue a detecção automática de
relacionamentos** (Arquivo → Opções → Atual → Carregamento de dados), como na Fase 4.

**Números para auditoria.** Depois de importar, sem nenhum filtro:

| Tabela | Linhas |
|---|---|
| `ml_forecast_demanda` | **1.729.200** (1.345.632 + 383.568) |
| `ml_backtest_metricas` | **9** (7 + 2) |

E filtrando `execucao = "20261116T233529Z"`:

| `tipo_rodada` | Linhas | Meses | Σ `previsao` | Σ `qtd_corridas_real` |
|---|---|---|---|---|
| `backtest` | 1.150.704 | 6 | **123.265.954** | **126.277.020** |
| `producao` | 194.928 | 1 | **22.156.449** | (nulo) |

Se esses números baterem, a importação está correta. Se não baterem, **pare** — é problema de importação, não de
medida, e seguir só vai esconder a causa.

> Repare: previsto 123,27 M contra real 126,28 M nas 6 rodadas, ou seja **−2,38%**. É o viés do L1 explicado na
> validação, seção 8.2 — o modelo subestima de propósito, por consequência da função de perda escolhida.

---

## 5. Relacionamentos (2 novos)

| De | Para | Cardinalidade | Direção |
|---|---|---|---|
| `ml_forecast_demanda[hora_alvo]` | `dim_tempo_hora[hora]` | N → 1 | única |
| `ml_backtest_metricas[mes_alvo]` | `dim_mes[ano_mes]` | N → 1 | única |

Mais o relacionamento de zona, se quiser quebrar a previsão por zona:

| `ml_forecast_demanda[zona_id]` | `dim_zona[zona_id]` | N → 1 | única |

**Confira depois de criar:** um filtro de mês na segmentação existente tem de mexer nos visuais das duas tabelas
novas. Se não mexer, o relacionamento está na direção errada ou foi criado contra a tabela errada.

---

## 6. ✍️ As medidas DAX (são suas)

Pelo `CLAUDE.md`, medida que **calcula métrica** é sua; medida de **apresentação** (só formata texto a partir de
métrica existente) eu escrevo. Aqui todas calculam.

### Contrato das medidas

| Medida | O que precisa fazer |
|---|---|
| `Previsão` | soma de `previsao` |
| `Realizado` | soma de `qtd_corridas_real` |
| `Erro Absoluto` | soma de \|previsao − real\| **linha a linha** |
| `WAPE` | `Erro Absoluto ÷ Realizado` — **razão das somas** |
| `Viés %` | `(Previsão − Realizado) ÷ Realizado` |

### Tabela de cenários — decida antes de escrever

| # | Cenário | Pergunta |
|---|---|---|
| 1 | O `Erro Absoluto` precisa do valor absoluto **por linha**, não da diferença das somas | Qual função DAX percorre linha a linha? |
| 2 | Linhas de `producao` têm `qtd_corridas_real` nulo | O que o `WAPE` devolve ali? Deve devolver algo? |
| 3 | Nenhuma execução selecionada na segmentação | As medidas somam tudo e dão número errado. Como avisar? |
| 4 | `Realizado` igual a zero num recorte | A divisão precisa de proteção? |

**A pegadinha do cenário 1** é a mesma do take rate da Fase 4 e do WAPE em SQL do passo 4: a diferença das somas
**não é** a soma das diferenças absolutas. Se `Erro Absoluto` for `ABS([Previsão] - [Realizado])`, você calculou o
**viés**, não o erro — e o WAPE sairia pequeno e errado.

> Dica, sem dar a resposta: você já resolveu isso em SQL no passo 4, com `sum(abs(...))`. Em DAX a função que
> percorre linha a linha e depois agrega começa com as mesmas quatro letras de `SUM`.

**Conferência:** com `execucao = "20261116T233529Z"` e `tipo_rodada = "backtest"`, o seu `WAPE` tem de dar
**12,92%** na média das 6 rodadas, e o `Viés %` tem de dar **−2,38%** no total. Esses números estão na tabela
`ml_backtest_metricas` e na validação, seção 8 — se o DAX divergir do SQL, uma das duas implementações está errada,
e é exatamente a reconciliação que você fez na Fase 4 para o P90.

---

## 7. Os visuais da raia 5

A raia segue o padrão das outras (ADR 0019): a pergunta, a resposta numa frase, os visuais como evidência.

**Pergunta:** *"Dá para prever a demanda, e quanto melhor que o palpite óbvio?"*

**Resposta sugerida (confira com os números):** *"Sim. O modelo errou 12,9% contra 14,1% do palpite sazonal,
vencendo nas 6 janelas testadas — e a vantagem é maior nos meses de feriado, onde o palpite óbvio falha."*

| # | Visual | Conteúdo |
|---|---|---|
| 1 | Cartões | `WAPE` do modelo, `WAPE` do baseline, ganho em pontos, "venceu em X de Y" |
| 2 | Linhas ou colunas por mês | `wape_modelo` × `wape_baseline` da `ml_backtest_metricas`, 6 rodadas |
| 3 | Linha por dia ou hora | `Previsão` × `Realizado` num mês escolhido (usa a `dim_tempo_hora`) |
| 4 | Cartão grande | a previsão de **outubro/2026**: 22.156.449 (filtro `tipo_rodada = "producao"`) |
| 5 | Cartão de texto | **as limitações** (ver abaixo) |

### O visual 5 não é opcional

As três limitações da fase, que precisam estar visíveis no relatório e não só na documentação:

1. **O modelo subestima ~2,4%**, por consequência da função de perda escolhida (L1 otimiza a mediana).
2. **O clima usado é o observado, não previsto** — vazamento aceito e documentado (spec 9.1). Em produção só
   existiria previsão do tempo, com erro, então o resultado do backtest é otimista.
3. **A previsão não é operacional:** os dados da TLC saem com ~2 meses de atraso, então o mês previsto já passou
   quando a previsão fica pronta. O enquadramento honesto é "validado em backtest; em produção seria alimentado
   por streaming".

Relatório que mostra só o número bom é propaganda. O que mostra o número e o preço dele é engenharia.

---

## 8. Se travar

| Sintoma | Causa provável |
|---|---|
| Números o dobro do esperado | Nenhuma execução filtrada na segmentação (decisão 3.1) |
| Um relacionamento aparece pontilhado | Caminho duplo: você ligou `mes_alvo` na `dim_mes` (decisão 3.2) |
| `WAPE` muito baixo e bonito | `Erro Absoluto` está usando a diferença das somas (cenário 1 do passo 6) |
| Filtro de mês não mexe no visual novo | Relacionamento na direção errada, ou contra a tabela errada |
| Outubro soma junto com os outros meses | Falta o filtro `tipo_rodada` (decisão 3.3) |
| `AccessDenied` no Athena | A sessão do Browser SSO expirou (8 h); refaça o login no navegador |

---

## 9. Quando terminar

1. Commitar o PBIP (TMDL + PBIR) como nas fases anteriores.
2. Prints da raia nova em `docs/img/relatorio/`.
3. Atualizar o `powerbi/README.md`.
4. Voltar ao Mac para o passo 9: `docs/aprendizados/fase-5.md` e o **gate de domínio**.

A branch já está no GitHub, então basta `git push` do Windows.
