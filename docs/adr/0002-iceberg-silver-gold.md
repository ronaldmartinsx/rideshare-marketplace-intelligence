# ADR 0002: Iceberg como formato de tabela da Silver e da Gold

- **Status:** Decidido e validado na Fase 1 (ver `docs/validacao/fase-1.md`, seções 6 e 7)
- **Data:** 15/10/2026 (decisão tomada na spec v1.0; registrada ao fim da Fase 1)
- **Fase:** 1

## Contexto

A Bronze guarda os arquivos da TLC como chegaram, em Parquet, numa tabela externa particionada por `year`/`month`. A Silver e a Gold são escritas pelo dbt e precisam de:

1. **Reprocessamento idempotente por mês:** quando a TLC republica um arquivo, o mês inteiro é substituído sem duplicar linhas (spec 6.3).
2. **Leitura consistente durante a escrita:** quem consulta (Power BI, agente de IA) nunca vê a tabela pela metade.
3. **Schema que muda com o tempo:** a TLC acrescenta colunas (ex.: `cbd_congestion_fee` desde 2025-01).
4. **Auditoria:** saber o que a tabela continha antes de um reprocessamento.

Parquet "solto" numa tabela Hive não atende os itens 1 e 2: não existe "apagar as linhas de janeiro"; seria preciso localizar e apagar arquivos à mão, e um leitor no meio do processo veria dados faltando.

## Decisão

A Silver e a Gold são **tabelas Apache Iceberg** no Glue Data Catalog, escritas pelo dbt-athena (`table_type='iceberg'` como padrão do projeto). A Bronze continua como **tabela externa** de Parquet.

## Evidências da Fase 1

| Comportamento | Evidência |
|---|---|
| Commit atômico + delete por condição | `delete` do mês + `append` (ADR 0014): a segunda execução manteve 20.405.666 linhas. Três snapshots registrados: `append` → `delete` (0 linhas) → `append` |
| Time travel | `FOR TIMESTAMP AS OF TIMESTAMP '2026-10-15 03:05:45 UTC'` devolveu 0 linhas: o instante entre o `delete` e o `append`. Time travel só lê; tornar uma versão vigente é rollback |
| Janela entre dois commits | 46 s sem o mês entre o `delete` e o `append` (são dois commits, não um) |
| Arquivos antigos continuam no S3 | A pasta `data/` da Silver passou de 499 MB para 1.015,6 MB: os arquivos do primeiro snapshot seguem referenciados pelo histórico. Exige `VACUUM` periódico |
| Tabela gerenciada: `DROP TABLE` apaga os dados | No Athena, uma tabela Iceberg é dona dos seus arquivos; diferente da Bronze externa, em que o `DROP` remove só a definição |
| Materialização `table` em Iceberg | O dbt-athena cria a tabela nova e troca o nome (sem janela sem dados na Gold). Exige caminho único por versão: `s3_data_naming: schema_table_unique` na pasta `marts` |
| Evolução de schema | `cbd_congestion_fee` existe em 2025-01 e não em 2024-01; no Iceberg, acrescentar a coluna não reescreve arquivos antigos (verificado só no schema dos arquivos; o backfill com meses de 2024 é da Fase 2) |

## Divergência com a spec

A spec (seção 4) cita **"overwrite por partição"** entre os motivos para o Iceberg. O formato oferece isso, mas o **dbt-athena 1.11.1 não expõe `insert_overwrite` para Iceberg**. A idempotência foi obtida com `append` + delete do mês (ADR 0014). A decisão pelo Iceberg não muda; muda só o mecanismo.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Parquet em tabela Hive (externa ou CTAS)** | Sem delete por condição nem commit atômico: reprocessar um mês exige apagar arquivos à mão, e leitores veem estados intermediários. A Bronze usa esse formato porque é só acrescentada |
| **Delta Lake** | Mesma proposta (é o formato do Fabric). No Athena, a escrita em Delta não é suportada (⚠️ não verificado nesta fase); o dbt-athena trabalha com Hive e Iceberg |
| **Apache Hudi** | Suporte no Athena mais limitado e menor adoção no ecossistema dbt (percepção do autor, não verificada) |

## Consequências

**Ganhamos:**
- Reprocessamento idempotente por `source_month`.
- Leitores sempre veem uma versão inteira da tabela.
- Histórico de versões para auditoria (snapshots e time travel).
- Formato aberto e neutro de fornecedor, lido por Athena, Spark, Trino, Snowflake e outros.

**Perdemos / cuidados:**
- `DROP TABLE` apaga os dados: nunca usá-lo "para recriar a definição" na Silver ou na Gold.
- Arquivos de versões antigas se acumulam no S3: `OPTIMIZE` e `VACUUM` entram na Fase 3.
- O incremental depende de dois commits (delete + append), com alguns segundos sem o mês: o Power BI atualiza depois do `dbt build`.
- Comportamento do adaptador (estratégias, nomes de caminho) precisa ser testado a cada atualização do dbt-athena.
