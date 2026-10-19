# ADR 0008: Airflow local (Astro CLI) e a identidade dele na AWS

- **Status:** Decidido. A parte "local × gerenciado" vem da Fase 0 (spec, seção 4); a credencial foi decidida e validada na Fase 2 (decisão D8)
- **Data:** 18/10/2026 (escrito)
- **Fase:** 0 e 2

## Contexto

O projeto precisa de um orquestrador que rode a ingestão mensal (Fase 2), o `dbt build` (Fase 3) e o ML (Fase 5). As opções eram um Airflow **gerenciado** na nuvem ou um Airflow **local**, em contêineres no Mac.

Uma vez local, o Airflow precisa de uma identidade para falar com a AWS **sem uma pessoa presente**. É o mesmo problema que apareceu no Power BI Service na Fase 1 (atualização agendada exige identidade de máquina). As pessoas do projeto entram pelo IAM Identity Center (login com MFA, credencial temporária), mas esse login expira e pede um navegador.

## Decisão

**1. Airflow local com o Astro CLI** (Astro Runtime 3.3-9 = Airflow 3.3.2, fixado no `airflow/Dockerfile`), rodando em Docker no Mac.

**2. Identidade em dois níveis:**

```text
usuário IAM rideshare-airflow-local  --sts:AssumeRole-->  role rideshare-airflow  -->  política de menor privilégio
(chave de acesso, no airflow/.env)                         (credencial de 1 hora)
```

- O **usuário** só tem uma permissão: assumir a role. A chave dele foi criada pelo terminal (fora do Terraform, para o segredo não ficar no estado) e gravada direto no `airflow/.env` (fora do Git), sem passar pela tela.
- A **role** tem a política `rideshare-airflow`: Bronze sem apagar, `controle/` e Silver/Gold com apagar, Athena **só** no workgroup `rideshare` (o do limite de 1 GiB), Glue só nos bancos do projeto.
- O Airflow usa a Connection `aws_default` (variável `AIRFLOW_CONN_AWS_DEFAULT` com `role_arn`). Cada task cria os seus clientes AWS no início, ganhando a sua própria credencial de 1 hora.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Airflow gerenciado (Amazon MWAA ou Astro na nuvem) | Custo fixo mensal de dezenas a centenas de dólares mesmo parado (não verificado em detalhe), incompatível com o orçamento de US$ 10/mês. Em produção real, seria a escolha certa |
| Montar o login SSO (`~/.aws`) no contêiner | A sessão expira e exige navegador: a DAG diária falharia sem uma pessoa; e o perfil SSO é administrador (fere o menor privilégio) |
| IAM Roles Anywhere (certificado X.509) | Sem chave permanente, mas exige criar e renovar uma autoridade certificadora: complexidade alta para um projeto de uma pessoa |
| Política direto no usuário (sem role) | Funcionaria, mas a permissão ficaria presa ao usuário. Com a role, a mesma permissão serve a um Airflow gerenciado no futuro, sem chave nenhuma |

## Consequências

**Ganhamos:**
- Custo zero de orquestração; o ambiente é idêntico em qualquer máquina com Docker (imagem fixada).
- Menor privilégio testado (Fase 2, etapa 2): a role lista a Bronze, mas **não** acessa o bucket do estado do Terraform nem o workgroup `primary` (sem freio de custo).
- O registro de auditoria da AWS mostra "a role `rideshare-airflow` fez isso": fica claro qual cargo agiu.
- Migrar para um Airflow gerenciado é trocar o usuário pela role de execução do serviço: a política não muda.

**Perdemos / cuidados:**
- **O agendamento só roda com o Mac ligado e o Docker de pé.** Um run perdido é recuperado no dia seguinte: a ingestão é guiada pelo manifesto (ADR 0003), não pela data do run.
- **Chave permanente:** se vazar, quem a tiver assume a role (os dois níveis não reduzem esse estrago). Mitigação: fora do Git (`.gitignore` e `.dockerignore`), menor privilégio, rotação manual (criar uma chave nova, trocar no `.env`, desativar a antiga; o IAM aceita até 2 por usuário).
- A renovação automática da credencial de 1 hora pelo provider da Amazon não está documentada; a criação dos clientes dentro de cada task evita depender dela.
