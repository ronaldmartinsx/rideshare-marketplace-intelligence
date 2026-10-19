# ADR 0015: Leitura da Bronze por partition projection, com a versão obrigatória na consulta

- **Status:** Decidido e validado na Fase 2 (decisão D6; etapas 1 e 10)
- **Data:** 18/10/2026
- **Fase:** 2

## Contexto

A Bronze é particionada por `year`, `month` e `ingest_ts` (ADR 0003). Na Fase 1, cada partição nova precisava ser registrada à mão no Glue (`ALTER TABLE ... ADD PARTITION`). Sem o registro, a pasta fica invisível e a consulta devolve **zero linhas, sem erro**. Com cerca de 32 meses, republicações e o clima, o registro manual não escala.

Havia um segundo problema, mais grave: a Silver filtrava só `year` e `month`. Quando um mês tivesse duas versões na Bronze (republicação), ela leria **as duas** e dobraria as corridas, em silêncio.

## Decisão

As tabelas `bronze.tlc_hvfhv` e `bronze.open_meteo` (e as de `teste_bronze`) usam **partition projection** do Athena, declarada no Terraform (`infra/terraform/bronze_tabelas.tf`):

| Partição | Tipo de projection | Regra |
|---|---|---|
| `year` | `date` | `yyyy`, de 2024 até `NOW` (o ano novo entra sozinho) |
| `month` | `enum` | `01` a `12` |
| `ingest_ts` | **`injected`** | Imprevisível: **a consulta é obrigada a informar o valor** |

Toda leitura da Bronze precisa dizer qual versão quer. A Silver tira essa versão do manifesto pela macro `ingest_ts_vigente` (dbt), que consulta `controle.manifesto_vigente` **antes** e escreve o valor literal no SQL. Sem versão vigente para o mês: erro de compilação, antes de qualquer leitura.

A tabela `bronze.tlc_hvfhv`, criada à mão na Fase 1, foi **adotada** pelo Terraform (bloco `import`) sem ser recriada.

## Evidência (etapas 1 e 10)

| Consulta | Resultado |
|---|---|
| Sem filtro de `ingest_ts` | `CONSTRAINT_VIOLATION: ... the WHERE clause must contain only static equality conditions` |
| Com a versão da Fase 1 | 20.405.666 corridas (0 bytes lidos: a contagem vem do rodapé do Parquet) |
| Com uma versão inexistente | 0, sem erro (o "zero silencioso") |
| `dbt compile` para um mês sem versão vigente | Erro de compilação com a explicação |
| `dbt build` da Silver e da Gold em dev | 20.405.666 corridas na versão vigente; Gold com 364.630 linhas, igual à Fase 1 |

A expressão "static equality" responde uma dúvida anotada na decisão: o valor do `ingest_ts` precisa estar **escrito** no SQL; uma subconsulta ao manifesto não é aceita.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Partições tradicionais, registradas por uma task da DAG | Mais uma peça para falhar; e ler só a versão vigente seria uma **convenção** (lembrar o filtro), não uma regra imposta |
| `MSCK REPAIR TABLE` (varrer as pastas) | Lento com muitas pastas e ainda exige alguém para rodá-lo; não resolve as duas versões |
| `ingest_ts` como `date` na projection | Precisão de segundos: milhões de partições candidatas, quase todas vazias (a documentação recomenda partições tradicionais quando mais da metade está vazia) |
| Mudar o layout da Bronze (sem `ingest_ts` no caminho) | Contradiz o ADR 0003 (uma pasta por versão) |

## Consequências

**Ganhamos:**
- Pasta nova visível sem registro manual nem permissão de Glue para isso.
- **Ler duas versões do mesmo mês sem querer ficou impossível**: o erro mais perigoso da fase virou um erro alto.
- A Silver registra de qual versão veio cada linha (`ingest_ts`): linhagem até o manifesto.

**Perdemos / cuidados:**
- A projection **ignora** as partições registradas no Glue; a partição manual da Fase 1 continua lá, sem efeito (o caminho dela bate com o molde).
- **`SHOW PARTITIONS` não mostra as partições projetadas**: a conferência usada na Fase 1 deixa de servir. Use o manifesto.
- Valor fora da faixa, ou versão sem pasta, devolve **zero linhas sem erro**. A macro do dbt evita isso na Silver; consultas manuais precisam do `ingest_ts` certo.
- Só vale no Athena (Spark, EMR e Redshift Spectrum usariam a lista do Glue). Aceitável: o dbt-athena roda no Athena.
- O `NOW` da faixa de anos é calculado em UTC (irrelevante para a granularidade de ano).
- A Silver passou a processar **um mês por vez** também na primeira construção (o filtro deixou de estar dentro do `is_incremental()`). Montar os ~32 meses é papel da DAG `dbt_build` (Fase 3). Isso atualiza a última consequência do ADR 0014.
