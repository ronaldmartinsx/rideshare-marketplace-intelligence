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
  description = "Limite de bytes lidos por consulta no workgroup do Athena. Acima disso, a consulta é cancelada."
  type        = number
  # 3 GiB (Fase 3, decisão F9 revisada): o incremental do dbt-athena copia o mês inteiro da tabela
  # temporária para a final, e um mês da int_trips_enriched tem ~1,3 GB. Ler a Silver inteira por
  # engano (~40 GB) continua barrado.
  default = 3221225472
}