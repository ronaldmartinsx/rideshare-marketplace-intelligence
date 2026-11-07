# Rideshare Marketplace Intelligence

Projeto de portfólio de engenharia de dados sobre as corridas de aplicativo (Uber, Lyft) de Nova York: um lakehouse na AWS (S3, Glue, Athena com Apache Iceberg), transformação com dbt, orquestração com Airflow, painel no Power BI e, nas próximas fases, previsão de demanda e um agente em linguagem natural.

> Em construção. Fase atual: **4**, relatório no Power BI ([veja o relatório](powerbi/README.md)). A especificação completa está em [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md), e as decisões de arquitetura em [`docs/adr/`](docs/adr/).

## O relatório

Uma página única no Power BI que responde, com 672 milhões de viagens, onde falta oferta, como evolui a economia de cada corrida, qual foi o efeito da taxa de congestionamento de Manhattan e onde a Lyft perde terreno para a Uber. Detalhes, prints e decisões de desenho em [`powerbi/README.md`](powerbi/README.md).

https://github.com/user-attachments/assets/57491ecf-722b-4c4d-a495-e67a7a7986be

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `infra/terraform/` | Infraestrutura na AWS como código |
| `airflow/` | DAGs de ingestão (`tlc_ingest`, `weather_ingest`), contratos de schema e testes |
| `dbt/` | Modelos da Silver e da Gold |
| `powerbi/` | Relatório do Power BI em PBIP (modelo semântico em TMDL, relatório em PBIR), mapa das zonas e o gerador da página |
| `docs/` | Especificação, ADRs, glossário, relatórios de validação e registro de aprendizado por fase |

## Fontes de dados e licenças

| Fonte | Uso | Licença / termos |
|---|---|---|
| [NYC Taxi & Limousine Commission (TLC): Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), arquivos High Volume For-Hire Vehicle | Corridas, de jan/2024 em diante | Dados abertos da cidade de Nova York |
| [Open-Meteo](https://open-meteo.com/), API histórica | Clima horário de um ponto de Manhattan | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). **Weather data by [Open-Meteo.com](https://open-meteo.com/)**. Uso gratuito não comercial, conforme os [termos](https://open-meteo.com/en/terms) |
