# Bucket que guarda o estado do Terraform (a "memória" do que foi criado).
# Ver ADR 0012.
resource "aws_s3_bucket" "tfstate" {
  bucket = "${var.prefixo}-tfstate"

  # Apagar este bucket faria o Terraform "esquecer" toda a infraestrutura.
  # Com esta marca, qualquer plano que tente apagá-lo falha.
  lifecycle {
    prevent_destroy = true
  }
}

# Cada apply grava uma nova versão do estado: dá para voltar a uma anterior
resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
