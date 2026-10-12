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

variable "athena_limite_bytes_por_consulta" {
  description = "Limite de bytes lidos por consulta no workgroup do Athena. Acima disso, a consulta é cancelada. Recalibrar na Fase 1."
  type        = number
  default     = 1073741824 # 1 GiB
}