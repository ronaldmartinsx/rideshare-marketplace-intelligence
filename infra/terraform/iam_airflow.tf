# Identidade do Airflow na AWS (ADR 0008, decisão D8 da Fase 2):
#   usuário rideshare-airflow-local (chave de acesso) --assume--> role rideshare-airflow --> política abaixo
# O usuário não tem permissão nenhuma além de assumir a role. A chave é criada fora do Terraform
# (pelo terminal), para o segredo não ficar gravado no estado.
# Layout de dev no S3: ver ADR 0013.

locals {
  # Prefixos onde o dbt grava, reescreve e apaga (prod e dev).
  # Regra do ADR 0013: prefixo no S3 = nome do banco no Glue.
  prefixos_dbt = ["silver", "gold", "dev_silver", "dev_gold"]

  # Prefixos do manifesto (Iceberg: a manutenção apaga arquivos) e do ambiente de teste
  # (o teste precisa ser limpo). A Bronze de produção fica fora desta lista: nunca apaga.
  prefixos_controle_e_teste = ["controle", "teste_bronze", "teste_controle"]

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
      {
        # Manifesto (Iceberg) e ambiente de teste: ler, gravar e apagar
        Sid      = "ControleETesteLerGravarApagar"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload"]
        Resource = [for prefixo in local.prefixos_controle_e_teste : "${aws_s3_bucket.datalake.arn}/${prefixo}/*"]
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

# ---------- Role: o "cargo" que o Airflow exerce ----------
# Só o usuário do Airflow pode assumi-la (trust policy). Num Airflow gerenciado (MWAA, Astro),
# esta mesma role seria a role de execução, sem chave nenhuma.
resource "aws_iam_role" "airflow" {
  name        = "rideshare-airflow"
  description = "Role assumida pelo Airflow local para ingestão e dbt."

  # Credencial temporária gerada ao assumir a role vale 1 hora (o provider renova sozinho)
  max_session_duration = 3600

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "SoOUsuarioDoAirflowAssume"
        Effect    = "Allow"
        Principal = { AWS = aws_iam_user.airflow_local.arn }
        Action    = "sts:AssumeRole"
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "airflow" {
  role       = aws_iam_role.airflow.name
  policy_arn = aws_iam_policy.airflow.arn
}

# ---------- Usuário: a identidade com chave, que só sabe "vestir o crachá" ----------
resource "aws_iam_user" "airflow_local" {
  name = "rideshare-airflow-local"
  path = "/servicos/"
}

resource "aws_iam_user_policy" "airflow_local_so_assume" {
  name = "so-assume-a-role-do-airflow"
  user = aws_iam_user.airflow_local.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AssumirSoARoleDoAirflow"
        Effect   = "Allow"
        Action   = "sts:AssumeRole"
        Resource = aws_iam_role.airflow.arn
      },
    ]
  })
}
