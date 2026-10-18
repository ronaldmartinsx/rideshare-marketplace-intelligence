# Bancos do Glue Data Catalog: agrupamentos lógicos de tabelas (equivalem a schemas).
# Não guardam dados; as tabelas serão criadas depois (Bronze na Fase 1, dbt na Silver/Gold).
# prod: bronze, silver, gold | dev: dev_bronze, dev_silver, dev_gold (spec, seção 6.1)
locals {
  camadas = ["bronze", "silver", "gold"]

  # Bancos que não são camadas (Fase 2). A regra do ADR 0013 vale para eles também:
  # o prefixo no S3 tem o mesmo nome do banco (controle/, teste_bronze/, teste_controle/).
  bancos_extras = {
    controle       = "Tabelas de controle do pipeline (manifesto de ingestão). ADR 0013, revisão da Fase 2"
    teste_bronze   = "Ambiente de teste da ingestão: Bronze alimentada pela TLC de mentira (Fase 2)"
    teste_controle = "Ambiente de teste da ingestão: manifesto do teste (Fase 2)"
  }

  bancos_glue = toset(concat(
    local.camadas,
    [for camada in local.camadas : "dev_${camada}"],
    keys(local.bancos_extras)
  ))
}

resource "aws_glue_catalog_database" "camadas" {
  for_each = local.bancos_glue

  name        = each.key
  description = lookup(local.bancos_extras, each.key, "Camada ${each.key} do lakehouse (gerenciado pelo Terraform)")
}
