# Data sources: LEEM informações da AWS, não criam nada.
# Usados para montar ARNs sem escrever o ID da conta no código (repositório público).
data "aws_caller_identity" "atual" {}

data "aws_region" "atual" {}

locals {
  conta_id = data.aws_caller_identity.atual.account_id
  regiao   = data.aws_region.atual.region
}
