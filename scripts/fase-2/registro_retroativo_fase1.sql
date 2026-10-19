-- Registro retroativo da ingestão manual da Fase 1 no manifesto (Fase 2, etapa 3b).
-- O arquivo de 2025-01 foi baixado e enviado à mão em 12/10/2026, antes de o manifesto existir.
-- Sem esta linha, o primeiro run da tlc_ingest baixaria o mês de novo como se fosse inédito.
--
-- Origem de cada valor:
--   etag, last_modified, content_length: HEAD na TLC (conferido de novo em 17/10/2026, sem mudança)
--   file_sha256: docs/validacao/fase-1.md, seção 1
--   row_count, schema_hash: include/ingestao/contrato.py rodado sobre o arquivo real (contrato v1)
--   ingest_ts e s3_path: partição registrada na Fase 1 (scripts/fase-1/bronze_tlc_hvfhv.sql)
--
-- Rodar UMA vez, no workgroup rideshare. O manifesto é só de acréscimo: rodar de novo duplicaria a linha.

INSERT INTO controle.ingestion_manifest VALUES (
  'tlc_hvfhv',
  '2025-01',
  'https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_2025-01.parquet',
  '"82b3922bcddc3e88ef5b27d1329be178-94"',
  TIMESTAMP '2025-04-23 16:30:36',
  491076642,
  'fcdef276f4e9887f2beab30590165cdea74caef50a1313d71fa01ff6afacca3a',
  20405666,
  '6fa14a7ebfdefcc0a1264c379cd5c2db604fa89c948076af26621ce72bc6ea9c',
  's3://rmartins-rideshare-lake/bronze/tlc_hvfhv/year=2025/month=01/ingest_ts=20261012T230806/fhvhv_tripdata_2025-01.parquet',
  '20261012T230806',
  'aceito',
  'registro retroativo: ingestão manual da Fase 1 (12/10/2026)',
  CAST(current_timestamp AT TIME ZONE 'UTC' AS timestamp(6)),
  'manual__fase1'
);
