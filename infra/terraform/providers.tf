provider "aws" {
  region = "us-east-1"

  # O perfil não fica no código: use `export AWS_PROFILE=rideshare-admin`.
  # Assim o código não depende de como cada máquina nomeia seus perfis.

  # Aplicadas automaticamente a todo recurso criado por este código
  default_tags {
    tags = {
      projeto        = "rideshare-marketplace-intelligence"
      gerenciado_por = "terraform"
    }
  }
}
