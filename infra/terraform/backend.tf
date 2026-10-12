# Onde o Terraform guarda o estado. Ver ADR 0012.
# O bloco backend NÃO aceita variáveis: o nome do bucket fica fixo aqui
# (e precisa bater com "${var.prefixo}-tfstate" do tfstate.tf).
terraform {
  backend "s3" {
    bucket       = "rmartins-rideshare-tfstate"
    key          = "infra/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
