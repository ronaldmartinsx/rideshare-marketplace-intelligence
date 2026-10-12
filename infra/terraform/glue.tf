# Bancos do Glue Data Catalog: agrupamentos lógicos de tabelas (equivalem a schemas).
# Não guardam dados; as tabelas serão criadas depois (Bronze na Fase 1, dbt na Silver/Gold).
# prod: bronze, silver, gold | dev: dev_bronze, dev_silver, dev_gold (spec, seção 6.1)
locals {
  camadas = ["bronze", "silver", "gold"]

  bancos_glue = toset(concat(
    local.camadas,
    [for camada in local.camadas : "dev_${camada}"]
  ))
}

resource "aws_glue_catalog_database" "camadas" {
  for_each = local.bancos_glue

  name        = each.key
  description = "Camada ${each.key} do lakehouse (gerenciado pelo Terraform)"
}
