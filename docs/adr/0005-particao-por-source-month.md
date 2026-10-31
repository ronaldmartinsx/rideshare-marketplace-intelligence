# ADR 0005: Partição da Silver e da Gold por `source_month`

- **Status:** Decidido e validado (Fase 1: partição e idempotência; Fase 3: premissa conferida nos 32 meses)
- **Data:** decidido na spec (seção 6.3); escrito em 28/10/2026
- **Fase:** 3
- **Relacionado:** ADR 0014 (estratégia incremental: `append` + `delete` do mês)

## Contexto

As tabelas Iceberg da Silver e da Gold precisam de uma coluna de partição. Ela decide duas coisas:

- **o que o Athena pula numa consulta** (partition pruning);
- **o que um reprocessamento apaga.** O ADR 0014 apaga o mês e grava de novo.

Havia três candidatas: o mês do arquivo de origem (`source_month`), o mês do embarque, e o dia do embarque.

A TLC publica **um arquivo por mês**, e a ingestão (Fase 2) controla versões por arquivo: o manifesto tem uma versão vigente por `(fonte, source_month)`. A spec já previa `source_month`, com a ressalva de que corridas na virada do mês poderiam cair fora do mês do arquivo.

Evidências:
- **jan/2025 (20/10/2026):** 100% das corridas do arquivo de janeiro embarcaram em janeiro. A "virada do mês" não apareceu.
- **Produção (28/10/2026):** o teste `date_format(pickup_datetime, '%Y-%m') = source_month` (severidade erro) passou nos **32 meses**, de 2024-01 a 2026-08.

## Decisão

Todas as tabelas incrementais da Silver (`stg_tlc__hvfhv_trips`, `int_trips_enriched`) e da Gold (`fct_*`) são particionadas por **`source_month`**, o mês do arquivo da Bronze (`AAAA-MM`). A granularidade é mensal, não diária.

A premissa "toda corrida do arquivo embarcou no mês do arquivo" deixa de ser suposição e vira **teste**. Se um dia falhar, o mês fica vermelho e a Gold não é construída.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Mês do embarque | Hoje dá o mesmo resultado (teste acima), mas quebra o reprocessamento se a premissa mudar: um arquivo com corridas de dois meses espalharia linhas em duas partições, e o `delete` do mês apagaria corridas de outro arquivo |
| Dia do embarque | ~30× mais partições e arquivos pequenos (o mês tem ~21 milhões de corridas e cabe em arquivos de ~180 MB). O reprocessamento continuaria sendo por arquivo, ou seja, por mês |
| Sem partição | Todo reprocessamento e toda consulta leriam a tabela inteira (~40 GB na `int`). Estoura o freio de 3 GiB por consulta do workgroup |

## Consequências

**Ganhamos:**
- **Uma unidade só, do começo ao fim:** arquivo da TLC = versão no manifesto = partição na Silver e na Gold = linha no registro de construção (ADR 0016) = mês da `dbt_mes`.
- O reprocessamento de um mês apaga exatamente o que aquele arquivo gerou.
- As consultas por mês leem só a partição: os testes da Silver com `where source_month = ...` leem poucos MB.

**Perdemos / cuidados:**
- Quem filtra por data de embarque (o Power BI, por exemplo) não ganha pruning automático pela data. Na Gold isso pesa pouco, porque as tabelas são pequenas.
- A premissa depende do formato de publicação da TLC. Se um arquivo trouxer corridas de outro mês, o teste falha e será preciso decidir de novo (novo ADR).
