# ADR 0020: Zonas da previsão por filtro semântico, não por "top N por volume"

- **Status:** Decidido e aplicado na Fase 5 (passo 1), com medição
- **Data:** 14/11/2026
- **Fase:** 5
- **Relacionado:** spec 9.1 (escopo da previsão, marcado ⚠️ "definir N com os dados"), `docs/validacao/fase-5.md` seção 1, ADR 0007 (CBD por lista de zonas)

## Contexto

A spec 9.1 definia o escopo da previsão como "as top N zonas por volume (ex.: 50)", com o aviso **⚠️ Definir N com os dados**. O pressuposto por trás disso é o de sempre em demanda urbana: que o volume se concentra em poucas zonas, e que modelar as maiores cobre quase todo o mercado.

A medição desfez o pressuposto. Cobertura acumulada nos últimos 12 meses:

| N zonas | % da demanda |
|---|---|
| 10 | 12,6% |
| **50** | **44,6%** |
| 100 | 70,1% |
| 150 | 86,4% |
| 200 | 96,6% |

A zona líder (138, LaGuardia) é **1,95%** do total; a segunda (132, JFK), 1,59%. **Não é uma curva de Pareto.**

A razão é que HVFHV não é táxi amarelo. Táxi amarelo concentra em Manhattan e aeroportos; Uber e Lyft em Nova York são majoritariamente deslocamento de bairro — Brooklyn, Queens, Bronx —, e isso espalha a demanda por quase todas as zonas.

Com o N = 50 sugerido, o projeto preveria **44,6% do mercado e ignoraria 55,4%**.

## Decisão

O critério deixa de ser estatístico e passa a ser **semântico**: entram as **zonas conhecidas e dentro de Nova York**, usando as marcas que a `dim_zona` já tem desde a Fase 3.

```sql
where is_zona_conhecida and not is_fora_de_nyc
```

Exclui exatamente 3 zonas:

| Zona | Nome | Motivo |
|---|---|---|
| 1 | Newark Airport | fora de NYC (Nova Jersey) |
| 264 | N/A | zona desconhecida |
| 265 | Outside of NYC | fora de NYC |

Resultado medido: **262 zonas, 99,99% da demanda**, ao custo de 12.815 corridas em 253 milhões (**0,005%**).

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Top 50 por volume**, como a spec sugeria | Preveria 44,6% do mercado. "Previ menos da metade da demanda" é indefensável num portfólio |
| **Top 150 por volume** (86,4%) | Melhor cobertura, mas mantém o problema de fundo: escolher N exige olhar o volume, e olhar o período de teste para escolher é **vazamento de seleção** |
| **Todas as 265 zonas, sem filtro** | Cobertura total, mas treina o modelo em zonas que não são lugares reais (`N/A`, `Outside of NYC`) e em Newark, que é outro estado |

## Consequências

- **Ganhamos:** cobertura de 99,99% em vez de 44,6%; e a eliminação completa do **vazamento de seleção** (Aula 2, vazamento nº 4) — critério semântico não tem o que vazar, critério estatístico tem.
- **O custo é quase nulo porque o modelo é global** (decisão da spec 9.1): um modelo só, com a zona como feature. Incluir 262 zonas em vez de 50 custa praticamente o mesmo treino.
- **O WAPE protege o lado fraco:** sendo ponderado por volume, zona minúscula não distorce a métrica principal — que era o medo por trás do "top N". A proteção já estava na métrica escolhida.
- **A tabela de features fica maior:** ~6,3 milhões de linhas em vez de ~1,2 milhão. Medido: 415 MB em memória, 27 s de leitura. Irrelevante.
- **Divergência da letra da spec**, que a própria spec deixou aberta com o ⚠️. A Seção 9.1 foi atualizada com a medição.
