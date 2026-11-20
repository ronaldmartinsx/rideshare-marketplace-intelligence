# Relatório: cinco respostas para o time de Marketplace da Lyft

Uma página única, de rolagem vertical, que responde às cinco perguntas de negócio do projeto com dados de **672 milhões de viagens** de Uber e Lyft em Nova York (jan/2024–set/2026), vindos da camada Gold do lakehouse na AWS. A quinta pergunta usa a previsão de demanda do modelo de ML da Fase 5.

**[▶ Abrir o relatório interativo no Power BI](https://app.powerbi.com/view?r=eyJrIjoiMmMwODgyYjUtNjYxOS00MjlkLTg3ZTctNGNlZTQ0MDU1ZjE1IiwidCI6IjJhNWJlYTI4LWFkNmItNDYxNi05ZjBkLWFmN2U5M2U5MDQyZCJ9)** (público, sem login; publicado pelo "Publicar na Web" do Power BI Service)

**Vídeo (40 s), rolando o relatório no Power BI Service** (gravado antes da raia 5):

https://github.com/user-attachments/assets/57491ecf-722b-4c4d-a495-e67a7a7986be

![Cabeçalho e cartões do relatório](../docs/img/relatorio/01-cabecalho.png)

## O que o relatório responde

No relatório, as respostas são **geradas pelos dados** ([ADR 0023](../docs/adr/0023-textos-do-relatorio-por-medida.md)): comparam os últimos 12 meses com os 12 anteriores e se reescrevem quando chega um mês novo. A tabela abaixo é uma **foto** de 20/11/2026, com dados até set/2026 (out/2025–set/2026 × out/2024–set/2025).

| # | Pergunta | Resposta (foto de 20/11/2026) |
|---|---|---|
| 1 | Onde e quando falta oferta? | A espera piorou: o P90 da cidade subiu de 8,5 para 9,8 min, puxado pela Uber (8,4 → 10,3 min); a Lyft ficou estável. Falta oferta fora de Manhattan (Breezy Point, City Island e Flushing Meadows: 18 a 21 min) e nas madrugadas de feriado e fim de semana |
| 2 | Como evolui a economia unitária? | Cada corrida rende mais: receita por milha +5,7% e repasse por hora de corrida +2,9%, com take rate estável em ~22,8%. A exceção é a Lyft: take rate de 21,8% para 23,0% |
| 3 | Qual foi o impacto da taxa de congestionamento? | Nos 12 meses depois de 05/01/2025, as corridas para o centro caíram 4,9% por dia enquanto a cidade cresceu 2,0%; a queda veio do resto de Manhattan (−9,6%), e Brooklyn, Queens e Bronx ficaram estáveis |
| 4 | Onde a Lyft perde terreno para a Uber? | A Lyft subiu de 26,9% para 27,7% de share, puxada pelo Bronx (+4,2 pp), mas recuou 0,9 pp em Manhattan: perde terreno em 48 das 211 maiores zonas, 45 delas em Manhattan |
| 5 | Dá para prever a demanda? | Sim: o modelo errou 12,9% contra 14,1% do palpite sazonal (média da mesma hora nas 4 semanas anteriores), vencendo nas 6 janelas de abr a set/2026. Para outubro, prevê 22,2 milhões de corridas |

| Raia | Imagem |
|---|---|
| 1 · Oferta | ![Raia 1](../docs/img/relatorio/02-raia1-oferta.png) |
| 2 · Economia | ![Raia 2](../docs/img/relatorio/03-raia2-economia.png) |
| 3 · Taxa do CBD | ![Raia 3](../docs/img/relatorio/04-raia3-cbd.png) |
| 4 · Uber × Lyft | ![Raia 4](../docs/img/relatorio/05-raia4-share.png) |
| 5 · Previsão | ![Raia 5](../docs/img/relatorio/07-raia5-previsao.png) |

Ao passar o mouse sobre um cartão, ele mostra o que é o número e como é calculado:

![Cartão com a explicação ao passar o mouse](../docs/img/relatorio/06-hover-cartao.png)

Na raia 5, o mesmo vale para os cartões da previsão:

![Cartão da previsão com a explicação ao passar o mouse](../docs/img/relatorio/08-hover-previsao.png)

## Como foi construído

| Peça | Escolha | Por quê |
|---|---|---|
| Fonte | Camada **Gold** (Apache Iceberg no S3, consultada pelo Athena), em modo **Import** | Consulta paga por dado lido: importar uma vez é mais barato e rápido que consultar a cada clique |
| Modelo | **Estrela** com 3 fatos (demanda por hora, histograma de espera, origem-destino mensal) e dimensões de tempo encadeadas (mês → período → hora) | Um filtro de mês chega às três fatos pelo caminho certo, inclusive ao histograma, que não tem hora real |
| Métricas | Fórmulas definidas uma vez no dbt e reproduzidas no DAX (take rate como razão das somas, economia só com tarifa válida) | **Consistência semântica**: o mesmo número no SQL e no Power BI |
| Espera P90 | Calculada a partir de um **histograma de faixas** guardado na Gold, por interpolação | Percentil não soma nem tira média; o histograma permite recalcular o P90 para qualquer recorte. Conferido contra o Athena em 9 recortes |
| Página | **Página única com raias**, uma por pergunta, com resposta escrita antes dos gráficos | Leitura de apresentação executiva ([ADR 0019](../docs/adr/0019-relatorio-pagina-unica-com-raias.md)) |
| Versionamento | **PBIP** (modelo em TMDL, relatório em PBIR), em texto no Git | Diferenças linha a linha e revisão das medidas ([ADR 0011](../docs/adr/0011-pbip-no-repositorio.md)) |
| Página como código | Os visuais foram gerados por um script a partir de um contrato de desenho ([`gerador/gerar_pagina.js`](gerador/gerar_pagina.js), [`_brief/report-spec.md`](../_brief/report-spec.md)) e refinados no Desktop | Reprodutível e revisável |
| Mapa | TopoJSON próprio das 263 zonas de táxi, gerado do shapefile oficial ([`mapas/`](mapas/README.md)) | Os mapas padrão não conhecem as zonas da TLC |
| Previsão (raia 5) | Duas tabelas de ML da Gold (`ml_forecast_demanda`, `ml_backtest_metricas`) e uma `dim_execucao` que filtra as duas | Cada execução do modelo fica guardada (versionamento); somar execuções duplicaria a previsão, então a página mostra uma por vez |
| WAPE no DAX | Erro absoluto linha a linha (zona × hora), só nas linhas com realizado, ÷ realizado | Conferido contra o WAPE calculado em Python nos 6 meses do backtest: iguais até a 14ª casa decimal |
| Textos | Respostas, aberturas e subtítulos gerados por medida, com períodos e afirmações por regra (o que é "estável", quem "puxou") | Nenhum texto fica errado quando chegam dados novos ([ADR 0023](../docs/adr/0023-textos-do-relatorio-por-medida.md)) |

## Como abrir

O projeto abre no **Power BI Desktop** pelo arquivo `rideshare-marketplace/Rideshare Marketplace Intelligence.pbip`. Os dados importados (`cache.abf`, ~540 MB) não ficam no Git: para ver números, é preciso atualizar a partir do Athena, o que exige acesso à conta AWS do projeto, o driver ODBC do Amazon Athena (2.5) e o DSN `rideshare-athena`. Sem esse acesso, o modelo e as medidas podem ser lidos como texto em `Rideshare Marketplace Intelligence.SemanticModel/definition/`.

## Limitações conhecidas

- A espera P90 acima de 15 minutos é estimada (margem de até 1 minuto), por causa da largura das faixas do histograma.
- As respostas e as aberturas das raias ignoram o filtro de período: comparam sempre os últimos 12 meses com os 12 anteriores (a da taxa do CBD, os 12 meses antes e depois de 05/01/2025). Subtítulos, cartões e gráficos seguem o período escolhido.
- A versão publicada no Power BI Service é uma foto dos dados, sem atualização agendada (exigiria um gateway local).
- Raia 5: o modelo erra para baixo (~2,4%, efeito da função de perda), o teste usa o clima observado (otimista) e a previsão não é operacional, porque a TLC publica os dados com ~2 meses de atraso. As três limitações estão na própria raia.
- O formato dos números nos gráficos segue a configuração regional de quem vê o relatório (nos prints, inglês: `3,815,508`, `Jan 2024`), mesmo com o modelo em `pt-BR`. Cartões, título, ficha e respostas formatam em português por conta própria.
