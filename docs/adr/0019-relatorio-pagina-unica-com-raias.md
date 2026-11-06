# ADR 0019: Relatório do Power BI em página única com raias

- **Status:** Decidido na Fase 4 (antes do passo 8)
- **Data:** 05/11/2026
- **Fase:** 4
- **Relacionado:** spec Seção 10 (substitui a lista de 5 páginas), D3 (página 5 vira Uber × Lyft), D4 (HTML Content), ADR 0011 (PBIP)

## Contexto

A Seção 10 da spec previa 5 páginas no formato padrão do Power BI (16:9): visão executiva, oferta × demanda, economia unitária, taxa de congestionamento e Uber × Lyft.

O critério de pronto da Fase 4 é "cada pergunta de negócio tem uma resposta visível e um insight escrito". Em 5 abas separadas, a história fica fragmentada: o leitor precisa clicar em cada uma e montar sozinho a conclusão.

O Ronald trouxe um relatório real que usa outro formato: página única de **1440 × 3770**, em **tamanho real com rolagem vertical**, dividida em **raias** com título próprio (cabeçalho → abertura com a mensagem principal → raias). O mesmo relatório tem **932 interações entre visuais editadas**, o custo de manter filtros de uma raia longe das outras.

## Decisão

O relatório é **uma página única, 1440 de largura, rolagem vertical, uma raia por pergunta de negócio**:

| Raia | Conteúdo |
|---|---|
| 0. Cabeçalho e resumo | Título, segmentação de mês, KPIs e as 4 respostas em uma linha cada (o índice do relatório) |
| 1. Onde e quando falta oferta? | Mapa do P90 por zona, matriz hora × tipo de dia, distribuição da espera com linha do P90, aviso "P90 acima de 15 min é aproximado" (D11) |
| 2. Como evolui a economia unitária? | Take rate, receita por milha e por minuto, repasse por hora, % tarifa inválida |
| 3. Qual foi o impacto da taxa do CBD? | Antes × depois, CBD × não-CBD, origem das corridas que entram no centro |
| 4. Uber × Lyft: onde estamos perdendo terreno? | Share por zona e evolução (D3) |

- **Estrutura de cada raia:** a pergunta como título → a resposta numa frase (insight) → os visuais como evidência → nota de método.
- **Páginas ocultas** de dica de ferramenta (tooltip) continuam permitidas.
- **Altura:** estimada entre 4.500 e 5.000 px. O limite máximo de altura de página personalizada não foi verificado em fonte oficial; o exemplo prova 3.770.

### Regras para conter o custo das interações

1. **Uma segmentação global só:** o mês, no cabeçalho. Ela deve filtrar tudo.
2. **Filtro específico de uma raia vira filtro no visual**, não segmentação solta na página.
3. **Segmentação que precisar ficar dentro de uma raia** (ex.: hora do dia e tipo de dia da `dim_periodo_espera`, que alcançam a demanda pela cadeia de relacionamentos) tem as interações restritas à própria raia, e isso fica documentado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| 5 páginas 16:9 (a spec original) | História fragmentada em abas; o resumo executivo fica longe das evidências |
| Página única sem raias definidas | Rolagem longa sem estrutura: o leitor se perde |
| Navegação por indicadores (bookmarks) entre seções | Um botão não rola a página até uma raia (comportamento nativo não verificado); a raia 0 cumpre o papel de índice |

## Consequências

- **Ganhamos:** leitura em sequência, como uma apresentação executiva; insight escrito ao lado de cada evidência; um vídeo de rolagem mostra o relatório inteiro no portfólio.
- **Perdemos ou passamos a cuidar de:**
  - **Interações:** toda segmentação filtra a página inteira por padrão. As regras acima existem para não chegar às centenas de interações editadas do exemplo.
  - **Carga:** os ~40 visuais carregam juntos. Com Import deve ser tranquilo; conferir no Analisador de Desempenho.
  - **Revisão no Git:** as interações ficam todas no `page.json` da única página, e o diff desse arquivo cresce.
  - **Celular:** a página não foi pensada para o layout de celular (fora do escopo da v1).
- **O passo 4 não muda:** o mapa ocupa uma raia em vez de uma página; o TopoJSON é o mesmo.
