-- Manifesto de ingestão (Fase 2, etapa 3a).
-- Decisões: D4 (banco controle, prefixo controle/), D5 (só INSERT; a versão vigente é calculada
-- pela view, nunca gravada), D7 (arquivo fora do contrato entra com status 'rejeitado').
--
-- __BANCO__ é trocado na execução: controle (produção) ou teste_controle (ambiente de teste).
-- Rodar no workgroup rideshare. Idempotente: pode rodar de novo sem efeito.

-- 1) A tabela: livro de registro só de acréscimo (Iceberg).
--    Uma linha por versão de arquivo que passou pela ingestão, aceita ou rejeitada.
CREATE TABLE IF NOT EXISTS __BANCO__.ingestion_manifest (
  source          string    COMMENT 'Fonte: tlc_hvfhv | open_meteo',
  source_month    string    COMMENT 'Mês de referência do dado, YYYY-MM',
  source_url      string    COMMENT 'URL baixada',
  etag            string    COMMENT 'Cabeçalho ETag da fonte no momento da ingestão (opaco: só igualdade)',
  last_modified   timestamp COMMENT 'Cabeçalho Last-Modified da fonte, em UTC',
  content_length  bigint    COMMENT 'Tamanho em bytes informado pela fonte',
  file_sha256     string    COMMENT 'Hash SHA-256 do arquivo baixado: a prova do conteúdo',
  row_count       bigint    COMMENT 'Linhas no arquivo (lidas do rodapé do Parquet)',
  schema_hash     string    COMMENT 'Hash da lista nome:tipo das colunas (contrato de schema)',
  s3_path         string    COMMENT 'Caminho completo do arquivo gravado na Bronze',
  ingest_ts       string    COMMENT 'Versão: YYYYMMDDTHHMMSS em UTC, igual ao nome da pasta',
  status          string    COMMENT 'aceito | rejeitado (outros valores podem surgir na etapa 5)',
  motivo          string    COMMENT 'Por que foi rejeitado, ou observação (ex.: coluna nova)',
  registrado_em   timestamp COMMENT 'Quando esta linha foi gravada, em UTC',
  dag_run_id      string    COMMENT 'Linhagem: qual execução do Airflow gravou (ou manual__...)'
)
LOCATION 's3://rmartins-rideshare-lake/__BANCO__/ingestion_manifest/'
TBLPROPERTIES (
  'table_type' = 'ICEBERG',
  'format' = 'parquet',
  -- Time travel de 90 dias depois de um VACUUM (a tabela é minúscula; a rede de segurança é longa)
  'vacuum_max_snapshot_age_seconds' = '7776000'
);

-- 2) A view: a versão vigente de cada mês de cada fonte.
--    Vigente = a versão ACEITA mais recente. Rejeitadas nunca entram.
--    É daqui que a Silver tira o ingest_ts que precisa escrever no SQL (D6).
CREATE OR REPLACE VIEW __BANCO__.manifesto_vigente AS
SELECT
  source,
  source_month,
  ingest_ts,
  s3_path,
  etag,
  file_sha256,
  row_count,
  schema_hash,
  registrado_em
FROM (
  SELECT
    m.*,
    row_number() OVER (
      PARTITION BY source, source_month
      ORDER BY ingest_ts DESC
    ) AS ordem
  FROM __BANCO__.ingestion_manifest AS m
  WHERE status = 'aceito'
)
WHERE ordem = 1;
