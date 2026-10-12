# ADR 0001: AWS (S3 + Glue + Athena) como plataforma

- **Status:** Decidido
- **Data:** 12/10/2026 (decisão tomada na spec v1.0, 03/10/2026; registrada ao fim da Fase 0)
- **Fase:** 0

## Contexto

O projeto precisa de um lakehouse para guardar e consultar os dados mensais da TLC (dezenas de milhões de linhas por mês, estimativa a validar na Fase 1), com três objetivos:

1. **Portfólio de mercado:** demonstrar engenharia de dados com ferramentas e formatos amplamente usados.
2. **Custo de portfólio:** uso intermitente (algumas horas por semana), com orçamento-alvo de US$ 10/mês.
3. **Diversificação:** o autor já domina o ecossistema Microsoft (Power BI, Fabric); o projeto deve mostrar uma stack neutra de fornecedor.

## Decisão

Usar a AWS com serviços sem servidor e cobrança por uso:

- **S3** para armazenar as três camadas (Bronze, Silver, Gold);
- **Glue Data Catalog** como catálogo de metadados;
- **Athena** como motor SQL (warehouse), lido pelo dbt, pelo Power BI e pelo agente de IA.

Formatos abertos (Parquet, Iceberg) e ferramentas open source (dbt, Airflow) por cima.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Microsoft Fabric** | Domínio que o autor já tem; não diversifica o portfólio. Cobrança por capacidade fixa (F SKU) é cara para uso intermitente |
| **Databricks Free Edition** | Descartado na spec: cotas diárias e acesso à internet restrito, o que inviabiliza a ingestão mensal real |
| **Google BigQuery** | Plano B. Modelo parecido (serverless, paga por dado lido), mas menos presença em vagas de engenharia de dados no Brasil que a AWS (percepção do autor, não verificada) |
| **Amazon Redshift / EMR** | Exigem cluster ou capacidade provisionada; custo parado incompatível com o orçamento |

## Consequências

**Ganhamos:**
- Custo próximo de zero quando nada está rodando: S3, Glue e Athena não têm servidor ligado.
- Arquitetura de lakehouse "desmontada" (armazenamento, catálogo e motor separados), que transfere para outras plataformas.
- Stack com forte presença no mercado.

**Perdemos / cuidados:**
- O Athena cobra por dado lido: consultas mal escritas custam dinheiro. Mitigado com o limite de bytes por consulta no workgroup, particionamento e Parquet.
- Latência de segundos por consulta: o Power BI usará modo Import, não DirectQuery.
- Mais peças para entender e configurar do que numa plataforma integrada (IAM, catálogo, workgroups), o que também é um objetivo de aprendizado.
- Dependência de serviços específicos da AWS (Glue, Athena); os dados em formatos abertos no S3 continuam portáveis.
