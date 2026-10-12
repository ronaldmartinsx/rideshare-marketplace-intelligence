# Alerta de orçamento da conta inteira (não só do projeto):
# um recurso esquecido fora do projeto também custa.
# Budget só AVISA. Não bloqueia nem desliga nada.
resource "aws_budgets_budget" "mensal" {
  name         = "rideshare-mensal"
  budget_type  = "COST"
  limit_amount = var.budget_limite_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # 1) Gasto real passou de 80% do limite: hora de investigar
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.email_alertas]
  }

  # 2) Gasto real passou do limite
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.email_alertas]
  }

  # 3) A PREVISÃO do mês passa do limite: avisa antes de o gasto acontecer
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.email_alertas]
  }
}
