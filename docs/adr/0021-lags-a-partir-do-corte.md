# ADR 0021: Defasagens medidas a partir do corte da previsão, não da hora-alvo

- **Status:** Decidido e aplicado na Fase 5 (passo 2b), com dois testes que provam a ausência de vazamento
- **Data:** 14/11/2026
- **Fase:** 5
- **Relacionado:** spec 9.1 (features de defasagem de 1 a 4 semanas), `docs/validacao/fase-5.md` seção 3, D1 do plano da Fase 5

## Contexto

A spec 9.1 pede prever **o mês seguinte ao último disponível** usando **defasagens (lags) de 1 a 4 semanas**. As duas exigências juntas não fecham.

Para prever a demanda de **28 de outubro**, o lag de 1 semana é **21 de outubro** — que também está no futuro. Para a maior parte das horas do mês previsto, os lags de 1 a 4 semanas caem **dentro do próprio mês que se quer prever**, e portanto não existem no momento da previsão.

Havia um caminho tentador e errado. O histórico inteiro está no disco, então **daria** para treinar dando ao modelo a sexta anterior ao alvo: para o alvo "sexta 15/05", mostrar a "sexta 08/05". É um `LAG()` e pronto. Mas no dia de valer, parado no fim de abril, a sexta mais recente é **24/04** — três semanas antes do alvo, não uma.

O modelo treinado assim aprende "o número que me deram é quase a resposta", e aplica essa confiança a um número muito mais velho. É **desalinhamento treino-produção**: vazamento disfarçado de inconsistência, com a assinatura clássica de melhorar as métricas sem dar erro nenhum.

## Decisão

Os lags são medidos a partir do **corte da previsão**, não da hora-alvo.

A feature passa a ser "a demanda naquela hora-da-semana, naquela zona, 1 a 4 semanas antes do **corte**" — igual para todas as horas do mês previsto. E a distância até o alvo entra como feature própria, `horizonte_horas` (1 a 744).

**A intuição:** no fim do mês você tira **uma** foto da rua e guarda no bolso. Perguntam sobre o dia 16 e sobre o dia 30, e você olha **a mesma foto** nas duas vezes. O que muda é só quanto ela ajuda — e isso é o horizonte.

**Consequência direta no grão:** o lag deixa de ser propriedade da hora-alvo e passa a ser propriedade do par (corte, hora-alvo). A `ml_features_demanda` tem grão **corte × hora-alvo × zona**, com 33 cortes mensais.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Lags da hora-alvo** (o "jeito fácil") | Desalinhamento treino-produção. O modelo treina com informação mais fresca do que a produção tem, e o WAPE sai otimista sem que nada acuse |
| **Previsão recursiva**: prever a hora 1, usar essa previsão como lag da hora 2 | Mais fiel à letra da spec, mas acumula erro ao longo de **744 passos**. O erro da primeira hora contamina todas as seguintes |
| **Usar só lags ≥ o horizonte** (ex.: lag de 5+ semanas) | Resolveria o vazamento, mas jogaria fora a informação mais recente disponível, que é justamente a mais preditiva |

## Consequências

- **A ausência de vazamento é TESTÁVEL, não declarada.** A tabela guarda `hora_lag_1`, a data em que a foto foi tirada, só para isso. Dois testes rodam a cada build:
  - `ml_features_lag_no_passado`: falha se `hora_lag_1 > corte` ou se o horizonte não for positivo;
  - `ml_features_mesma_foto`: para cada corte × zona × hora da semana, o número de valores **distintos** de cada lag tem de ser **1**. Medido: 44.016 combinações por corte (168 × 262), todas com 1.
- **O WAPE fica pior, e isso é correto.** No jeito fácil o número seria melhor e mentiroso.
- **A tabela cresce:** grão de três partes, ~6,3 milhões de linhas (33 cortes × ~730 horas × 262 zonas).
- **O baseline herda a garantia de graça:** ele é a média dos quatro lags, que já vêm medidos do corte.
- **Interpretação da spec, não contradição.** A spec pede os lags e pede o horizonte de um mês; esta decisão é a única leitura das duas que não vaza.
