# ADR 0009: Fuso horário: horário local de Nova York, sem fuso, nas corridas

- **Status:** Decidido na Fase 2 (decisão D9), com evidência nos dados
- **Data:** 18/10/2026
- **Fase:** 2
- **Risco relacionado:** R5 (spec, seção 13)

## Contexto

As quatro colunas de data e hora das corridas (`request_datetime`, `on_scene_datetime`, `pickup_datetime`, `dropoff_datetime`) não dizem em que fuso estão:

- O **dicionário oficial da TLC** não informa (conferido na Fase 1).
- O **rodapé dos arquivos** marca as quatro colunas como `isAdjustedToUTC = false` em todos os meses lidos (2019 a 2026): o horário é "de relógio de parede", **sem** fuso junto.

Então o fuso não se resolve olhando o tipo da coluna. Foi preciso testar nos dados. Nos EUA, na troca para o horário de verão o relógio pula das 2h para as 3h, e na volta a 1h acontece duas vezes. Se os horários forem locais de Nova York, isso aparece na contagem de corridas:

| Data | Hora | Corridas | Mesmo horário, dia anterior |
|---|---|---|---|
| 09/03/2025 (relógio pula de 2h para 3h) | 2h | **85** | 20.601 |
| 02/11/2025 (a 1h acontece duas vezes) | 1h | **75.292** | 48.411 |

A hora que "não existe" fica quase vazia, e a hora repetida soma duas horas reais. **Os horários estão no relógio local de Nova York.** As 85 corridas da hora inexistente ainda não têm explicação (registro antecipado, erro de equipamento?); fica para investigar na Fase 3.

## Decisão

1. **As corridas ficam no horário local de Nova York, sem fuso, em todas as camadas** (Bronze, Silver, Gold), como a TLC entrega.
2. **Momentos de máquina ficam em UTC:** `ingest_ts`, `registrado_em` e `last_modified` do manifesto. Os `COMMENT` das colunas dizem isso, para ninguém misturar.
3. **O clima é pedido em UTC** ao Open-Meteo e convertido para o horário de Nova York **na Silver** (Fase 3), com `AT TIME ZONE 'America/New_York'`, que aplica as regras do horário de verão. Motivo: o parâmetro `timezone` da API usa um deslocamento fixo para o período inteiro e **ignora** a troca do horário de verão (documentação da API). Cada arquivo de clima inclui o dia 1 do mês seguinte, porque as últimas horas de cada mês em Nova York caem no dia seguinte em UTC.
4. **As duas horas de troca do horário de verão** (a inexistente em março e a repetida em novembro) ganham uma marcação na Fase 3, para não distorcerem análises por hora nem a previsão da Fase 5.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Converter as corridas para UTC na Silver | **Impossível sem ambiguidade:** na hora repetida de novembro não há como saber a qual das duas "1h" cada corrida pertence. Converter inventaria uma precisão que o dado não tem |
| Guardar as duas versões (local e UTC) | Duplica colunas e herda a mesma ambiguidade na versão UTC |
| Pedir o clima já em `America/New_York` | A API ignora o horário de verão dentro do período pedido: as horas depois da troca sairiam deslocadas em 1 hora |

## Consequências

**Ganhamos:**
- As perguntas de negócio são sobre o horário local ("pico às 18h em NYC"), e o dado já responde nesse horário, sem conversão.
- Quem usa o Power BI pensa no horário da cidade: nenhuma surpresa de fuso no dashboard.

**Perdemos / cuidados:**
- Duas horas por ano são anômalas por construção: a de março quase vazia e a de novembro com o volume de duas horas. Precisam de marcação (Fase 3) e de cuidado no modelo de previsão (Fase 5).
- Cruzar corridas com dados em UTC (o clima) exige conversão explícita. O cruzamento na hora repetida de novembro também é ambíguo do lado do clima (duas horas UTC para uma hora local): a Silver vai agregar as duas.
- Se a TLC algum dia passar a entregar UTC (`isAdjustedToUTC = true`), o contrato de schema não percebe hoje (ele confere o tipo, não essa marcação). Pendência anotada para a Fase 3.
