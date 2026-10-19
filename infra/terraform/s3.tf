resource "aws_s3_bucket" "datalake" {
  bucket = "${var.prefixo}-lake"
}

resource "aws_s3_bucket_versioning" "datalake" {
  bucket = aws_s3_bucket.datalake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "datalake" {
  bucket = aws_s3_bucket.datalake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------
# Bronze imutável garantida pelo armazenamento (ADR 0003, decisão D3 da Fase 2)
# Gravar só é aceito com o cabeçalho If-None-Match: o S3 recusa (412) se o caminho
# já existir. Vale para QUALQUER identidade, inclusive administradores.
# Modelo: exemplo oficial da AWS "Enforce conditional writes on Amazon S3 buckets".
# ---------------------------------------------------------------
locals {
  prefixos_imutaveis = ["bronze", "teste_bronze"]
}

resource "aws_s3_bucket_policy" "datalake" {
  bucket = aws_s3_bucket.datalake.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "BronzeSoGravaSeOCaminhoNaoExistir"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = [for prefixo in local.prefixos_imutaveis : "${aws_s3_bucket.datalake.arn}/${prefixo}/*"]
        Condition = {
          # Nega quando o cabeçalho If-None-Match NÃO veio...
          Null = { "s3:if-none-match" = "true" }
          # ...numa operação que cria o objeto (PutObject ou CompleteMultipartUpload).
          # As partes de um upload em partes (UploadPart) não aceitam o cabeçalho e ficam liberadas.
          Bool = { "s3:ObjectCreationOperation" = "true" }
        }
      },
    ]
  })
}

# ---------------------------------------------------------------
# Ciclo de vida do lake (decisão D11 da Fase 2)
# Com versionamento ligado, "apagar" um arquivo só esconde a versão: o espaço
# nunca é liberado. Estas regras limpam o que nenhuma tabela usa mais.
# A Bronze fica de fora de propósito: lá, nada expira.
# ---------------------------------------------------------------
resource "aws_s3_bucket_lifecycle_configuration" "datalake" {
  bucket = aws_s3_bucket.datalake.id

  # As regras de versões antigas dependem do versionamento já estar ligado
  depends_on = [aws_s3_bucket_versioning.datalake]

  # Pedaços de uploads em partes interrompidos ficam invisíveis e são cobrados
  rule {
    id     = "aborta-uploads-incompletos"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Uma regra por prefixo que reescreve ou apaga (dbt, manifesto, teste). Nunca a bronze/.
  dynamic "rule" {
    for_each = concat(local.prefixos_dbt, local.prefixos_controle_e_teste)

    content {
      id     = "expira-versoes-antigas-${rule.value}"
      status = "Enabled"

      filter {
        prefix = "${rule.value}/"
      }

      # Versão escondida (substituída ou "apagada") some 30 dias depois
      noncurrent_version_expiration {
        noncurrent_days = 30
      }

      # Remove a "marca de apagado" que sobra quando não há mais nenhuma versão por trás
      expiration {
        expired_object_delete_marker = true
      }
    }
  }
}

