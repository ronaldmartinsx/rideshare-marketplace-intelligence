-- Arquivos da "TLC de mentira" (Fase 2, etapa 8), gerados a partir do arquivo real de 2025-01.
-- Cada arquivo tem 1.000 corridas reais, com o MESMO schema da TLC (colunas, tipos, maiúsculas).
--
-- Uso, a partir da raiz do repositório:
--   duckdb < scripts/fase-2/gerar_amostra.sql
-- Pré-requisito: data/tlc_hvfhv/fhvhv_tripdata_2025-01.parquet (baixado na Fase 1, fora do Git).
-- Saída: data/tlc_de_mentira/ (fora do Git)
--   trip-data/  o que o servidor publica (o nginx serve esta pasta)
--   estoque/    versões alternativas, trocadas à mão em cada cenário do teste

SET enable_progress_bar = false;
SET VARIABLE origem = 'data/tlc_hvfhv/fhvhv_tripdata_2025-01.parquet';

-- Publicados no início: três meses, cada um com corridas diferentes (conteúdos diferentes)
COPY (SELECT * FROM read_parquet(getvariable('origem')) LIMIT 1000 OFFSET 0)
  TO 'data/tlc_de_mentira/trip-data/fhvhv_tripdata_2026-06.parquet' (FORMAT parquet);
COPY (SELECT * FROM read_parquet(getvariable('origem')) LIMIT 1000 OFFSET 1000)
  TO 'data/tlc_de_mentira/trip-data/fhvhv_tripdata_2026-07.parquet' (FORMAT parquet);
COPY (SELECT * FROM read_parquet(getvariable('origem')) LIMIT 1000 OFFSET 2000)
  TO 'data/tlc_de_mentira/trip-data/fhvhv_tripdata_2026-08.parquet' (FORMAT parquet);

-- Republicação de 2026-07: outras corridas (conteúdo novo, mesmo schema)
COPY (SELECT * FROM read_parquet(getvariable('origem')) LIMIT 1000 OFFSET 5000)
  TO 'data/tlc_de_mentira/estoque/republicacao_2026-07.parquet' (FORMAT parquet);

-- 2026-08 fora do contrato: trip_miles como TEXTO (pergunta 1b da Aula 4)
COPY (
  SELECT * REPLACE (CAST(trip_miles AS VARCHAR) AS trip_miles)
  FROM read_parquet(getvariable('origem')) LIMIT 1000 OFFSET 2000
) TO 'data/tlc_de_mentira/estoque/fora_do_contrato_2026-08.parquet' (FORMAT parquet);

-- Conferência
SELECT 'trip-data' AS pasta, count(*) AS arquivos FROM glob('data/tlc_de_mentira/trip-data/*.parquet')
UNION ALL
SELECT 'estoque', count(*) FROM glob('data/tlc_de_mentira/estoque/*.parquet');
