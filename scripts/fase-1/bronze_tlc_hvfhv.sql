-- Tabela externa da Bronze sobre os arquivos HVFHV da TLC (Fase 1, fatia vertical).
-- Executar no Athena, pelo workgroup `rideshare`, um comando por vez.
-- Forma definitiva (Terraform ou dbt-external-tables + partition projection): decidir na Fase 2.

-- 1) A tabela. EXTERNAL + LOCATION: o catálogo só aponta; os arquivos pertencem à ingestão.
--    Tipos conferidos contra o arquivo real (docs/validacao/fase-1.md, seção 2).
--    cbd_congestion_fee só existe a partir de 2025: em meses anteriores, a leitura devolve NULL.
CREATE EXTERNAL TABLE IF NOT EXISTS bronze.tlc_hvfhv (
  hvfhs_license_num    string,
  dispatching_base_num string,
  originating_base_num string,
  request_datetime     timestamp,
  on_scene_datetime    timestamp,
  pickup_datetime      timestamp,
  dropoff_datetime     timestamp,
  pulocationid         int,
  dolocationid         int,
  trip_miles           double,
  trip_time            bigint,
  base_passenger_fare  double,
  tolls                double,
  bcf                  double,
  sales_tax            double,
  congestion_surcharge double,
  airport_fee          double,
  tips                 double,
  driver_pay           double,
  shared_request_flag  string,
  shared_match_flag    string,
  access_a_ride_flag   string,
  wav_request_flag     string,
  wav_match_flag       string,
  cbd_congestion_fee   double
)
PARTITIONED BY (year string, month string, ingest_ts string)
STORED AS PARQUET
LOCATION 's3://rmartins-rideshare-lake/bronze/tlc_hvfhv/';

-- 2) Registro manual da partição da ingestão de 12/10/2026 (sem isso, a pasta é invisível).
ALTER TABLE bronze.tlc_hvfhv ADD IF NOT EXISTS
  PARTITION (year = '2025', month = '01', ingest_ts = '20261012T230806')
  LOCATION 's3://rmartins-rideshare-lake/bronze/tlc_hvfhv/year=2025/month=01/ingest_ts=20261012T230806/';

-- 3) Conferência
SHOW PARTITIONS bronze.tlc_hvfhv;
