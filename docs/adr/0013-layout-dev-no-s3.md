# ADR 0013: Layout do ambiente de dev no S3

- **Status:** Decidido
- **Data:** 12/10/2026
- **Fase:** 0

## Contexto

A spec (seções 6.1 e 11.2) cria bancos `dev_bronze`, `dev_silver` e `dev_gold` no Glue, mas não define onde ficam os arquivos de dev no S3. A política IAM do Airflow precisa dessa resposta para limitar onde ele pode gravar e apagar.

## Decisão

Um único bucket (`<prefixo>-lake`), com o dev isolado no prefixo `dev/`:

| Camada | Prod | Dev |
|---|---|---|
| Bronze | `bronze/` | lê a mesma `bronze/` de prod (não há `dev/bronze/`) |
| Silver | `silver/` | `dev/silver/` |
| Gold | `gold/` | `dev/gold/` |

As tabelas de `dev_bronze` são definições no Glue que apontam para os mesmos arquivos de `bronze/`.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Bucket separado para dev | Mais um recurso e mais ARNs, sem ganho real num projeto de uma pessoa |
| Copiar a Bronze para `dev/bronze/` | O arquivo bruto é imutável e idêntico; copiar só duplica custo e cria risco de divergência |
| Dev e prod no mesmo prefixo | Um `dbt build` em dev poderia sobrescrever dados de prod |

## Consequências

**Ganhamos:** o dev nunca grava fora de `dev/` (garantido pela política IAM); a Bronze tem uma única cópia.

**Perdemos / cuidados:**
- Dev e prod compartilham o bucket: uma regra de ciclo de vida no bucket precisa filtrar por prefixo para não afetar os dois.
- Ponto em aberto para a Fase 2: o manifesto de ingestão (`bronze.ingestion_manifest`) é uma tabela Iceberg, e Iceberg apaga arquivos antigos na manutenção. Se ele ficar em `bronze/`, conflita com a regra "Bronze sem `DeleteObject`". Resolver na Fase 2 (provável: prefixo próprio para o manifesto).
