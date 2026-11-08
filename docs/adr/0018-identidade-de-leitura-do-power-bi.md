# ADR 0018: Identidade somente leitura do Power BI

- **Status:** Decidido e aplicado na Fase 4 (passo 3). Validado pela AWS CLI (12/12 testes). No Power BI, uso **provisório** do papel de administrador até acrescentar `athena:ListDataCatalogs` (ver Consequências)
- **Data:** 01/11/2026
- **Fase:** 4
- **Relacionado:** spec 11.5 (menor privilégio), ADR 0008 (identidade do Airflow), ADR 0012 (estado do Terraform), D5 e P1 a P4 do plano da Fase 4

## Contexto

Na Fase 1, o DSN `rideshare-athena` do Windows usava o papel **`AdministratorAccess`**. O Power BI só precisa ler a Gold, mas com esse papel um erro de configuração ou uma consulta errada poderia apagar tabelas, ler a Silver inteira ou gravar em qualquer bucket.

A spec (11.5) pede **menor privilégio**: uma identidade somente leitura para o Power BI e o agente, separada da do Airflow.

## Decisão

| # | Decisão | Como |
|---|---|---|
| P1 | **Permission set do Identity Center**, sem chave de acesso | `RideshareLeituraGold`, atribuído ao usuário do Identity Center nesta conta. O driver ODBC entra por **Browser SSO OIDC**: navegador, MFA e credencial temporária. Nenhum segredo fica no Windows |
| P2 | **Workgroup próprio** no Athena | `rideshare-bi`: limite de 1 GiB por consulta (a maior importação lê 358 MB), resultados em `bi/` no bucket de resultados, métricas no CloudWatch (custo do BI separado do custo do dbt) |
| P3 | **Só o banco `gold`** de produção | S3: listar e ler só `gold/` no lake; escrever só em `bi/` no bucket de resultados. Glue: leitura do banco `gold` e das tabelas dele. Athena: consultas só no workgroup `rideshare-bi` |
| P4 | **Sessão de 8 horas** | Um dia de trabalho sem pedir login de novo |

Tudo em Terraform (`infra/terraform/iam_powerbi.tf` e `athena.tf`). Usuário e instância do Identity Center vêm de *data sources*: nenhum ID da conta escrito no código.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Manter o `AdministratorAccess` | Contraria o menor privilégio; qualquer engano no Power BI tem alcance total |
| Usuário IAM com chave de acesso no DSN | Chave permanente guardada no Windows: o tipo de credencial que mais vaza |
| Política gerenciada da AWS para o Athena (ex.: acesso total ao Athena) | Ampla demais: permite consultar em qualquer workgroup e não restringe os buckets |
| AWS Lake Formation | Permissões mais finas (coluna e linha), mas outra camada de administração para um único banco somente leitura |
| Usar o workgroup `rideshare` do dbt | Mistura custo e resultados do BI com os do pipeline, e o limite de 3 GiB é maior que o necessário |

## Consequências

- **Ganhamos:**
  - menor privilégio comprovado: 12 de 12 testes pela AWS CLI (lê a Gold; Silver, Bronze, outros workgroups, escrita e exclusão negados; validação da Fase 4, seção 3);
  - o catálogo listado pelo papel mostra só o banco `gold`;
  - sem segredo guardado; custo do BI visível por workgroup.
- **Perdemos ou passamos a cuidar de:**
  - **Login pelo navegador:** a cada 8 horas e, numa recarga do zero, atualizar primeiro uma tabela pequena para fazer um login só (atualizar tudo de uma vez abre um login por tabela e estoura o tempo limite).
  - **Atualização no Service:** o Browser SSO exige uma pessoa no navegador. Uma atualização agendada pelo gateway precisaria de outra forma de autenticação (inferência; não verificado). Está fora da v1 (spec, Seção 10).
  - **Menor privilégio se descobre na prática.** A política nasceu sem `athena:ListDataCatalogs` e `athena:ListWorkGroups`, de propósito. Com o driver ODBC 2.5.0.0, listar as tabelas do `gold` no navegador do Power BI ainda chama `athena:ListDataCatalogs` (validação, seção 4). Enquanto isso:
    - o DSN usa **provisoriamente** o `AdministratorAccess`, mantendo o banco `gold`, o workgroup `rideshare-bi` e a saída `bi/`. O projeto guarda só o nome do DSN, então trocar o papel não muda o PBIP;
    - **pendente (Mac):** acrescentar `athena:ListDataCatalogs` à política (o formato do `Resource` está não verificado na referência do IAM), voltar o DSN para `RideshareLeituraGold` e testar uma atualização completa.
