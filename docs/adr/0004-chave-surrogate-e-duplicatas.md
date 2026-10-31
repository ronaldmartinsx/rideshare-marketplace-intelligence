# ADR 0004: Chave surrogate por hash e política de duplicatas exatas

- **Status:** Decidido e validado na Fase 3 (32 meses em produção, teste `unique` verde em todos)
- **Data:** decidido em 20/10/2026 (plano da Fase 3, F2 e F3); escrito em 28/10/2026
- **Fase:** 3

## Contexto

A corrida da TLC não tem chave natural: o arquivo não traz um "número da corrida". A spec (seção 6.3, regra 1) pede uma chave surrogate por hash, um teste de unicidade e uma política escrita para duplicatas exatas.

Evidências (`dev_silver`, jan/2025, 20/10/2026):

- Com **5 colunas** (licença, horário do pedido, horário do embarque, zona de origem, zona de destino) houve **27 colisões**: duas corridas reais com a mesma chave. Eram corridas compartilhadas, com tarifas diferentes.
- Com **as 25 colunas** da corrida não houve colisão, e havia **0 duplicatas exatas** nos 3 meses de dev.

Na carga de produção (28/10/2026, 32 meses) apareceram **17 duplicatas exatas**: as 25 colunas iguais, inclusive horários ao segundo e valores ao centavo. Todas são da Uber (HV0003): 15 em 2025-10, 1 em 2025-12 e 1 em 2026-03.

## Decisão

1. **Chave de conteúdo:** `dbt_utils.generate_surrogate_key` das 25 colunas da corrida. Mesmo conteúdo → mesma chave. O dbt-utils trata NULL sem zerar o hash.
2. **Ordem da duplicata:** `row_number()` dentro de cada chave de conteúdo. A primeira cópia é 1, a segunda é 2, e assim por diante.
3. **Chave final `corrida_id`:** hash de (chave de conteúdo, ordem). É única mesmo com duplicatas, e o teste `unique` + `not_null` roda todo mês.
4. **Política de duplicatas: marcar, não apagar.** A cópia de ordem ≥ 2 fica na Silver com `is_valid = false` e `invalid_reason = 'duplicata_exata'`. A Gold só conta corridas válidas, então a duplicata não infla a demanda.

A chave de conteúdo é só um passo intermediário e **não é gravada** (ver Consequências).

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Hash de poucas colunas (licença, horários, zonas) | 27 colisões em um mês: corridas reais diferentes com a mesma chave, e o teste `unique` falharia |
| Hash só das 25 colunas, sem a ordem | Duas cópias idênticas teriam a mesma chave: o `unique` falharia nos 3 meses com duplicata |
| `SELECT DISTINCT` (apagar a duplicata) | Viola "qualidade se marca, não se apaga" (spec 6.3): some a evidência de que a TLC mandou a linha duas vezes |
| Manter a duplicata como válida | Infla a contagem. São só 17 em 651 milhões, mas a regra estaria errada |
| ID aleatório (`uuid()`) | Muda a cada reconstrução: o mesmo mês reprocessado teria chaves diferentes (não determinístico) |

## Consequências

**Ganhamos:**
- A chave é determinística: reconstruir a mesma versão de um mês gera as mesmas `corrida_id`.
- A duplicata fica visível e contável na Silver (`invalid_reason`). A Gold fica limpa sem perder a auditoria.

**Perdemos / cuidados:**
- Um hash é texto aleatório e quase não comprime no Parquet. A `corrida_id` sozinha pesa boa parte dos ~1,3 GB por mês da `int_trips_enriched`. Por isso a chave de conteúdo não é gravada: economiza ~0,6 GB por mês.
- Se a TLC republicar um mês com um valor corrigido, a `corrida_id` daquela corrida muda. É aceitável: nenhuma tabela fora da Silver guarda `corrida_id`, porque a corrida individual não sai da Silver (spec 6.4).
- Entre duas cópias idênticas, qual recebe a ordem 1 é arbitrário. Não importa, porque as duas têm o mesmo conteúdo.
- Interpretação (não verificada com a TLC): 25 colunas iguais ao segundo e ao centavo indicam registro duplicado, não duas corridas reais.
