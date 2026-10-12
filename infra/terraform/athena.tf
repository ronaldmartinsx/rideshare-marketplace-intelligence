# ---------------------------------------------------------------
# Bucket de resultados do Athena
# Toda consulta grava seu resultado (CSV) aqui. É dado descartável:
# sem versionamento (de propósito) e com expiração automática.
# ---------------------------------------------------------------
resource "aws_s3_bucket" "athena_results" {
  bucket = "${var.prefixo}-athena-results"
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Apaga resultados com mais de 7 dias; sem isso o bucket só cresce
resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    id     = "expira-resultados-antigos"
    status = "Enabled"

    filter {}

    expiration {
      days = 7
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# ---------------------------------------------------------------
# Workgroup principal: regras aplicadas a toda consulta feita por ele
# ---------------------------------------------------------------
resource "aws_athena_workgroup" "rideshare" {
  name        = "rideshare"
  description = "Workgroup principal do projeto (dbt, Airflow, consultas de desenvolvimento)"

  configuration {
    # Quem usa o workgroup não pode trocar estas regras na própria consulta
    enforce_workgroup_configuration = true

    # Freio de mão: consulta que tentar ler mais que isso é cancelada
    bytes_scanned_cutoff_per_query = var.athena_limite_bytes_por_consulta

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/resultados/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}
