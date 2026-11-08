# Report Spec — Rideshare em NY (Fase 4, passo 8)

> Especificação travada do relatório (página única com raias, ADR 0019). Escrita pelo Claude Code em 05/11/2026 a partir das decisões do Ronald; aguarda aprovação antes de qualquer edição no PBIR.

## Report identity
- Report name: Rideshare Marketplace Intelligence
- Semantic model: `Rideshare Marketplace Intelligence.SemanticModel` (Import da Gold no Athena)
- Audience: time de Marketplace da Lyft em Nova York (liderança; leitura de reunião executiva)
- Primary purpose: responder às 4 perguntas de negócio da spec (Seção 2.4) com uma resposta escrita e a evidência ao lado
- Delivery target: PBIP local versionado em `powerbi/` (publicação no Service fora da v1)

## Semantic model binding
- Entry mode: Local Model
- Model name: Rideshare Marketplace Intelligence
- connectionString: byPath `../Rideshare Marketplace Intelligence.SemanticModel` (já existente no `definition.pbir`)

## User decisions and constraints
- Scope: uma página única de 1440 × 4700, rolagem vertical (tamanho real), 5 raias (ADR 0019)
- Page count: 1 (a página existente `5b8ff5507780d35cb750` é reaproveitada; o Shape Map de teste é removido)
- Interactivity: uma segmentação global (mês, intervalo de datas) que filtra tudo; **clique num visual filtra só a própria raia** (interações entre raias desligadas, geradas mecanicamente); sem navegação entre páginas, sem bookmarks
- Design direction: esqueleto montado pelo Claude; refinamento de design pelo Ronald no Desktop
- Publishing: não
- Tooling: `powerbi-report-author` 0.5.0, Power BI Desktop, MCP de modelagem (leitura)
- Model edit permissions: nenhuma mudança no modelo nesta etapa. Medidas DAX novas, se surgirem, são ✍️ do Ronald
- Accessibility: paleta Okabe-Ito (segura para daltonismo), texto alternativo em todo visual, contraste WCAG AA
- Data caveats: 2026 só até setembro; P90 acima de 15 min é aproximado (D11); P90 com menos de 100 corridas no recorte não é exibido no mapa; textos de resposta descrevem o período completo e citam o recorte

## Narrative
- Core story: a cidade cresceu, a espera piorou (mais na Uber), cada corrida rende mais, a taxa do CBD tirou corridas do centro vindas do próprio Manhattan, e a Lyft ganhou share fora de Manhattan.
- Audience promise: em 40 segundos de rolagem, o time sabe onde agir (zonas e horários sem oferta, zonas de Manhattan onde perde share) e qual é o pano de fundo econômico.
- Key questions answered: (1) onde e quando falta oferta; (2) como evolui a economia unitária; (3) qual foi o impacto da taxa de congestionamento; (4) onde a Lyft perde terreno para a Uber.

## Design identity
- Tone: Briefing executivo editorial — fundo claro, muito respiro, títulos como frases-resposta, uma cor de destaque por raia
- Signature: cada raia abre com a **pergunta** (rótulo pequeno, caixa alta, cor da raia) e logo abaixo a **resposta em uma frase**, antes de qualquer gráfico
- Brownfield delta: página padrão 1920 × 1080 com um visual de teste → página única editorial com raias

## Page plan
1. Rideshare em NY — quatro respostas para o Marketplace da Lyft
   - Archetype: Narrative Story (abertura Executive Summary)
   - Layout variant: A — raias empilhadas de largura total; cada raia com título, resposta e 3 a 5 visuais
   - Purpose: contar a história das 4 perguntas em sequência
   - Visuals: 6 cartões de KPI, 4 respostas-resumo, 3 mapas de formas, 1 matriz de calor, 8 gráficos de linha/barra, 1 tabela, notas
   - Fields/measures: só medidas e colunas existentes (lista abaixo)
   - Slicers/interactions: `dim_mes[mes_inicio]` (intervalo) global; cliques filtram só dentro da raia

## Respostas escritas (textos que entram nos títulos de raia)

Período completo (jan/2024–set/2026), salvo indicação. Números conferidos no modelo em 05/11/2026.

| Raia | Pergunta | Resposta (frase de abertura) |
|---|---|---|
| 1 | Onde e quando falta oferta? | A espera piorou: o P90 da cidade subiu de 8,1 min (2024) para 10,1 min (jan–set/2026), puxado pela Uber (7,8 → 10,7 min); a Lyft ficou estável em ~8,8. Falta oferta na periferia (Breezy Point, City Island, Flushing Meadows: 18 a 21 min) e nas madrugadas de fim de semana e feriado (4h: ~13 min). |
| 2 | Como evolui a economia unitária? | Cada corrida rende mais: receita por milha +9% (US$ 5,16 → 5,65) e repasse por hora de corrida +7% (US$ 60 → 64) de 2024 a 2026, com take rate estável em ~23%. A exceção é a Lyft, cujo take rate caiu para 20,9% em 2025 (no mesmo ano em que ganhou share; hipótese, não causalidade provada) e voltou a 23,9% em 2026. |
| 3 | Qual foi o impacto da taxa de congestionamento? | Nos 12 meses depois de 05/01/2025, as corridas com destino no CBD caíram 5,1% (153 mil → 145 mil por dia) enquanto o total da cidade subiu 1,9%; a fatia do CBD foi de 23,4% para 21,8%. A queda veio do resto de Manhattan (−10% nas corridas que entram no CBD); Brooklyn e Queens ficaram estáveis. |
| 4 | Onde a Lyft perde terreno para a Uber? | A Lyft subiu de 25,2% (2024) para 27,7% de share (últimos 12 meses), puxada pelo Bronx (+7 p.p. em Bedford Park, Belmont e Norwood). Perde terreno em só 10 das 179 maiores zonas, todas em Manhattan (Yorkville, Manhattan Valley, Lower East Side), em até −1,7 p.p. |

## Design system summary
- Theme: `base.json` da skill adaptado; fundo da página `#F7F7F5`, visuais em cartão branco sem borda pesada
- Color semantics (Okabe-Ito): espera/P90 `#D55E00`; economia `#0072B2` (repasse `#56B4E9`); CBD `#009E73`; Lyft `#CC79A7`; Uber `#4D4D4D`
- Typography: Segoe UI Semibold nos títulos e respostas; Segoe UI no corpo; números tabulares
- Layout: 12 colunas × 46 linhas (100 px), margem 48, gutter 24, snap 8; largura útil 1344
- Accessibility: texto alternativo em todos os visuais; nenhuma informação só por cor (rótulos e dicas de ferramenta)

## Model requirements
- Existing measures: Corridas; Take rate; Receita por milha; Receita por minuto; Repasse por hora de corrida; % tarifa invalida; Espera P90 (min); Corridas com espera valida; Share da operadora; % destino no CBD; Corridas entrando no CBD
- New measures: nenhuma
- New calculated columns: nenhuma
- Filtros no nível do visual (sem DAX): mapa do P90 com `Corridas com espera valida >= 100`; ranking de zonas com `>= 1000` e `dim_zona[zona_id] <= 263`; Lyft = `dim_operadora[operadora_id] = "HV0005"`; operadoras ativas = HV0003 e HV0005

## Canonical design contract

```yaml
Design Brief:
  generated_by: powerbi-report-cli
  contract_version: 1
  mode: brownfield
  design_identity:
    tone: "Briefing executivo editorial: fundo claro #F7F7F5, cartões brancos, títulos como frases-resposta, uma cor de destaque por raia, densidade média"
    signature: "Cada raia abre com a pergunta (rótulo pequeno em caixa alta na cor da raia) seguida da resposta em uma frase grande, antes dos gráficos"
    current_tone: indistinct
    current_signature: none
  archetype: Narrative
  navigation_model: none
  color_map:
    - measure: fct_espera_histograma[Espera P90 (min)]
      color: "#D55E00"
      tint: "#FBE3D3"
    - measure: fct_demanda_zona_hora[Take rate]
      color: "#0072B2"
      tint: "#D9EAF5"
    - measure: fct_demanda_zona_hora[Receita por milha]
      color: "#0072B2"
      tint: "#D9EAF5"
    - measure: fct_demanda_zona_hora[Receita por minuto]
      color: "#0072B2"
      tint: "#D9EAF5"
    - measure: fct_demanda_zona_hora[Repasse por hora de corrida]
      color: "#56B4E9"
      tint: "#E3F2FB"
    - measure: fct_demanda_zona_hora[% destino no CBD]
      color: "#009E73"
      tint: "#D6F0E8"
    - measure: fct_od_mensal[Corridas entrando no CBD]
      color: "#009E73"
      tint: "#D6F0E8"
    - measure: fct_demanda_zona_hora[Share da operadora]
      color: "#CC79A7"
      tint: "#F3E1EC"
    - measure: fct_demanda_zona_hora[Corridas]
      color: "#4D4D4D"
      tint: "#E6E6E6"
    - measure: fct_demanda_zona_hora[% tarifa invalida]
      color: "#4D4D4D"
      tint: "#E6E6E6"
  semantic_colors:
    operadora:
      Lyft: "#CC79A7"
      Uber: "#4D4D4D"
  pages:
    - name: "Rideshare em NY — quatro respostas para o Marketplace da Lyft"
      role: landing
      archetype: Narrative
      layout_variant: A
      variant_rationale: "Quatro perguntas independentes com evidências próprias pedem raias empilhadas de largura total, lidas em sequência (ADR 0019)."
      navigation: []
      page_background: "#F7F7F5"
      display_option: ActualSize
      layout_summary: "Cabeçalho com título e filtro de meses; abertura com 6 KPIs e as 4 respostas-resumo; raias 1 a 4 com pergunta, resposta e evidências; rodapé com fonte e método."
      layout_contract:
        canvas:
          width: 1440
          height: 4700
          margin: 48
          gutter: 24
          snap: 8
        grid:
          columns: 12
          rows: 46
          regions:
            header:          [1,  1,  9,  2]
            filters:         [9,  1, 13,  2]
            kpis:            [1,  2, 13,  4]
            answers:         [1,  4, 13,  7]
            l1_question:     [1,  7, 13,  8]
            l1_answer:       [1,  8, 13,  9]
            l1_map:          [1,  9,  7, 16]
            l1_heatmap:      [7,  9, 10, 16]
            l1_ranking:      [10, 9, 13, 16]
            l1_note:         [1, 16, 13, 17]
            l2_question:     [1, 17, 13, 18]
            l2_answer:       [1, 18, 13, 19]
            l2_take:         [1, 19,  7, 23]
            l2_receita:      [7, 19, 13, 23]
            l2_repasse:      [1, 23,  7, 26]
            l2_receita_min:  [7, 23, 10, 26]
            l2_qualidade:    [10, 23, 13, 26]
            l3_question:     [1, 26, 13, 27]
            l3_answer:       [1, 27, 13, 28]
            l3_map:          [1, 28,  6, 36]
            l3_trend:        [6, 28, 13, 32]
            l3_origem:       [6, 32, 13, 36]
            l4_question:     [1, 36, 13, 37]
            l4_answer:       [1, 37, 13, 38]
            l4_map:          [1, 38,  7, 46]
            l4_trend:        [7, 38, 13, 42]
            l4_table:        [7, 42, 13, 46]
            footer:          [1, 46, 13, 47]
        placements:
          - id: page_title
            region: header
            kind: textbox
            text: "Rideshare em NY, jan/2024–set/2026: quatro respostas para o time de Marketplace da Lyft"
            purpose: "Dizer do que trata a página e o recorte antes de qualquer número."
          - id: month_slicer
            region: filters
            kind: slicer
            field_bindings: dim_mes[mes_inicio]
            slicer_type: between
            insight_basis: "A história é mensal (antes × depois de 05/01/2025, tendência de 33 meses); o leitor recorta o período."
          - id: kpi_corridas
            region: kpis
            kind: cardVisual
            purpose: "Qual é o volume de corridas no período?"
            field_bindings: fct_demanda_zona_hora[Corridas]
            color_strategy: measure_match
            slot: 1
            of: 6
          - id: kpi_p90
            region: kpis
            kind: cardVisual
            purpose: "Quanto esperam os 10% mais azarados?"
            field_bindings: fct_espera_histograma[Espera P90 (min)]
            color_strategy: measure_match
            slot: 2
            of: 6
          - id: kpi_take_rate
            region: kpis
            kind: cardVisual
            purpose: "Quanto da tarifa fica com as operadoras?"
            field_bindings: fct_demanda_zona_hora[Take rate]
            color_strategy: measure_match
            slot: 3
            of: 6
          - id: kpi_receita_milha
            region: kpis
            kind: cardVisual
            purpose: "Quanto rende cada milha?"
            field_bindings: fct_demanda_zona_hora[Receita por milha]
            color_strategy: measure_match
            slot: 4
            of: 6
          - id: kpi_destino_cbd
            region: kpis
            kind: cardVisual
            purpose: "Que fatia das corridas termina no CBD?"
            field_bindings: fct_demanda_zona_hora[% destino no CBD]
            color_strategy: measure_match
            slot: 5
            of: 6
          - id: kpi_share_lyft
            region: kpis
            kind: cardVisual
            purpose: "Qual é o share da Lyft?"
            field_bindings: fct_demanda_zona_hora[Share da operadora]
            visual_filters: ["dim_operadora[operadora_id] = HV0005"]
            color_strategy: measure_match
            slot: 6
            of: 6
          - id: answer_oferta
            region: answers
            kind: textbox
            text: "1 · OFERTA — A espera piorou: P90 de 8,1 para 10,1 min, puxado pela Uber; falta oferta na periferia e nas madrugadas de fim de semana."
            insight_basis: "Resumo da raia 1 (variação anual do P90 e piores zonas/horários)."
            slot: 1
            of: 4
          - id: answer_economia
            region: answers
            kind: textbox
            text: "2 · ECONOMIA — Cada corrida rende mais: receita por milha +9% e repasse por hora +7%, com take rate estável em ~23%."
            insight_basis: "Resumo da raia 2 (variação 2024 → 2026)."
            slot: 2
            of: 4
          - id: answer_cbd
            region: answers
            kind: textbox
            text: "3 · TAXA DO CBD — Corridas para o centro −5,1% enquanto a cidade cresceu 1,9%; a queda veio do resto de Manhattan."
            insight_basis: "Resumo da raia 3 (12 meses antes × depois de 05/01/2025)."
            slot: 3
            of: 4
          - id: answer_share
            region: answers
            kind: textbox
            text: "4 · UBER × LYFT — Share da Lyft de 25,2% para 27,7%, puxado pelo Bronx; perde terreno só em 10 zonas de Manhattan."
            insight_basis: "Resumo da raia 4 (share 2024 × últimos 12 meses, zonas com 500 mil+ corridas)."
            slot: 4
            of: 4
          - id: l1_question_text
            region: l1_question
            kind: textbox
            text: "1 · ONDE E QUANDO FALTA OFERTA?"
            purpose: "Abrir a raia com a pergunta de negócio."
          - id: l1_answer_text
            region: l1_answer
            kind: textbox
            text: "A espera piorou: o P90 da cidade subiu de 8,1 min (2024) para 10,1 min (jan–set/2026), puxado pela Uber (7,8 → 10,7 min); a Lyft ficou estável em ~8,8. Falta oferta na periferia (Breezy Point, City Island, Flushing Meadows: 18 a 21 min) e nas madrugadas de fim de semana e feriado (4h: ~13 min)."
            insight_basis: "P90 por ano e por operadora; top zonas com 1.000+ corridas; matriz hora × tipo de dia (últimos 12 meses)."
          - id: l1_map_p90
            region: l1_map
            kind: shapeMap
            purpose: "Em que zonas os 10% mais lentos esperam mais?"
            field_bindings: { Location: dim_zona[zona_id], ColorSaturation: fct_espera_histograma[Espera P90 (min)], Tooltips: [dim_zona[zona], dim_zona[borough], fct_espera_histograma[Corridas com espera valida]] }
            custom_map: powerbi/mapas/zonas_tlc.json (key LocationID)
            visual_filters: ["fct_espera_histograma[Corridas com espera valida] >= 100"]
            color_strategy: gradient
            color_scale: { min: 6, max: 15, min_color: "#FBE3D3", max_color: "#D55E00", note: "acima de 15 na cor máxima; zonas sem amostra mínima ficam sem cor" }
          - id: l1_heatmap_hora
            region: l1_heatmap
            kind: pivotTable
            purpose: "Em que hora e tipo de dia a espera é pior?"
            field_bindings: { Rows: dim_periodo_espera[hora_do_dia], Columns: dim_periodo_espera[tipo_dia], Values: fct_espera_histograma[Espera P90 (min)] }
            sort_policy: natural_order
            color_strategy: gradient
            conditional_format: { background: gradient, min_color: "#FFFFFF", max_color: "#D55E00", field: fct_espera_histograma[Espera P90 (min)] }
          - id: l1_ranking_zonas
            region: l1_ranking
            kind: barChart
            purpose: "Quais zonas com volume relevante têm a pior espera?"
            field_bindings: { Category: dim_zona[zona], Y: fct_espera_histograma[Espera P90 (min)] }
            visual_filters: ["Top 15 dim_zona[zona] por Espera P90 (min)", "fct_espera_histograma[Corridas com espera valida] >= 1000", "dim_zona[zona_id] <= 263"]
            sort_policy: value_desc
            color_strategy: measure_match
          - id: l1_note_text
            region: l1_note
            kind: textbox
            text: "Método: P90 = 90% das corridas esperaram até este valor (pedido → embarque), recalculado do histograma de faixas (ADR 0006). Acima de 15 min é aproximado (erro de até ~1 min). Zonas com menos de 100 corridas no recorte ficam sem cor."
            purpose: "Nota de método e limites do P90 (D11 e amostra mínima)."
          - id: l2_question_text
            region: l2_question
            kind: textbox
            text: "2 · COMO EVOLUI A ECONOMIA UNITÁRIA?"
            purpose: "Abrir a raia com a pergunta de negócio."
          - id: l2_answer_text
            region: l2_answer
            kind: textbox
            text: "Cada corrida rende mais: receita por milha +9% (US$ 5,16 → 5,65) e repasse por hora de corrida +7% (US$ 60 → 64) de 2024 a 2026, com take rate estável em ~23%. A exceção é a Lyft: take rate de 20,9% em 2025, no mesmo ano em que ganhou share (hipótese, não causalidade provada), e 23,9% em 2026."
            insight_basis: "Variação 2024 → 2026 (jan–set) das medidas de economia, por operadora."
          - id: l2_take_trend
            region: l2_take
            kind: lineChart
            purpose: "Como o take rate de cada operadora evoluiu mês a mês?"
            field_bindings: { Category: dim_mes[mes_inicio], Y: fct_demanda_zona_hora[Take rate], Series: dim_operadora[operadora] }
            visual_filters: ["dim_operadora[operadora_id] in (HV0003, HV0005)"]
            color_strategy: semantic
          - id: l2_receita_trend
            region: l2_receita
            kind: lineChart
            purpose: "Como a receita por milha evoluiu mês a mês?"
            field_bindings: { Category: dim_mes[mes_inicio], Y: fct_demanda_zona_hora[Receita por milha] }
            color_strategy: measure_match
          - id: l2_repasse_trend
            region: l2_repasse
            kind: lineChart
            purpose: "Como o repasse por hora de corrida evoluiu mês a mês?"
            field_bindings: { Category: dim_mes[mes_inicio], Y: fct_demanda_zona_hora[Repasse por hora de corrida] }
            color_strategy: measure_match
          - id: l2_receita_min_ano
            region: l2_receita_min
            kind: columnChart
            purpose: "Quanto rende cada minuto de corrida, ano a ano?"
            field_bindings: { Category: dim_mes[ano], Y: fct_demanda_zona_hora[Receita por minuto] }
            sort_policy: category_asc
            color_strategy: measure_match
          - id: l2_qualidade_card
            region: l2_qualidade
            kind: cardVisual
            purpose: "Que parcela das corridas ficou fora das métricas de economia?"
            field_bindings: fct_demanda_zona_hora[% tarifa invalida]
            callout_value_basis: "Parcela com tarifa ≤ 0 excluída das médias econômicas (passo 1); não aparece em nenhum gráfico vizinho."
            color_strategy: measure_match
          - id: l3_question_text
            region: l3_question
            kind: textbox
            text: "3 · QUAL FOI O IMPACTO DA TAXA DE CONGESTIONAMENTO?"
            purpose: "Abrir a raia com a pergunta de negócio."
          - id: l3_answer_text
            region: l3_answer
            kind: textbox
            text: "Nos 12 meses depois de 05/01/2025, as corridas com destino no CBD caíram 5,1% (153 mil → 145 mil por dia) enquanto o total da cidade subiu 1,9%; a fatia do CBD foi de 23,4% para 21,8%. A queda veio do resto de Manhattan (−10% nas corridas que entram no CBD); Brooklyn e Queens ficaram estáveis."
            insight_basis: "12 meses antes × 12 meses depois do corte diário; origem por distrito em fev–dez de 2024 × 2025."
          - id: l3_map_origem
            region: l3_map
            kind: shapeMap
            purpose: "De onde vêm as corridas que entram no CBD?"
            field_bindings: { Location: dim_zona[zona_id], ColorSaturation: fct_od_mensal[Corridas entrando no CBD], Tooltips: [dim_zona[zona], dim_zona[borough]] }
            custom_map: powerbi/mapas/zonas_tlc.json (key LocationID)
            color_strategy: gradient
          - id: l3_pct_trend
            region: l3_trend
            kind: lineChart
            purpose: "A fatia das corridas que termina no CBD mudou depois de 05/01/2025?"
            field_bindings: { Category: dim_mes[mes_inicio], Y: fct_demanda_zona_hora[% destino no CBD] }
            comparison_basis: "Antes × depois de 05/01/2025 (jan/2025 é mês de transição)"
            color_strategy: measure_match
          - id: l3_origem_trend
            region: l3_origem
            kind: lineChart
            purpose: "Quais distritos de origem reduziram as corridas para o CBD?"
            field_bindings: { Category: dim_mes[mes_inicio], Y: fct_od_mensal[Corridas entrando no CBD], Series: dim_zona[borough] }
            visual_filters: ["dim_zona[borough] in (Manhattan, Brooklyn, Queens, Bronx)"]
            color_strategy: unique
          - id: l4_question_text
            region: l4_question
            kind: textbox
            text: "4 · ONDE A LYFT PERDE TERRENO PARA A UBER?"
            purpose: "Abrir a raia com a pergunta de negócio."
          - id: l4_answer_text
            region: l4_answer
            kind: textbox
            text: "A Lyft subiu de 25,2% (2024) para 27,7% de share (últimos 12 meses), puxada pelo Bronx (+7 p.p. em Bedford Park, Belmont e Norwood). Perde terreno em só 10 das 179 maiores zonas, todas em Manhattan (Yorkville, Manhattan Valley, Lower East Side), em até −1,7 p.p."
            insight_basis: "Share 2024 × out/2025–set/2026 por zona, zonas com 500 mil+ corridas no período recente."
          - id: l4_map_share
            region: l4_map
            kind: shapeMap
            purpose: "Em que zonas o share da Lyft é maior ou menor?"
            field_bindings: { Location: dim_zona[zona_id], ColorSaturation: fct_demanda_zona_hora[Share da operadora], Tooltips: [dim_zona[zona], dim_zona[borough], fct_demanda_zona_hora[Corridas]] }
            custom_map: powerbi/mapas/zonas_tlc.json (key LocationID)
            visual_filters: ["dim_operadora[operadora_id] = HV0005"]
            color_strategy: gradient
            color_scale: { min: 0.15, max: 0.40, min_color: "#F3E1EC", max_color: "#CC79A7" }
          - id: l4_share_trend
            region: l4_trend
            kind: lineChart
            purpose: "Como o share de Uber e Lyft evoluiu mês a mês?"
            field_bindings: { Category: dim_mes[mes_inicio], Y: fct_demanda_zona_hora[Share da operadora], Series: dim_operadora[operadora] }
            visual_filters: ["dim_operadora[operadora_id] in (HV0003, HV0005)"]
            color_strategy: semantic
          - id: l4_table_zonas
            region: l4_table
            kind: tableEx
            purpose: "Nas 20 zonas com mais corridas da Lyft, qual é o share dela?"
            field_bindings: [dim_zona[zona], dim_zona[borough], fct_demanda_zona_hora[Corridas], fct_demanda_zona_hora[Share da operadora]]
            visual_filters: ["dim_operadora[operadora_id] = HV0005", "Top 20 dim_zona[zona] por Corridas"]
            column_labels: { "Corridas": "Corridas da Lyft", "Share da operadora": "Share da Lyft" }
            sort_policy: value_desc
          - id: footer_text
            region: footer
            kind: textbox
            text: "Fonte: NYC TLC, High Volume FHV Trip Records (jan/2024–set/2026), via pipeline AWS (S3, Glue, Athena/Iceberg, dbt). Métricas definidas na spec (Seção 2.5) e reconciliadas com o Athena (docs/validacao/fase-4.md). Textos de resposta descrevem o período completo; os gráficos seguem o filtro de meses."
            purpose: "Fonte, método e aviso sobre textos estáticos."
        space_audit:
          content_cell_count: 540
          placed_cell_count: 540
          empty_cell_pct: 0
          unplaced_regions: []
          largest_region:
            name: l4_map
            pct_of_content: 9
          balance_rationale: "Cada raia ocupa 9 a 10 linhas de 100 px: pergunta e resposta (2 linhas) e evidências. Os mapas são os maiores blocos de cada raia porque a pergunta é geográfica; os gráficos de apoio têm no mínimo 3 colunas × 3 linhas. Nenhuma faixa vazia: o respiro vem dos gutters de 24 px."
  interaction_pattern:
    drill_targets: []
    cross_filter_rules: "month_slicer → todos (Filter). Entre visuais da mesma raia: padrão do Power BI. Entre raias diferentes: None (interações desligadas, geradas mecanicamente). Abertura (kpis/answers) não filtra nem é filtrada por cliques das raias."
  accessibility:
    alt_text_strategy: "headline+trend: cada visual recebe texto alternativo com a pergunta e a leitura principal"
    contrast_notes: "Textos sobre #F7F7F5 e branco em #1F1F1F/#4D4D4D (AA). Cores Okabe-Ito nunca são a única pista: séries rotuladas e dicas de ferramenta com valores."
  theme:
    base: "references/design/assets/base.json adaptado (fundo #F7F7F5, paleta Okabe-Ito)"
    user_overrides: "Nenhum tema anterior a preservar (relatório começou com o tema padrão Fluent 2)."
```

## Revisões durante a construção (05/11/2026)

Aprovado o contrato acima, a construção e as capturas de tela mudaram estes pontos. O PBIR em `powerbi/` reflete esta lista.

| # | Mudança | Motivo (evidência) |
|---|---|---|
| 1 | Altura 4700 → **4600**, grade de **45** linhas; respostas-resumo com 2 linhas; pergunta e resposta de cada raia numa **caixa de texto só** (1 linha), com a linha liberada indo para os visuais | 1ª captura: 2/3 das caixas de resposta vazias e ~100 px entre pergunta e resposta |
| 2 | Cabeçalho mais largo (colunas 1–9), título de uma linha a 20 px; filtro nas colunas 10–12 | 1ª captura: título em duas linhas cortava o subtítulo e abria barra de rolagem |
| 3 | Raia 1: mapa nas colunas 1–5, **matriz de calor nas colunas 6–9** (mais larga), ranking nas 10–12 | Coluna "util" cortada e horas 20–23 fora da matriz |
| 4 | Ranking da raia 1: "top 15 por P90" → **"zonas com P90 de 12 min ou mais"** (filtro de medida) | O CLI avisa que o filtro TopN não pode ordenar por medida (erro no Desktop) |
| 5 | KPIs: **um cartão multivalor** com 5 medidas + um cartão separado para o share da Lyft | Regra do CLI (cartões relacionados num visual só); o share precisa do filtro da Lyft, que não pode valer para os outros |
| 6 | Mapas: **sem escala fixa de cor** no arquivo; gradiente no formato que o Desktop grava (paradas com `expr`) | O formato sem `expr`, exigido pelo validador (`PBIR_FILLRULE_STOP_DOUBLE_WRAP`), deixou os 3 mapas em branco; o formato nativo renderiza. Escala fixa (6–15 min; 15%–40%) fica para o Desktop |
| 7 | Dica de ferramenta dos mapas só com medidas | O papel `Tooltips` do `shapeMap` só aceita medidas |
| 8 | Subtítulo automático ("X by Y") desligado nos visuais | Ruído visual na 2ª captura |

Erros do validador que permanecem, conscientemente: `PBIR_JSON_FILE_NO_SCHEMA` no `.pbip` e no `definition.pbir` (arquivos do Desktop; só importam para publicar no Fabric) e `PBIR_FILLRULE_STOP_DOUBLE_WRAP` nos 3 mapas (item 6). Evidência da página inteira: `docs/validacao/img/fase-4-pagina-esqueleto.png`.

## Revisão 3: refinamentos do Ronald (05/11/2026)

Pedidos do Ronald depois do esqueleto e como foram atendidos. O PBIR em `powerbi/` reflete esta lista (página 1440 × **5000**, grade de 49 linhas).

| Pedido | Solução | Evidência |
|---|---|---|
| Uma fonte só (Segoe UI) | Tema próprio `RideshareTema-3f9c2a71.json` (textClasses em Segoe UI, paleta Okabe-Ito) registrado no `report.json`; textos sem "Segoe UI Semibold" | Validação sem erro de tema |
| Subtítulo-insight em cada gráfico | 14 subtítulos estáticos (aprovados pelo Ronald), período completo | Capturas |
| Raias pouco destacadas | Faixa de abertura de borda a borda (136 px) na cor escura da raia, com o número grande, "RAIA N DE 4 · pergunta" e a resposta em branco; fundo levemente tingido atrás da raia | `docs/validacao/img/fase-4-pagina-rev3-inteira.png` |
| Título fraco; imagem; logos | Cabeçalho azul-marinho de borda a borda com título de 30 px e ilustração SVG das 263 zonas (CBD em verde) gerada do nosso TopoJSON. **Sem logos da Uber e da Lyft** (marcas registradas; decisão do Ronald) | `fase-4-pagina-rev3-topo.png` |
| Filtro "largado" | Filtro dentro do cabeçalho, rótulo "Período analisado", campos de data brancos | Idem |
| Cartões em HTML com explicação ao passar o mouse | Visual HTML Content (edição **Secure**, GUID gravado pelo Desktop do Ronald) com a medida `HTML Cartoes KPI` (**escrita pelo Claude, exceção à regra ✍️ autorizada pelo Ronald**). Explicação por CSS `:hover` (✅ testado pelo Ronald no Desktop) | Idem |
| Rodapé com LinkedIn, GitHub e portfólio | Faixa azul-marinho com a fonte e três botões (`visualLink` WebUrl) | Captura da raia 4 e rodapé |
| (achado na revisão) Cores da raia 3 | Manhattan na cor da raia, demais distritos em cinza (técnica de destaque); antes, Queens saía na cor da Lyft | `fase-4-pagina-rev3-raia3.png` |
| (achado na revisão) Escala dos mapas | Limites fixos (P90 6–15 min; share 15%–40%) no formato nativo do Desktop, que renderiza | Mapa do share com variação visível |

Pendentes desta revisão:
- **Cultura `pt-BR` do modelo:** não pode ser trocada com o cache de dados existente (o motor recusa mudar a cultura depois de criado o modelo). Caminho previsto: renomear o `cache.abf`, pôr `culture: pt-BR` no TMDL, abrir e atualizar (~500 MB no Athena). Enquanto isso, os gráficos usam o formato `en-US`; os cartões HTML já formatam em `pt-BR`.
- **Versão em inglês** do relatório: pedido do Ronald, backlog da Fase 7.

## Revisão 4: refinamentos do Ronald (07/11/2026)

Base: posições do cabeçalho ajustadas pelo Ronald no Desktop (commit `96ff690`), incorporadas ao gerador (`powerbi/gerador/gerar_pagina.js`).

| Pedido | Solução |
|---|---|
| "JAN/2024–SET/2026" fixo no título | Título em HTML com a medida `Texto Periodo Dados` (primeiro e último mês com dados, ignorando filtros); o volume de viagens do subtítulo também é dinâmico. As 4 respostas, que são leituras fixas, ganharam "Leitura com dados até set/2026" |
| Espaço ocioso à direita do cabeçalho | Ficha dos dados em HTML (`HTML Ficha Dados`): meses, zonas, viagens e último mês, dinâmicos |
| Filtro indo até dez/2026 | Filtro no próprio visual da segmentação: só meses com `Corridas > 0` (funcionou sem mexer no dbt) |
| Cartões mais explorados | Borda inteira na cor da métrica, ícone SVG por cartão, hover no tom escuro da mesma cor (contraste AA), textos sem jargão |
| Raias "carnaval de cores" | Sem preenchimento nem fundo tingido: linha de 4 px na cor da raia, número e pergunta no tom escuro, resposta em texto normal; visuais a 24 px da abertura e ~64 px até a próxima raia (na raia 1, os 64 px foram para os visuais) |
| Rodapé com "spec" | `HTML Rodape` em linguagem de negócio, com período dinâmico e a linha do projeto de portfólio |
| Formatação condicional na tabela | Barras de dados nas corridas da Lyft; gradiente de uma cor no share (20%–35%) |
| (achado na revisão) Nota de método com "ADR"/"Athena" | Reescrita em linguagem de negócio |
| Nome da zona no mapa (pedido do Ronald) | O `shapeMap` não tem rótulos (e 263 nomes fixos seriam ilegíveis): o nome e o distrito entram na dica de ferramenta dos 3 mapas pela medida de apresentação `Nome da zona`; o código da zona aparece como "Código da zona". Zoom pela roda do mouse descartado (conflita com a rolagem da página) |

Medidas de apresentação novas (regra de 07/11/2026 no CLAUDE.md: o Claude escreve as que só formatam texto/HTML): `Texto Periodo Dados`, `HTML Titulo`, `HTML Ficha Dados`, `HTML Rodape`; `HTML Cartoes KPI` reescrita. Evidências: `docs/validacao/img/fase-4-pagina-rev4-*.png`.

## Implementation notes

- Model changes: nenhuma.
- PBIR/report authoring: reaproveitar a página `5b8ff5507780d35cb750` (renomear, 1440 × 4700, `ActualSize`); remover o Shape Map de teste; gerar os visuais pelo `powerbi-report-author`, validando por lote (abertura, raia 1, 2, 3, 4).
- Tabela da raia 4: filtrada pela Lyft no visual. "Corridas" passa a ser as corridas da Lyft, e o share continua correto porque o denominador da medida remove o filtro da operadora (`REMOVEFILTERS(dim_operadora)`). Rótulos das colunas: "Corridas da Lyft" e "Share da Lyft". Mostrar o total da zona ao lado pediria uma medida nova (✍️ do Ronald), fora do esqueleto.
- Interações: a lista de interações desligadas entre raias é gerada a partir das regiões (prefixo `l1_`…`l4_`), não à mão.
- Validation: JSON e validação do CLI por lote; reabrir no Desktop; captura de tela da página inteira; conferir os números dos cartões contra os desta especificação.
- Desktop screenshot verification: página longa, conferir por trechos se a captura cortar.
- Publishing boundary: nada sai da máquina.
- Risks: (1) Shape Map pode exigir recurso de visualização (o teste funcionou); (2) limite de altura da página não verificado; (3) a escala fixa de cor do Shape Map pode não ser configurável via PBIR (então fica para o Ronald no Desktop); (4) textos estáticos podem divergir do filtro de meses (avisado no rodapé).
