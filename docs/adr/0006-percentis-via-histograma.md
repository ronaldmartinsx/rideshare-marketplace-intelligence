# ADR 0006: Percentis de espera via histograma na Gold (18 faixas, grão por hora do dia)

- **Status:** Decidido e validado na Fase 3 (muda o grão e as faixas da spec, seção 6.4)
- **Data:** decidido em 20/10/2026 (plano da Fase 3, F4); escrito em 28/10/2026
- **Fase:** 3

## Contexto

O P50 e o P90 do tempo de espera são KPIs do projeto (spec 2.5). Percentil **não é aditivo**:

- o P90 de uma cidade não é a média dos P90 das zonas;
- também não é a média ponderada deles, porque o erro vem da **forma** de cada distribuição, não do tamanho.

A Gold não guarda corridas individuais, então o Power BI precisa de uma estrutura que **some** e da qual se tire o percentil de qualquer recorte. Essa estrutura é o histograma: contagem de corridas por faixa de espera.

A spec propunha grão "hora × zona × operadora × faixa", com 6 faixas (0–2, 2–4, 4–6, 6–10, 10–15, 15+ min).

Evidências (jan/2025, corridas válidas com espera entre 0 e 2 h):

| Método | P90 da cidade (min) |
|---|---|
| Real (das corridas) | **8,05** |
| Média simples dos P90 das 262 zonas | 8,55 |
| Média ponderada dos P90 das zonas | 7,90 |
| Histograma da spec, 6 faixas | 8,81 (+9%: o P90 cai na faixa 6–10, larga demais) |
| Faixas de 1 min até 30 + "30+" | 8,06 |
| **Adotado: 18 faixas** | **8,06** |

Tamanho medido em jan/2025 (28/10/2026):

| Grão | Linhas no mês |
|---|---|
| Spec: hora do relógio × zona × operadora × 6 faixas | 1.552.010 |
| Hora do relógio × zona × operadora × 18 faixas | 2.986.630 |
| **Adotado: mês × hora do dia × tipo de dia × zona × operadora × 18 faixas** | **473.497** |

O tamanho vem das **células pequenas**, não do número de faixas: na hora do relógio, cada combinação tem poucas corridas, e quase toda faixa vira uma linha.

## Decisão

`fct_espera_histograma` com:

- **Faixas (18):** de 1 em 1 minuto até 15 min, depois 15–20, 20–30 e 30+. Cada linha traz `faixa_inicio_min` e `faixa_fim_min` para a interpolação.
- **Grão:** mês (`source_month`) × hora do dia (0–23) × tipo de dia (útil / fim de semana / feriado) × zona de origem × operadora × faixa.
- **Conteúdo:** só corridas válidas no nível corrida (`is_valid`) e no nível métrica (`is_valid_wait_metric`: espera entre 0 e 2 h).
- **Consumo:** para qualquer recorte, somar as contagens por faixa, acumular até 50% ou 90% e interpolar dentro da faixa. Os passos estão no `meta` do YAML e viram DAX na Fase 4.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Média (simples ou ponderada) dos percentis | Erra o P90 da cidade em −2% a +6% (tabela acima) e não tem como corrigir |
| Grão e faixas da spec | +9% no P90 (faixa 6–10 larga) e 3× mais linhas que o adotado |
| Hora do relógio com 18 faixas | Precisão igual, ~6× mais linhas |
| Guardar a corrida na Gold e calcular o percentil no Power BI | ~21 milhões de linhas por mês no modelo: contraria a spec 6.4 ("a corrida individual não sai da Silver") |
| `approx_percentile` pré-calculado por recorte | Só serve para os recortes escolhidos antes. Qualquer filtro novo no Power BI exigiria mudar a Gold |

## Consequências

**Ganhamos:**
- O P90 de qualquer combinação de zona, operadora, hora do dia, tipo de dia e mês sai com erro < 1% (8,06 × 8,05 na cidade; 9,30 × 9,25 em Manhattan, 18h de dia útil, mai/2026).
- Tamanho controlado: produção tem 343.839 a 510.616 linhas por mês (média 434.762), 13,9 milhões nos 32 meses.

**Perdemos / cuidados:**
- **Não dá o P90 de um dia específico** (ex.: 05/01/2025 às 18h), só do mês por hora do dia e tipo de dia. Para comparar antes e depois da taxa do CBD, o corte é por mês.
- A faixa "30+" não tem fim: um percentil que caia nela não pode ser interpolado. Na prática o P90 fica por volta de 8–10 min, longe dela.
- O tipo de dia depende do seed de feriados (2024–2026). Ano novo exige atualizar o seed.
