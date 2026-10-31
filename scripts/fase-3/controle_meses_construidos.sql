-- Registro de construção do dbt (Fase 3, etapa 8, decisão B1).
-- A dbt_mes grava uma linha SÓ quando o mês inteiro termina verde (Silver, gate e Gold), com as
-- versões lidas da própria Silver (o que foi construído de fato).
-- Mês pendente = a versão vigente no manifesto é diferente da última construção registrada.
-- Mesmo padrão do manifesto (Fase 2, D5): só INSERT; a última construção é calculada pela view.
--
-- Fica no banco controle (produção), com a coluna ambiente separando dev e prod do dbt.
-- Rodar no workgroup rideshare. Idempotente: pode rodar de novo sem efeito.

-- 1) A tabela: livro de registro só de acréscimo (Iceberg).
--    Uma linha por mês construído com sucesso, em cada ambiente.
CREATE TABLE IF NOT EXISTS controle.dbt_meses_construidos (
  ambiente         string    COMMENT 'Ambiente do dbt: dev (dev_silver/dev_gold) | prod (silver/gold)',
  source_month     string    COMMENT 'Mês construído, YYYY-MM',
  ingest_ts_tlc    string    COMMENT 'Versão da TLC que a Silver usou (max ingest_ts da staging no mês)',
  ingest_ts_clima  string    COMMENT 'Versão do clima que a Silver usou (max ingest_ts da staging no mês)',
  motivo           string    COMMENT 'manifesto (versão nova na Bronze) | forcado (código do dbt mudou) | manual',
  construido_em    timestamp COMMENT 'Quando a construção terminou, em UTC',
  dag_run_id       string    COMMENT 'Linhagem: qual execução da dbt_mes construiu e gravou'
)
LOCATION 's3://rmartins-rideshare-lake/controle/dbt_meses_construidos/'
TBLPROPERTIES (
  'table_type' = 'ICEBERG',
  'format' = 'parquet',
  -- Time travel de 90 dias depois de um VACUUM, como o manifesto (tabela minúscula)
  'vacuum_max_snapshot_age_seconds' = '7776000'
);

-- 2) A view: a última construção de cada mês em cada ambiente.
--    A dbt_build compara esta view com a manifesto_vigente para achar os meses pendentes.
CREATE OR REPLACE VIEW controle.dbt_meses_construidos_vigente AS
SELECT
  ambiente,
  source_month,
  ingest_ts_tlc,
  ingest_ts_clima,
  motivo,
  construido_em,
  dag_run_id
FROM (
  SELECT
    c.*,
    row_number() OVER (
      PARTITION BY ambiente, source_month
      ORDER BY construido_em DESC
    ) AS ordem
  FROM controle.dbt_meses_construidos AS c
)
WHERE ordem = 1;
