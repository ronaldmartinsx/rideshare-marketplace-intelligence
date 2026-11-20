# ADR 0023: Textos do relatório gerados por medida, com períodos por regra

- **Status:** Decidido e aplicado na Fase 5 (20/11/2026), depois da raia 5 (passo 8)
- **Data:** 20/11/2026
- **Fase:** 5
- **Relacionado:** ADR 0019 (página única com raias), `_brief/report-spec.md` (revisão 4 da Fase 4 e revisão 6),
  `powerbi/gerador/gerar_pagina.js`, guia `docs/guias/fase-5-continuar-no-windows.md`
- **Reverte:** a decisão da revisão 4 da Fase 4 ("o texto é fixo; o período fica explícito")

## Contexto

Até a revisão 5, as respostas do cabeçalho, as aberturas das raias e os subtítulos dos gráficos eram texto escrito
no gerador: "P90 de 8,1 para 10,1 min", "Só Manhattan reduziu: −10%", "Leitura com dados até set/2026". A revisão 4
escolheu isso de propósito e deixou o período explícito para o leitor saber de quando era a leitura.

O pedido do Ronald (20/11/2026): **nenhum texto chumbado**. A TLC publica um mês novo por mês e o modelo de ML
ganha execuções novas; texto fixo fica errado em silêncio, e ninguém deveria precisar lembrar de reescrevê-lo.

O problema tem duas camadas. **Número dinâmico é fácil**: vira medida. **Afirmação dinâmica não é**: "puxado pela
Uber" ou "a queda veio do resto de Manhattan" podem deixar de ser verdade, e um número certo ao lado de uma frase
errada é pior que um texto fixo. Além disso, várias comparações usavam períodos que só fazem sentido numa data
(2024 × jan–set/2026), que nem são comparáveis entre si.

## Decisão

Todo texto do relatório com número, mês ou afirmação sobre os dados sai de **medida DAX**. Os quatro princípios,
aprovados pelo Ronald:

| # | Princípio | Regra |
|---|---|---|
| 1 | **Período por regra** | Respostas comparam os **últimos 12 meses com os 12 anteriores**, ancorados em `[Mes Fim Dados]` (o último mês com corridas). Exceção: a raia 3 fica **ancorada no evento** (12 meses antes × 12 depois de `[Data Taxa CBD]`, por dia) |
| 2 | **Afirmação com regra** | O sujeito e o verbo são calculados: quem lidera, o sentido, o maior. Cada "estável" tem um limiar (±0,3 min no P90, ±1% na receita, ±1 pp no take rate, ±0,5 pp no share). Onde não há regra que sustente a frase ("periferia", "hipótese da Lyft em 2025"), a frase sai |
| 3 | **Quem segue o filtro** | Respostas e aberturas são "a resposta": ignoram o filtro de período e os cliques (a 5 segue só a execução escolhida). Subtítulos descrevem o gráfico que está na tela: seguem o filtro |
| 4 | **Fato de método pode ficar fixo** | Definições e fatos do mundo (a data da taxa, "fica fora das métricas de economia", o atraso de ~2 meses da TLC) ficam fixos, num lugar só |

E uma consequência sobre a raia 5: a **execução padrão** também passou a ser regra (`dim_execucao[is_padrao]`: a de
mais janelas de backtest; no empate, a mais recente). A segmentação perdeu a pré-seleção fixa; sem seleção, a
medida `[Execucao Alvo]` usa a padrão, e as medidas de base filtram sempre por ela, então somar execuções ficou
impossível, não só bloqueado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Manter texto fixo com o período explícito** (revisão 4) | É o problema: fica errado sem avisar. O teste mostrou isso: filtrando 2024, o mapa diria "Manhattan, menos", e era o Brooklyn |
| **Narrativa inteligente (Smart Narrative) do Power BI** | Gera texto, mas sem as regras do negócio (o que é "estável", quem "puxou") e sem controle de formato em pt-BR |
| **Comparar o primeiro ano com o último** (2024 × últimos 12 meses) | Distância cresce sozinha a cada mês e mistura tendência de longo prazo com a do último ano. Na raia 4 ela escondia que a Lyft recua em Manhattan no último ano |
| **Subtítulos ignorando o filtro, como as respostas** | O subtítulo descreve o gráfico na tela; se o leitor filtra 2024, o subtítulo tem de falar de 2024 |
| **Grupos de cálculo para as janelas** (um item "12 meses", outro "anteriores") | Exigem desligar as agregações implícitas do modelo; uma medida por métrica e janela é mais simples de ler |

## Consequências

- **Os números das frases mudaram**, porque a régua mudou: P90 8,5 → 9,8 min (antes 8,1 → 10,1), receita por milha
  +5,7% (antes +9%), share da Lyft 26,9% → 27,7% (antes 25,2% → 27,7%).
- **Uma leitura mudou de verdade.** Na raia 4, contra o ano anterior, a Lyft perde terreno em 48 das 211 maiores
  zonas, 45 delas em Manhattan, e recua 0,9 pp em Manhattan como um todo. O texto fixo ("só 10 zonas") estava certo
  para a comparação com 2024, mas escondia a tendência do último ano.
- **Regras de borda testadas**, não supostas: singular/plural e "única janela" na raia 5 (execução de teste com
  1 janela); filtro sem antes e depois da taxa na raia 3; menos de 24 meses no filtro nas tendências (aí o
  subtítulo descreve a faixa, porque mês contra mês mede sazonalidade, não tendência).
- **~45 medidas novas** (pastas `Janelas` e `Apresentacao`). As que calculam métrica foram escritas pelo Claude, por
  autorização do Ronald nesta frente (exceção à regra ✍️ do `CLAUDE.md`, registrada no guia do Windows).
- **O gerador não escreve mais nenhum número nem mês**: respostas e aberturas são HTML de medida, e os subtítulos
  apontam para medida (`subTitle.text` → `expr.Measure`, formato conferido no Desktop numa prova de conceito).
- **Os documentos continuam sendo foto datada.** README e validação registram os números de uma data; o relatório
  é que é vivo.
- **Custo de manutenção novo:** um limiar ou uma regra de frase errada aparece no relatório inteiro. Por isso cada
  medida de texto tem a regra na descrição.
