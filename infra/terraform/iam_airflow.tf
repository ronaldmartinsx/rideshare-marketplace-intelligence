# Política de permissões do Airflow (menor privilégio).
# Criada SOLTA: ainda não está ligada a nenhuma identidade (decisão da Aula 6).
# Layout de dev no S3: ver ADR 0013.

locals {
  # Prefixos onde o dbt grava, reescreve e apaga (prod e dev).
  # Regra do ADR 0013: prefixo no S3 = nome do banco no Glue.
  prefixos_dbt = ["silver", "gold", "dev_silver", "dev_gold"]

  glue_catalogo = "arn:aws:glue:${local.regiao}:${local.conta_id}:catalog"
  glue_bancos   = [for banco in local.bancos_glue : "arn:aws:glue:${local.regiao}:${local.conta_id}:database/${banco}"]
  glue_tabelas  = [for banco in local.bancos_glue : "arn:aws:glue:${local.regiao}:${local.conta_id}:table/${banco}/*"]
}

resource "aws_iam_policy" "airflow" {
  name        = "rideshare-airflow"
  description = "Permissões do Airflow: ingestão na Bronze, dbt via Athena e catálogo do Glue."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ---------- Bucket do lake ----------
      {
        # Ações sobre o BUCKET: ARN sem /*
        Sid      = "LakeListarBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:GetBucketLocation"]
        Resource = [aws_s3_bucket.datalake.arn]
      },
      {
        # Bronze imutável: grava arquivo novo, nunca apaga (ADR 0003)
        Sid      = "BronzeLerEGravarSemApagar"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"]
        Resource = ["${aws_s3_bucket.datalake.arn}/bronze/*"]
      },
      {
        # dbt reescreve tabelas e apaga temporárias na Silver e na Gold
        Sid      = "SilverGoldLerGravarApagar"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload"]
        Resource = [for prefixo in local.prefixos_dbt : "${aws_s3_bucket.datalake.arn}/${prefixo}/*"]
      },

      # ---------- Bucket de resultados do Athena ----------
      {
        Sid      = "ResultadosAthenaListarBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:GetBucketLocation", "s3:ListBucketMultipartUploads"]
        Resource = [aws_s3_bucket.athena_results.arn]
      },
      {
        # Sem DeleteObject: quem limpa é a regra de ciclo de vida
        Sid      = "ResultadosAthenaLerEGravar"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"]
        Resource = ["${aws_s3_bucket.athena_results.arn}/*"]
      },

      # ---------- Athena: só pelo workgroup do projeto ----------
      {
        Sid    = "AthenaConsultasNoWorkgroup"
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution",
          "athena:GetWorkGroup",
        ]
        Resource = [aws_athena_workgroup.rideshare.arn]
      },

      # ---------- Glue: só os 6 bancos do projeto ----------
      {
        # Mexer numa tabela exige permissão nos 3 níveis: catálogo, banco e tabela
        Sid    = "GlueTabelasDoProjeto"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:CreateTable",
          "glue:UpdateTable",
          "glue:DeleteTable",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:BatchCreatePartition",
          "glue:BatchDeletePartition",
        ]
        Resource = concat([local.glue_catalogo], local.glue_bancos, local.glue_tabelas)
      },
    ]
  })
}
