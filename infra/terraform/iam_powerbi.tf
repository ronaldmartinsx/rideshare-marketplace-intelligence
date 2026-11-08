# Identidade de leitura do Power BI (Fase 4, decisões P1 a P4; spec 11.5):
#   usuário do Identity Center --atribuição--> permission set RideshareLeituraGold --> política abaixo
# O Power BI Desktop entra pelo driver ODBC com "Browser SSO OIDC" (navegador + MFA, credencial
# temporária): nenhuma chave fica guardada no Windows. O Role name do DSN passa a ser o nome
# deste permission set, no lugar do AdministratorAccess usado na Fase 1.
# O AdministratorAccess foi criado no console (Fase 0) e não é gerenciado aqui.

# Data sources: leem o Identity Center, não criam nada (sem IDs escritos no código)
data "aws_ssoadmin_instances" "atual" {}

data "aws_identitystore_user" "powerbi" {
  identity_store_id = tolist(data.aws_ssoadmin_instances.atual.identity_store_ids)[0]

  alternate_identifier {
    unique_attribute {
      attribute_path  = "UserName"
      attribute_value = var.usuario_identity_center
    }
  }
}

locals {
  sso_instancia = tolist(data.aws_ssoadmin_instances.atual.arns)[0]
}

# ---------- Permission set: o molde do papel "Visualizador" ----------
resource "aws_ssoadmin_permission_set" "leitura_gold" {
  name         = "RideshareLeituraGold"
  description  = "Somente leitura da Gold de producao pelo workgroup rideshare-bi (Power BI)."
  instance_arn = local.sso_instancia

  # 8 horas: um dia de trabalho sem o navegador pedir login de novo (decisão P4)
  session_duration = "PT8H"
}

resource "aws_ssoadmin_permission_set_inline_policy" "leitura_gold" {
  instance_arn       = local.sso_instancia
  permission_set_arn = aws_ssoadmin_permission_set.leitura_gold.arn

  inline_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ---------- Bucket do lake: só a Gold, só leitura ----------
      {
        Sid      = "LakeLocalizarBucket"
        Effect   = "Allow"
        Action   = ["s3:GetBucketLocation"]
        Resource = [aws_s3_bucket.datalake.arn]
      },
      {
        # Listar o bucket, mas só debaixo de gold/ (a Bronze e a Silver nem aparecem)
        Sid       = "LakeListarSoAGold"
        Effect    = "Allow"
        Action    = ["s3:ListBucket"]
        Resource  = [aws_s3_bucket.datalake.arn]
        Condition = { StringLike = { "s3:prefix" = ["gold/*"] } }
      },
      {
        Sid      = "GoldLer"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["${aws_s3_bucket.datalake.arn}/gold/*"]
      },

      # ---------- Bucket de resultados: a única escrita, e só em bi/ ----------
      {
        Sid      = "ResultadosListarBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:GetBucketLocation", "s3:ListBucketMultipartUploads"]
        Resource = [aws_s3_bucket.athena_results.arn]
      },
      {
        # O Athena grava o CSV do resultado com a credencial de quem consulta
        Sid      = "ResultadosBiLerEGravar"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"]
        Resource = ["${aws_s3_bucket.athena_results.arn}/bi/*"]
      },

      # ---------- Athena: só pelo workgroup do Power BI ----------
      {
        Sid    = "AthenaConsultasNoWorkgroupBi"
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          # O driver ODBC 2.x pode buscar o resultado por streaming em vez do CSV no S3
          "athena:GetQueryResultsStream",
          "athena:StopQueryExecution",
          "athena:GetWorkGroup",
        ]
        Resource = [aws_athena_workgroup.bi.arn]
      },
      {
        # O navegador do Power BI lista bancos e tabelas pela API do Athena
        Sid    = "AthenaMetadadosDoCatalogo"
        Effect = "Allow"
        Action = [
          "athena:GetDataCatalog",
          "athena:ListDatabases",
          "athena:GetDatabase",
          "athena:ListTableMetadata",
          "athena:GetTableMetadata",
        ]
        Resource = ["arn:aws:athena:${local.regiao}:${local.conta_id}:datacatalog/AwsDataCatalog"]
      },

      # ---------- Glue: só o banco gold, só leitura ----------
      {
        # Ler uma tabela exige permissão nos 3 níveis: catálogo, banco e tabela
        Sid    = "GlueLerAGold"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:BatchGetPartition",
        ]
        Resource = [
          local.glue_catalogo,
          "arn:aws:glue:${local.regiao}:${local.conta_id}:database/gold",
          "arn:aws:glue:${local.regiao}:${local.conta_id}:table/gold/*",
        ]
      },
    ]
  })
}

# ---------- Atribuição: quem (usuário) + o quê (permission set) + onde (esta conta) ----------
# Ao ser criada, o Identity Center gera na conta a role AWSReservedSSO_RideshareLeituraGold_...
resource "aws_ssoadmin_account_assignment" "powerbi" {
  instance_arn       = local.sso_instancia
  permission_set_arn = aws_ssoadmin_permission_set.leitura_gold.arn

  principal_type = "USER"
  principal_id   = data.aws_identitystore_user.powerbi.user_id

  target_type = "AWS_ACCOUNT"
  target_id   = local.conta_id
}
