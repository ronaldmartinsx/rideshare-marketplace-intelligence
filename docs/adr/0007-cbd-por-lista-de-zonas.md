# ADR 0007: CBD definido por lista de zonas da MTA, e não pela taxa

- **Status:** Decidido e validado na Fase 3 (lista conferida contra a cobrança da taxa em jan/2025 e ago/2026)
- **Data:** decidido na spec (seção 2.5, risco R7); lista montada em 20/10/2026; escrito em 28/10/2026
- **Fase:** 3

## Contexto

Uma das perguntas de negócio do projeto é o efeito da taxa de congestionamento de Manhattan (em vigor desde **05/01/2025**): volume, tarifa e destino das corridas que entram no centro (CBD), antes × depois.

Para isso, cada corrida precisa de uma marca "destino no CBD". Havia dois caminhos:

1. **Pela taxa:** `cbd_congestion_fee > 0`.
2. **Por uma lista de zonas de táxi** que ficam dentro da área da taxa.

Fatos:

- A coluna `cbd_congestion_fee` só existe nos arquivos a partir de 2025-01 (✅ verificado na Fase 2: 2 schemas nos 32 meses). Em 2024 ela é nula, e a comparação "antes" ficaria impossível.
- A MTA publica a lista oficial de zonas de táxi dentro do CBD: *MTA Central Business District Taxi Zones*, data.ny.gov, dataset `yfdc-w5jh`, com **38 zonas**.

Evidência (Silver de produção, corridas válidas, por zona de **destino**, 28/10/2026):

| Período | Menor % pagando a taxa, entre as 38 zonas da lista | Maior % pagando a taxa, entre as zonas fora da lista |
|---|---|---|
| 05 a 31/01/2025 | 96,2% | 88,2% (sem a zona 105) |
| ago/2026 | 95,6% | 89,4% |

A zona 105 (ilhas: Governors, Ellis e Liberty) teve 3 corridas em jan/2025, todas pagando. Ela não está na lista da MTA.

## Decisão

- O seed **`seed_zonas_cbd`** guarda as 38 zonas da lista oficial da MTA (fonte documentada no YAML do seed).
- **`is_dropoff_cbd`** na `int_trips_enriched` = zona de destino está no seed. **`is_cbd`** na `dim_zona` usa o mesmo seed.
- A coluna `cbd_congestion_fee` continua na Silver e na Gold **como valor em dinheiro** (soma da taxa), não como definição de "destino no CBD".

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| `cbd_congestion_fee > 0` | Nula antes de 2025: não serve para o "antes". E não marca destino: zonas fora da lista têm até 88–89% das corridas pagando |
| Lista derivada dos dados (zonas com ≥ 96% pagando) | Depende de um limite escolhido por nós e muda mês a mês (em ago/2026 a menor zona da lista ficou em 95,6%). A fonte oficial é estável e citável |
| Polígono da área da taxa cruzado com o polígono de cada zona | Precisa de geometria (shapefile) e de uma regra para zonas parcialmente dentro. A MTA já fez esse trabalho na lista |

## Consequências

**Ganhamos:**
- A mesma definição vale para 2024, 2025 e 2026: dá para comparar antes × depois.
- A fonte é oficial e citável, e o seed é revisável no repositório.
- A lista foi conferida contra o dado: dentro da lista, ~96% ou mais das corridas pagam; fora dela, no máximo ~89%.

**Perdemos / cuidados:**
- "Destino no CBD" não é o mesmo que "pagou a taxa". Uma corrida que só atravessa o CBD pode pagar sem terminar nele. Explicação provável para os 88–89% fora da lista; **não verificado**.
- A zona 105 fica fora da lista (fonte MTA), apesar de pagar. O impacto é desprezível: 3 corridas em jan/2025.
- Se a MTA mudar a área da taxa, o seed precisa ser atualizado, e a Gold reconstruída com `forcar_meses` (ADR 0016).
