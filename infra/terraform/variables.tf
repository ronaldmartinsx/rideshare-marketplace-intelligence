variable "budget_limite_usd" {
  description = "Limite mensal de gasto da conta AWS, em dólares."
  type        = number
  default     = 10
}

variable "email_alertas" {
  description = "E-mail que recebe os alertas do budget. Definido em terraform.tfvars (fora do Git)."
  type        = string
}

variable "prefixo" {
  description = "Prefixo usado no nome do bucket S3"
  type        = string
}