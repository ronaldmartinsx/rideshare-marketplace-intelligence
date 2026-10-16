-- Inspeção de um arquivo Parquet da TLC com DuckDB (Fase 1, Aula 7).
-- Lê só o rodapé (metadados): não carrega as linhas.
--
-- Uso, a partir da raiz do repositório:
--   duckdb < scripts/fase-1/inspecao_parquet.sql
--
-- Pré-requisito: o arquivo baixado em data/tlc_hvfhv/ (fora do Git).

SET enable_progress_bar = false;
SET VARIABLE arquivo = 'data/tlc_hvfhv/fhvhv_tripdata_2025-01.parquet';

.print '=== 1. Visão geral (rodapé) ==='
SELECT num_rows       AS linhas,
       num_row_groups AS row_groups,
       format_version,
       created_by
FROM parquet_file_metadata(getvariable('arquivo'));

.print '=== 2. Compressão e tamanho por coluna (soma dos row groups) ==='
SELECT path_in_schema                                                     AS coluna,
       any_value(compression)                                             AS compressao,
       round(sum(total_compressed_size) / 1048576, 1)                     AS mb_comprimido,
       round(sum(total_uncompressed_size) / 1048576, 1)                   AS mb_original,
       round(sum(total_uncompressed_size) / sum(total_compressed_size), 1) AS taxa
FROM parquet_metadata(getvariable('arquivo'))
GROUP BY path_in_schema
ORDER BY mb_comprimido DESC;

.print '=== 3. Min/max de pickup_datetime por row group (o predicate pushdown funciona?) ==='
SELECT row_group_id       AS rg,
       row_group_num_rows AS linhas,
       stats_min          AS pickup_min,
       stats_max          AS pickup_max
FROM parquet_metadata(getvariable('arquivo'))
WHERE path_in_schema = 'pickup_datetime'
ORDER BY row_group_id;
