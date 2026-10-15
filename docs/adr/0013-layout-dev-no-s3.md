# ADR 0013: Layout do ambiente de dev no S3

- **Status:** Decidido (revisado em 14/10/2026; ver "Revisão")
- **Data:** 12/10/2026
- **Fase:** 0 (revisão na Fase 1)

## Contexto

A spec (seções 6.1 e 11.2) cria bancos `dev_bronze`, `dev_silver` e `dev_gold` no Glue, mas não define onde ficam os arquivos de dev no S3. A política IAM do Airflow precisa dessa resposta para limitar onde ele pode gravar e apagar.

## Decisão

Um único bucket (`<prefixo>-lake`). **Regra: o prefixo no S3 é igual ao nome do banco no Glue.**

| Camada | Prod | Dev |
|---|---|---|
| Bronze | `bronze/` | lê a mesma `bronze/` de prod (não há `dev_bronze/`) |
| Silver | `silver/` | `dev_silver/` |
| Gold | `gold/` | `dev_gold/` |

As tabelas de `dev_bronze` são definições no Glue que apontam para os mesmos arquivos de `bronze/`.

## Revisão (14/10/2026)

A versão original deste ADR usava `dev/silver/` e `dev/gold/`. Ao montar o projeto dbt (Fase 1), verificou-se que o dbt-athena monta o caminho das tabelas como `<s3_data_dir>/<banco>/<tabela>/` (`s3_data_naming: schema_table`), o que produz `dev_silver/` e `dev_gold/`. Manter o layout original exigiria configurar o local de cada model à mão. A intenção do ADR (dev nunca grava fora do espaço de dev) não muda; só o nome do prefixo. A política IAM do Airflow foi ajustada junto.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Bucket separado para dev | Mais um recurso e mais ARNs, sem ganho real num projeto de uma pessoa |
| Copiar a Bronze para o espaço de dev | O arquivo bruto é imutável e idêntico; copiar só duplica custo e cria risco de divergência |
| Dev e prod no mesmo prefixo | Um `dbt build` em dev poderia sobrescrever dados de prod |
| Manter `dev/silver/` (versão original) | Exigiria `external_location` em cada model do dbt |

## Consequências

**Ganhamos:** a regra "prefixo = banco" é fácil de lembrar e de auditar; o dev nunca grava fora de `dev_*/` (garantido pela política IAM); a Bronze tem uma única cópia.

**Perdemos / cuidados:**
- Dev e prod compartilham o bucket: uma regra de ciclo de vida no bucket precisa filtrar por prefixo para não afetar os dois.
- Ponto em aberto para a Fase 2: o manifesto de ingestão (`bronze.ingestion_manifest`) é uma tabela Iceberg, e Iceberg apaga arquivos antigos na manutenção. Se ele ficar em `bronze/`, conflita com a regra "Bronze sem `DeleteObject`". Resolver na Fase 2 (provável: prefixo próprio para o manifesto).
