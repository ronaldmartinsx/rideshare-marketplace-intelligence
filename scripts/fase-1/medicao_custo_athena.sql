-- Experimento de custo no Athena (Fase 1, risco R1).
-- Rodar no editor do Athena, workgroup `rideshare`, UMA consulta por vez,
-- e anotar o "Data scanned" que aparece abaixo do resultado.
-- Resultados registrados em docs/validacao/fase-1.md.

-- 1) Contagem: o Parquet guarda o número de linhas no rodapé
SELECT count(*) AS corridas
FROM bronze.tlc_hvfhv;

-- 2) Uma coluna só (armazenamento colunar)
SELECT avg(trip_miles) AS milhas_media
FROM bronze.tlc_hvfhv;

-- 3) Duas colunas + filtro de data (predicate pushdown nos row groups)
SELECT avg(trip_miles) AS milhas_media
FROM bronze.tlc_hvfhv
WHERE pickup_datetime >= TIMESTAMP '2025-01-15 00:00:00';

-- 4) Todas as 25 colunas (o "arquivo inteiro", sem gerar 20 milhões de linhas de resultado)
SELECT max(hvfhs_license_num), max(dispatching_base_num), max(originating_base_num),
       max(request_datetime), max(on_scene_datetime), max(pickup_datetime), max(dropoff_datetime),
       max(pulocationid), max(dolocationid), max(trip_miles), max(trip_time),
       max(base_passenger_fare), max(tolls), max(bcf), max(sales_tax), max(congestion_surcharge),
       max(airport_fee), max(tips), max(driver_pay),
       max(shared_request_flag), max(shared_match_flag), max(access_a_ride_flag),
       max(wav_request_flag), max(wav_match_flag), max(cbd_congestion_fee)
FROM bronze.tlc_hvfhv;

-- 5) Partition pruning: a pasta year=2024 não existe nesta tabela
SELECT avg(trip_miles) AS milhas_media
FROM bronze.tlc_hvfhv
WHERE year = '2024';
