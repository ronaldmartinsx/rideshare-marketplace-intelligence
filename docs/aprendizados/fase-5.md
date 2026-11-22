# Fase 5: Previsão de demanda (ML) — registro de aprendizado

- **Período:** 10/11/2026 a 22/11/2026 (passos 1 a 7 no Mac; passo 8, textos dinâmicos e gate no Windows)
- **Objetivo:** um modelo que vença o baseline, ou um relatório honesto de que não venceu (spec, Seção 12).
- **Resultado:** "pronto quando" cumprido. O backtest roda de forma reprodutível (semente fixa, mesmo resultado
  em duas execuções) e o resultado está documentado: o LightGBM errou **12,92%** de WAPE contra **14,09%** do
  baseline sazonal e **venceu nas 6 rodadas oficiais**. Previsão de outubro/2026: **22.156.449 corridas**. A raia 5
  do relatório mostra o resultado e as limitações. Gate de domínio aprovado, com cinco reforços (seção 5).

> As aulas dos passos 1 a 7 aconteceram no Mac, e o registro detalhado delas ficou na memória do Claude Code de
> lá. Este documento usa o que está no repositório (`docs/validacao/fase-5.md`, commits, guia do Windows) e a
> sessão do Windows.

---

## 1. O que foi construído

| Peça | Como | Onde |
|---|---|---|
| Medição da demanda e escolha das zonas | Dados densos e demanda **não** concentrada; filtro **semântico** (zonas conhecidas, dentro de NY), não estatístico | Validação, seção 1; [ADR 0020](../adr/0020-zonas-por-filtro-semantico.md) |
| Série limpa | `ml_demanda_hora_zona`: hora × zona, com zeros explícitos | `dbt/models/marts/` |
| Features | `ml_features_demanda`: corte × hora-alvo × zona, 4 lags medidos a partir do **corte**, calendário, clima observado, horizonte | `dbt/models/marts/`; [ADR 0021](../adr/0021-lags-a-partir-do-corte.md) |
| ✍️ Baseline | `ml_baseline_demanda`: média da mesma hora da semana nas 4 semanas antes do corte | `dbt/models/marts/` |
| ✍️ WAPE do baseline | `ml_wape_baseline`: a régua em SQL, antes do modelo, com `vies_pct` | `dbt/models/marts/` |
| Código de ML | `janelas.py` (rodadas walk-forward), `dados.py` (Athena → pandas), `modelo.py` (LightGBM L1, versão), `backtest.py`, `persistencia.py` | `airflow/include/ml/`; [ADR 0022](../adr/0022-codigo-de-ml-no-include-do-airflow.md) |
| DAG `ml_forecast` | Backtest + previsão de produção no contêiner, gravando na Gold | `airflow/dags/ml_forecast.py` |
| Tabelas de saída | `ml_forecast_demanda` (previsão linha a linha, com o realizado) e `ml_backtest_metricas` (modelo × baseline por rodada), em **append** por execução | Gold (Iceberg) |
| Raia 5 do relatório | "Dá para prever a demanda?": execução, 5 cartões HTML, erro por janela, previsto × realizado por dia, limitações | `powerbi/`; `_brief/report-spec.md` (revisão 5) |
| Modelo semântico da raia 5 | 2 tabelas, `dim_execucao`, 5 relacionamentos, 12 medidas ✍️ do Ronald | `powerbi/.../SemanticModel/` |
| Textos dinâmicos | Respostas, aberturas e 15 subtítulos gerados por medida, com períodos e afirmações por regra | [ADR 0023](../adr/0023-textos-do-relatorio-por-medida.md); revisão 6 |
| Correções no relatório | Borda das formas (contorno em duas entradas), links do rodapé que nunca abriam (caixa de texto → botão), subtítulo que não cabia | `powerbi/gerador/gerar_pagina.js` |
| Publicação | Link público ("Publicar na Web") nos READMEs; prints 01, 07 e 08 | `README.md`, `powerbi/README.md`, `docs/img/relatorio/` |

**Critérios de pronto:**

| Critério | Evidência |
|---|---|
| Backtest reprodutível | Semente fixa e modo determinístico; duas execuções com o mesmo resultado (validação, 9.1); execução de teste reproduz setembro da oficial |
| Resultado documentado, positivo ou não | Validação, seções 8 e 10; raia 5; README |
| Baseline e WAPE escritos pelo Ronald | Validação, seções 4 e 5 |
| Página do Power BI | Raia 5 (decisão D3 da Fase 4 trouxe o Forecast para cá) |

**Custo da fase (Athena):** centavos. Leituras de medição e conferência em MB (validação, seções 1 a 3); 7 leituras
por backtest (validação, 8.3); a análise das 32 rodadas leu as features uma vez.

---

## 2. O que aprendi, por tecnologia

> O gate (seção 5) confirma o que ficou dominado. Esta seção registra o que foi ensinado e praticado.

- **Séries temporais:** a **tendência** é a direção de longo prazo da própria série (a maré); a **sazonalidade** é
  o padrão que se repete (as ondas). Aqui, a sazonalidade que manda é a **hora da semana** (168 horas).
- **Baseline primeiro:** a régua barata, conferida em SQL **antes** do modelo existir. A spec aceita as duas
  saídas: o modelo vence, ou o relatório honesto mostra que não venceu. O nosso baseline é forte (~13% de WAPE).
- **WAPE × MAPE:** WAPE = Σ|erro| ÷ Σ real, a razão das somas, ponderada pelo volume. O MAPE tira a média dos
  erros percentuais linha a linha: cada linha pesa igual e ele divide por zero nas zona × hora sem corridas.
- **Lags e calendário:** 4 colunas de lag (1 a 4 semanas, mesma hora da semana, antes do corte) e calendário
  conhecido com antecedência (feriado, tipo de dia, mês). O baseline **reage**; o modelo **antecipa o que já viu**
  (validação, 10.3: o primeiro Natal não ajuda, o segundo dá o maior ganho).
- **Vazamento:** usar informação que não existiria no momento da previsão. Evitado: lags da hora-alvo (ADR 0021,
  "a foto no bolso"), com dois testes dbt que provam a ausência. Aceito e documentado: o clima observado.
- **Gradient boosting (LightGBM):** árvores pequenas em sequência, cada uma corrigindo o erro das anteriores
  (o minigolfe). O Python dá as ordens; o LightGBM, em C++, faz o trabalho pesado, dentro do contêiner.
- **Perda L1 × L2:** a L1 mira o típico (a mediana) e combina com o WAPE; a L2 mira a média e persegue picos. A
  escolha da L1 deixa um viés de −2,4% na soma, documentado como limitação.
- **Backtest walk-forward:** treina só com o passado, prevê um mês nunca visto, anda para a frente com janela
  crescente. Sortear linhas deixaria o modelo "colar da vizinha" (preencher um buraco em vez de prever o futuro).
- **Erro e agregação:** o WAPE de 12,9% por zona × hora vira 3,9% no total do dia, porque erros para cima e para
  baixo se cancelam ao somar.
- **Versionamento de modelo:** execução, versão (ambiente, corte, instante), métricas lado a lado com o baseline,
  tamanho do treino, o modelo salvo no S3 e a semente fixa. Responde "piorou? e foi o dado, o código ou os
  parâmetros?".
- **Append × overwrite:** o dbt sobrescreve porque reconstrói (o saldo do banco); uma previsão é um fato no tempo
  e não se reconstrói (o diário). O preço do append: duplicação (o bug de 19/11) e a leitura de uma execução só.
- **Power BI com ML:** auditar a importação antes de medir; a `dim_execucao` para o filtro alcançar duas tabelas;
  a execução padrão **por regra** (`is_padrao`, `[Execucao Alvo]`); `SUMX` linha a linha; BLANK × 0 numa conta
  e numa divisão; reconciliação DAX × Python.
- **Inteligência de tempo e textos por regra:** janela de 12 meses ancorada no último mês com dados; âncora por
  evento (a taxa do CBD); afirmação com limiar ("estável", "puxado por"); por que a medida vai numa `VAR` antes
  do filtro do `CALCULATE`; o que o `REMOVEFILTERS(dim_mes)` protege.

---

## 3. Erros cometidos (e o que ensinaram)

**Do Ronald:**
- **✍️ WAPE do baseline (validação, 5.3 e 5.4):** a primeira versão deixava o denominador contar linhas sem
  palpite e o numerador não, o que daria um WAPE **artificialmente melhor**, sem erro nenhum. Tropeços de SQL:
  `countif` × `count_if`; `count_if` sobre um número (vinha de copiar `count_if(is_*)` da Fase 3); colunas
  calculadas na CTE e esquecidas no `select` final.
- **✍️ Medidas da raia 5:** respondeu que o `Realizado` igual a zero não precisava de proteção (depois, distinção
  excelente entre **0** e **BLANK**, com `DIVIDE`); dividiu o `Ganho (pp)` por 100 (mostraria "1,18%"); esqueceu o
  filtro de backtest nas medidas de métricas e corrigiu depois da pista.
- **Acertos de destaque:**
  - a coluna `vies_pct`, **fora do contrato**, que mostrou que o baseline quase não tem viés e que a barra era mais
    alta do que o WAPE sugeria;
  - as duas camadas contra somar execuções ("não contar com ovo no cu da galinha");
  - o pedido de **nenhum texto chumbado**, que virou o ADR 0023 e revelou que a Lyft recua em Manhattan no último
    ano;
  - os pedidos de revisão do relatório (cartões em HTML, espaço ocioso, subtítulo que não cabia, links que não
    abriam).

**Do Claude Code (registrados por honestidade):**
- **Gerador com o Desktop aberto:** a checagem do Desktop estava no mesmo comando do gerador e não o impediu de
  rodar. Nada se perdeu. Combinado: conferir o `PBIDesktop.exe` fechado **antes**, em comando separado (memória do
  Windows).
- **Baseline no rascunho:** escreveu "o mesmo horário um ano antes"; o `ml_baseline_demanda.sql` diz "4 semanas
  antes". Pego antes de entrar no relatório.
- **Pré-seleção de segmentação:** disse que a segmentação poderia abrir filtrada por outra coluna; não pode. A
  solução real foi a `[Execucao Alvo]`.
- **Contorno das formas:** escreveu só a entrada com seletor; a borda azul apareceu depois da regeneração.
- **Links do rodapé:** caixas de texto com ação desde a Fase 4; nunca abriram. Viraram botões.
- **Textos dinâmicos:** concordância ("nas 1 janelas"), comparação de caixa de texto com corte errado (`LEFT(..., 9)`),
  variação mês a mês lida como tendência (sazonalidade) e cartões que cortavam o texto. Todos pegos nos testes
  de borda ou na revisão do Ronald.
- **Vídeo do README:** instalou o ffmpeg, que o Controle de Aplicativos do Windows bloqueou (não contornado; foi
  desinstalado). O vídeo ficou o da Fase 4, com aviso.

### Quem escreveu o quê

| Peça | Quem desenhou | Quem escreveu |
|---|---|---|
| Baseline (`ml_baseline_demanda`, SQL) | Ronald | **Ronald**; refactor (CTE, comentários, caixa) pelo Claude a pedido, com resultado idêntico provado |
| WAPE do baseline (`ml_wape_baseline`, SQL) | Ronald | **Ronald**, incluindo o `vies_pct`; o Claude revisou e aplicou o `coalesce` e os comentários a pedido |
| Série limpa e features (dbt) | Decisões do Ronald (D1, zonas) | Claude |
| Rodadas walk-forward (`janelas.py`) | Tabela de cenários combinada com o Ronald | Claude, com 13 testes, um por cenário |
| Demais módulos Python e a DAG | Plano aprovado pelo Ronald | Claude |
| Terraform (prefixo `ml/` do Airflow) | — | Claude (plan); apply do Ronald |
| 12 medidas da raia 5 (DAX) | Ronald (6 cenários) | **Ronald** |
| `dim_execucao`, relacionamentos, formatos, pastas | Plano aprovado pelo Ronald | Claude, pelo MCP |
| Medidas de apresentação da raia 5 | Conteúdo aprovado pelo Ronald | Claude (exceção de 07/11) |
| Textos dinâmicos: ~20 medidas de janela e métrica | Princípios aprovados pelo Ronald | **Claude, por autorização expressa do Ronald nesta frente** (exceção à regra ✍️) |
| Textos dinâmicos: ~25 medidas de texto | Regras aprovadas raia a raia pelo Ronald | Claude |
| Prova de conceito do subtítulo dinâmico | Claude | **Ronald, no Desktop** |
| Gerador, revisões 5, 6 e 6b | Decisões e pedidos do Ronald | Claude |

---

## 4. Decisões tomadas

| Decisão | Registro |
|---|---|
| Zonas por filtro semântico | [ADR 0020](../adr/0020-zonas-por-filtro-semantico.md) |
| D1: lags a partir do corte | [ADR 0021](../adr/0021-lags-a-partir-do-corte.md) |
| Código de ML no `include/` do Airflow | [ADR 0022](../adr/0022-codigo-de-ml-no-include-do-airflow.md) |
| Perda L1 (combina com o WAPE), semente fixa | `airflow/include/ml/config.py`; validação, 8.2 |
| As 6 rodadas da spec são o resultado oficial; as 31 são análise | Validação, 6.3 e 10 |
| D4: intervalos de previsão nulos (exigiriam regressão quantílica) | Validação, 9.3 |
| Tabelas `ml_*` em append, por execução | `persistencia.py` |
| Raia 5 na página única (a D3 da Fase 4 adiada para cá) | `_brief/report-spec.md`, revisão 5 |
| `dim_execucao` (refinamento da decisão 3.1, sem ADR) | Guia do Windows |
| Execução padrão por regra (`is_padrao`, opção A) | ADR 0023 |
| Textos por medida, com períodos e afirmações por regra | [ADR 0023](../adr/0023-textos-do-relatorio-por-medida.md) |
| Publicação na web (dados públicos da TLC) | README |
| Layout mobile: descartado pelo Ronald | — |

---

## 5. Gate de domínio

Formato híbrido (o mesmo das fases anteriores), em 22/11/2026, no Windows.

### Explicação com as próprias palavras (resumo da avaliação)

| Item | Avaliação |
|---|---|
| Tendência e sazonalidade | ⚠️ Sazonalidade certa. Tendência definida como "direção nos meses seguintes" (é a direção de longo prazo da própria série). Faltou a sazonalidade da hora da semana |
| Baseline | ⚠️ Ideia certa; faltou dizer qual é o nosso. "Tem sempre que ganhar" corrigido: a spec aceita o relatório honesto |
| WAPE × MAPE | ⚠️ WAPE certo; MAPE definido como "média simples dos erros" (é a média dos erros percentuais); motivo embaralhado (divisão por zero e peso igual por linha) |
| Lags e calendário | ✅ (4 colunas, não um total) |
| Vazamento | ⚠️ Definição perfeita; citou o vazamento aceito (clima) em vez do evitado pelo ADR 0021 (lags da hora-alvo) |
| Gradient boosting | ✅ |
| Walk-forward | ✅ |
| Versionamento | ⚠️ Faltou o "por que piorou" (dado, código ou parâmetros) |
| Append | ✅ |
| `dim_execucao` / `Execucao Alvo` | ⚠️ Faltou o problema: somar execuções duplica |
| `VAR fim` antes do filtro | ❌ Deu vantagens (legibilidade, reuso); o motivo era obrigatório (medida não entra no filtro do `CALCULATE`) |
| `REMOVEFILTERS(dim_mes)` | ⚠️ Direção certa; faltou o efeito (interseção vazia num filtro de `ano`; substituição na própria coluna) |

### Autoavaliação (quiz)

| # | Tipo | Resultado |
|---|---|---|
| 1 | Conceitual: por que o erro cai de 12,9% para 3,9% no total do dia | ❌ Disse "granularidade mais fina" (é mais grossa) e o motivo errado (os erros se cancelam ao somar) |
| 2 | Conceitual: baseline × Labor Day | ⚠️ Baseline certo; faltou o que o modelo tem (calendário e feriados anteriores no treino) |
| 3 | Aplicada: a DAG roda de novo | ⚠️ Três execuções e a nova como padrão (desempate) certos; achou que o relatório publicado muda sozinho |
| 4 | Aplicada: L2 em vez de L1 | ⚠️ WAPE pior, certo; viés ao contrário (ele encolheria, porque a L2 mira a média) |
| 5 | Diagnóstico: o colega com WAPE de 4% | ✅ Vazamento; faltou como provar. Perguntou por que melhora "com menos lags" (são os mesmos 4, mais frescos) |

**Pergunta de entrevista:** "Como você sabe que o modelo é bom e que não está otimista demais?"
- ✅ Abriu com evidência medida ("vence em 100% das rodadas").
- Desviou para o viés da L1, que é limitação e não prova, e disse "sempre menor" (o viés é na soma). Faltaram
  régua antes do modelo, walk-forward, vazamento com prova e o vazamento aceito, reprodutibilidade. Resposta-modelo
  entregue.

**Mini-checagem:**

| Item | Resultado |
|---|---|
| M1: erros +30, −20, −10 zona a zona × total | ✅ |
| M2: o que precisa acontecer para o link público mudar | ✅ (completada a cadeia: ingestão → dbt → DAG → atualizar → republicar) |
| M3: chute da L1 e da L2, e o viés | ✅ |
| M4: por que a `VAR` é obrigatória | ✅ |
| M5: o MAPE com zero corridas | ✅ (com a frase do Claude, palavra por palavra) |

**Resultado:** ✅ Passou. Os quatro pontos errados na primeira rodada foram acertados na mini-checagem.

**Reforços para as próximas fases:**
1. **Responder o que foi perguntado, com o "no nosso projeto":** qual é o nosso baseline, qual vazamento o ADR
   evitou, que problema a peça resolve.
2. **Separar vantagem de motivo:** a `VAR` é legível (vantagem) e foi obrigatória (motivo); o append guarda
   histórico (vantagem) porque a previsão não se reconstrói (motivo).
3. **O que não atualiza sozinho** (pela segunda fase seguida): a cadeia ingestão → dbt → DAG → atualizar →
   republicar.
4. **Limitação dita por você, mas como complemento da prova**, e sem o "sempre".
5. **Manter o fechamento com evidência medida**, que apareceu de novo.

---

## 6. Pendências e melhorias anotadas

- **Confirmar no Athena** (no Mac): o realizado do backtest oficial é **126.277.028** (Power BI, soma exata de
  inteiros) e não 126.277.020 (guia). Hipótese não verificada: a soma de um `REAL` de 32 bits exibida como
  `1.2627702E8`. Consulta: `sum(cast(qtd_corridas_real as double))`. Não muda decisão; corrigir o número no guia e na
  validação.
- **Republicar no Power BI Service** depois de cada mudança do relatório (o link público é uma foto).
- **Intervalos de previsão** (regressão quantílica): fora desta versão (D4).
- **Clima previsto em vez de observado**, para tirar o vazamento aceito, se a previsão um dia for operacional.
- **Vídeo do README:** o da Fase 4 ficou, com aviso; o limite de 10 MB do GitHub barrou a gravação nova.
- **Versão em inglês do relatório:** backlog da Fase 7 (da Fase 4).
- **Layout mobile:** considerado e descartado pelo Ronald (o gerador teria de escrever o `mobile.json`).
