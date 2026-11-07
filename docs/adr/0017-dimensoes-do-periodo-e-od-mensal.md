# ADR 0017: Dimensões do período para o histograma e origem-destino mensal no Power BI

- **Status:** Decidido e validado na Fase 4 (passos 2 e 5)
- **Data:** 31/10/2026 (decisão); 01/11/2026 (reconstrução de produção); 02/11/2026 (modelo no Power BI)
- **Fase:** 4
- **Relacionado:** ADR 0006 (percentis via histograma), ADR 0011 (PBIP), ADR 0016 (registro de construção), D1, D2 e D7 do plano da Fase 4

## Contexto

A Seção 10 da spec previa uma estrela simples: as fatos ligadas a `dim_zona`, `dim_operadora` e `dim_tempo_hora`. Dois problemas apareceram ao planejar o modelo do Power BI.

**1. O histograma não tem hora real.** A `fct_espera_histograma` está no grão mês × hora do dia × tipo de dia × zona × operadora × faixa (ADR 0006). Ela não tem data nem hora exatas, então não pode ligar à `dim_tempo_hora` (uma linha por hora local de NY). Sem essa ligação, uma segmentação de mês filtra a demanda, mas o P90 **ignora o filtro em silêncio**: o leitor vê "jan/2025" no título e o P90 dos 33 meses no cartão.

**2. A origem-destino diária é pesada demais para o uso.** A `fct_od_diario` tem 55 milhões de linhas (819 MB no S3). As perguntas que usam origem-destino (taxa do CBD: antes × depois, de onde vêm as corridas que entram no centro) olham meses, não dias.

## Decisão

### Dimensões do período (D1)

Três dimensões novas no dbt, na Gold:

| Modelo | Grão | Linhas | Papel |
|---|---|---|---|
| `dim_mes` | mês (`ano_mes`, AAAA-MM) | 36 | Topo da hierarquia de tempo |
| `dim_periodo_espera` | mês × hora do dia × tipo de dia (`periodo_id`, ex.: `2025-03\|18\|util`) | 2.376 | **Dimensão encolhida** da `dim_tempo_hora`, no grão do histograma |
| `dim_faixa_espera` | faixa de espera | 18 | Limites e rótulo de cada faixa, para o eixo dos gráficos e para a interpolação |

A chave `periodo_id` entra na `dim_tempo_hora` e na `fct_espera_histograma`. No Power BI, as dimensões de tempo formam uma **cadeia**, sempre 1 → N e em direção única:

```
dim_mes ──► dim_periodo_espera ──► dim_tempo_hora ──► fct_demanda_zona_hora
   │                │
   │                └──► fct_espera_histograma ◄── dim_faixa_espera
   └──► fct_od_mensal
```

Uma segmentação na `dim_mes` chega às três fatos pelo caminho certo. Segmentações de hora do dia e tipo de dia vêm da `dim_periodo_espera`, que alcança a demanda (pela `dim_tempo_hora`) e o histograma (direto).

### Origem-destino mensal (D2)

A `fct_od_mensal` (mês × zona de origem × zona de destino × operadora) soma a `fct_od_diario` no dbt e é a tabela de origem-destino do Power BI. A diária fica no Athena. Um teste (`reconciliacao_od_mensal`) confere corridas e tarifa das duas, mês a mês.

### Zona de destino como segunda tabela (D7)

A `fct_od_mensal` tem duas zonas. No Power BI, o papel destino é uma **segunda tabela** (`dim_zona_destino`, Referência da `dim_zona` no Power Query), com relacionamento ativo próprio. Assim, "destino no CBD" vira um filtro comum, sem `USERELATIONSHIP` em cada medida. Decisão de modelagem do Power BI, registrada aqui por fazer parte do mesmo modelo; a Gold não muda.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Ligar o histograma à `dim_tempo_hora` com relacionamento muitos-para-muitos ou filtro bidirecional | O histograma não tem a chave da hora. Um relacionamento por colunas parciais (mês, hora do dia, tipo de dia) gera caminhos ambíguos e totais difíceis de explicar |
| Refazer o histograma por hora real | Muda o grão decidido no ADR 0006 e multiplica as linhas pelo número de dias do mês |
| Criar as dimensões no Power BI (tabelas calculadas em DAX ou no Power Query) | As dimensões existiriam só no relatório. O agente da Fase 6 e os testes do dbt não as veriam, e a consistência semântica entre SQL e DAX se perderia |
| Segmentações separadas por fato, ou sincronizadas | Frágil: duas segmentações que precisam ficar iguais à mão |
| Importar a `fct_od_diario` | 55 milhões de linhas para responder perguntas mensais: ~15 vezes as linhas da mensal |
| Destino como relacionamento inativo + `USERELATIONSHIP` | Funciona, mas cada medida de destino precisa lembrar de ativar o relacionamento; um filtro de segmentação por zona de destino não funciona sem medidas especiais |

## Consequências

- **Ganhamos:**
  - um filtro de mês filtra as três fatos com o mesmo recorte. Teste em jan/2025: demanda 20.403.058 = origem-destino 20.403.058; histograma 20.203.505 (só espera válida);
  - o P90 respeita o período escolhido;
  - a origem-destino entra no Power BI com 3,66 milhões de linhas (60 MB), conferida contra a diária: 672.148.703 corridas nas duas, 0 meses divergentes.
- **Custou:**
  - reconstruir os 32 meses de produção: 3h44, ~US$ 0,69 no Athena;
  - uma exceção temporária `on_schema_change = 'append_new_columns'` no histograma, revertida depois;
  - a `dbt_mes` passou de 34 para 51 tasks.
- **Passamos a cuidar de:**
  - **Detecção automática de relacionamentos:** na primeira carga, o Desktop criou `dim_tempo_hora[ano_mes] → dim_mes`. Esse segundo caminho fez o Desktop **desativar em silêncio** a ligação `dim_tempo_hora → dim_periodo_espera`, e hora do dia e tipo de dia deixariam de filtrar a demanda. O atalho foi apagado e a detecção automática foi desligada no arquivo.
  - **Regra de uso:** em visuais com P50/P90, filtrar o tempo só pela `dim_mes` ou pela `dim_periodo_espera`. Filtros de data ou hora exata (`dim_tempo_hora`) não chegam ao histograma.
