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
variable "athena_bi_limite_bytes_por_consulta" {
  description = "Limite de bytes lidos por consulta no workgroup do Power BI (rideshare-bi)."
  type        = number
  # 1 GiB (Fase 4, decisão P2): a maior tabela que o Power BI importa, a fct_demanda_zona_hora,
  # tem 358 MB nos 33 meses (01/11/2026). A fct_od_diario (819 MB) não é importada.
  default = 1073741824
}

variable "usuario_identity_center" {
  description = "Nome de login (UserName) do usuário do Identity Center que recebe o papel de leitura do Power BI. Definido em terraform.tfvars."
  type        = string
}
