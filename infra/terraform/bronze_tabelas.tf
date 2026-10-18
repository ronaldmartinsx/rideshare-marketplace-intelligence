# Tabelas externas da Bronze da TLC (Fase 2, decisão D6; ADR 0015).
# A de produção foi criada à mão na Fase 1 (scripts/fase-1/bronze_tlc_hvfhv.sql) e entra
# no Terraform por import: o Terraform passa a "adotar" a tabela existente, sem recriá-la.
# A de teste é nova e idêntica, apontando para teste_bronze/ (etapa 8).
# Externa: o catálogo só aponta para os arquivos. Apagar a tabela não apaga nenhum arquivo.

import {
  to = aws_glue_catalog_table.tlc_hvfhv["bronze"]
  # catálogo:banco:tabela. O ID da conta vem do data source (repositório público).
  id = "${local.conta_id}:bronze:tlc_hvfhv"
}

locals {
  # Banco do Glue → prefixo no S3 (regra do ADR 0013: mesmo nome)
  bancos_bronze_tlc = toset(["bronze", "teste_bronze"])

  # Mesma ordem e tipos do DDL da Fase 1 (conferidos contra o arquivo real, validação da Fase 1)
  colunas_tlc_hvfhv = [
    ["hvfhs_license_num", "string"],
    ["dispatching_base_num", "string"],
    ["originating_base_num", "string"],
    ["request_datetime", "timestamp"],
    ["on_scene_datetime", "timestamp"],
    ["pickup_datetime", "timestamp"],
    ["dropoff_datetime", "timestamp"],
    ["pulocationid", "int"],
    ["dolocationid", "int"],
    ["trip_miles", "double"],
    ["trip_time", "bigint"],
    ["base_passenger_fare", "double"],
    ["tolls", "double"],
    ["bcf", "double"],
    ["sales_tax", "double"],
    ["congestion_surcharge", "double"],
    ["airport_fee", "double"],
    ["tips", "double"],
    ["driver_pay", "double"],
    ["shared_request_flag", "string"],
    ["shared_match_flag", "string"],
    ["access_a_ride_flag", "string"],
    ["wav_request_flag", "string"],
    ["wav_match_flag", "string"],
    ["cbd_congestion_fee", "double"],
  ]
}

resource "aws_glue_catalog_table" "tlc_hvfhv" {
  for_each = local.bancos_bronze_tlc

  database_name = aws_glue_catalog_database.camadas[each.key].name
  name          = "tlc_hvfhv"
  table_type    = "EXTERNAL_TABLE"

  # Valor padrão que o Athena grava ao criar tabela por DDL (Fase 1). Declarado igual
  # para o import não "corrigir" nada além da projection.
  owner = "hadoop"

  parameters = {
    EXTERNAL = "TRUE"

    # Partition projection: o Athena calcula as partições pelas regras abaixo,
    # em vez de pedir a lista ao Glue. Ligada, ela IGNORA as partições registradas.
    "projection.enabled" = "true"

    # year: de 2024 até o ano corrente (NOW é calculado em UTC, na hora da consulta)
    "projection.year.type"          = "date"
    "projection.year.format"        = "yyyy"
    "projection.year.range"         = "2024,NOW"
    "projection.year.interval"      = "1"
    "projection.year.interval.unit" = "YEARS"

    # month: os 12 meses com zero à esquerda, como nas pastas (month=01)
    "projection.month.type"   = "enum"
    "projection.month.values" = "01,02,03,04,05,06,07,08,09,10,11,12"

    # ingest_ts: imprevisível. Toda consulta TEM que informar qual versão quer,
    # senão falha: ler duas versões do mesmo mês sem querer fica impossível (D6).
    "projection.ingest_ts.type" = "injected"

    # Onde fica cada partição. $${...} escreve ${...} literal (sem o Terraform interpretar).
    "storage.location.template" = "s3://${aws_s3_bucket.datalake.bucket}/${each.key}/tlc_hvfhv/year=$${year}/month=$${month}/ingest_ts=$${ingest_ts}/"
  }

  partition_keys {
    name = "year"
    type = "string"
  }

  partition_keys {
    name = "month"
    type = "string"
  }

  partition_keys {
    name = "ingest_ts"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.datalake.bucket}/${each.key}/tlc_hvfhv"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    # Padrão do DDL do Athena ("sem buckets"), declarado pelo mesmo motivo do owner
    number_of_buckets = -1

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      parameters = {
        "serialization.format" = "1"
      }
    }

    dynamic "columns" {
      for_each = local.colunas_tlc_hvfhv

      content {
        name = columns.value[0]
        type = columns.value[1]
      }
    }
  }

  lifecycle {
    # Diferenças que não são configuração nossa; sem estas linhas, todo plan mostraria "mudanças" falsas:
    # - carimbo que o Glue atualiza sozinho a cada alteração;
    # - bloco "skew" vazio, que o DDL do Athena grava (produção) e a API não grava (teste).
    ignore_changes = [
      parameters["transient_lastDdlTime"],
      storage_descriptor[0].skewed_info,
    ]
  }
}
