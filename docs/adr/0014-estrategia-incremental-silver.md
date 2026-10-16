# ADR 0014: Estratégia incremental da Silver (append + delete do mês)

- **Status:** Decidido e validado na Fase 1 (idempotência confirmada; janela sem o mês medida em 46 s; ver `docs/validacao/fase-1.md`, seção 6)
- **Data:** 14/10/2026
- **Fase:** 1

## Contexto

A spec (seção 6.3) pede que os models incrementais da Silver sejam **idempotentes por partição**: reprocessar um `source_month` substitui só aquele mês, inclusive quando a TLC republica um arquivo. A estratégia prevista era `insert_overwrite` (ou `merge`), com a ressalva "⚠️ A VALIDAR" (risco R2).

Evidência (dbt-core 1.12.5, dbt-athena 1.11.1, 14/10/2026): o primeiro `dbt build` do `stg_tlc__hvfhv_trips` falhou na compilação com:

```
Invalid incremental strategy provided: insert_overwrite
Incremental models on Iceberg tables only work with 'append', 'microbatch' or 'merge' (v3 only) strategy.
```

## Decisão

Models incrementais da Silver usam **`append` com um `pre_hook` que apaga o mês a ser processado**:

```sql
{{ config(
    materialized='incremental',
    incremental_strategy='append',
    partitioned_by=['source_month'],
    pre_hook="{% if is_incremental() %} delete from {{ this }} where source_month = '<mês>' {% endif %}"
) }}
```

O mês vem da variável `source_month` do dbt, passada pelo orquestrador (Airflow, Fase 3).

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| `insert_overwrite` | Não suportado para Iceberg no dbt-athena 1.11.1 (erro acima) |
| `merge` com chave surrogate | Não é idempotente na republicação: a chave prevista é um hash que inclui valores; uma tarifa corrigida gera chave nova e a linha antiga fica duplicada; linhas removidas pela TLC nunca saem |
| `microbatch` por `pickup_datetime` | Recorta pelo horário da corrida, não pelo mês do arquivo; o filtro na Bronze não usaria as colunas de partição (sem pruning: leria todos os meses a cada execução). Não testado com o Athena |
| Macro própria de overwrite de partição | Mais código para manter; o `pre_hook` resolve com duas linhas |

## Consequências

**Ganhamos:**
- Idempotência por `source_month`: rodar duas vezes o mesmo mês dá o mesmo resultado; a republicação substitui o mês inteiro.
- O `DELETE` fica explícito no código do model.
- O filtro na Bronze continua pelas partições (`year`, `month`): partition pruning preservado.

**Perdemos / cuidados:**
- São **dois commits Iceberg** (delete e insert), não um. Entre eles, por alguns segundos, o mês fica ausente para quem consulta. Aceitável para carga mensal sem consumo simultâneo; o Power BI deve atualizar depois do `dbt build`.
- Se o insert falhar depois do delete, o mês fica vazio até a próxima execução. Mitigação: o teste de volume (gate da seção 8) barra a Gold; o time travel permite consultar a versão anterior.
- O `DELETE` em Iceberg gera arquivos de deleção e snapshots; a manutenção (`OPTIMIZE`/`VACUUM`) entra na Fase 3.
- A primeira execução (tabela inexistente) processa todos os meses presentes na Bronze, não só o da variável.
