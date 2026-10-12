# Fase 0: Fundação — registro de aprendizado

- **Período:** 10/10/2026 a 12/10/2026
- **Objetivo:** ambiente reproduzível e seguro, com custo controlado.
- **Resultado:** todos os critérios de pronto cumpridos; gate de domínio aprovado (com dois reforços registrados).

---

## 1. O que foi construído

| Peça | Como | Onde |
|---|---|---|
| Repositório público com `.gitignore` preventivo | Git + GitHub CLI | raiz do repo |
| Acesso de admin sem chave permanente | IAM Identity Center (SSO) + perfil `rideshare-admin` na AWS CLI | `~/.aws/config` (fora do repo) |
| Budget de US$ 10/mês com alertas real (80%, 100%) e previsto (100%) | Terraform | `infra/terraform/budget.tf` |
| Bucket do data lake, versionado e privado ✍️ | Terraform (escrito pelo Ronald) | `infra/terraform/s3.tf` |
| Estado do Terraform no S3, com versionamento, trava e `prevent_destroy` | Terraform + migração `-migrate-state` | `tfstate.tf`, `backend.tf` |
| 6 bancos do Glue (`bronze`, `silver`, `gold` e `dev_*`) | Terraform com `for_each` | `glue.tf` |
| Bucket de resultados do Athena (expira em 7 dias) e workgroup `rideshare` (limite de 1 GiB por consulta) | Terraform | `athena.tf` |
| Política IAM do Airflow, com menor privilégio, ainda solta ✍️ | Terraform (rascunho do Ronald, finalizado pelo Claude Code) | `iam_airflow.tf` |
| Airflow 3.3 rodando local | Astro CLI + Docker | `airflow/` |

**Infraestrutura total:** 18 recursos na AWS, todos em código. Custo até aqui: praticamente zero.

**Critérios de pronto:**

| Critério | Evidência |
|---|---|
| `terraform plan` limpo depois do apply | `No changes. Your infrastructure matches the configuration.` |
| Alerta de budget ativo | `rideshare-mensal`, 10.0 USD, MONTHLY (`aws budgets describe-budgets`) |
| `SELECT 1` no Athena pelo workgroup | `SUCCEEDED`, 0 bytes lidos, Athena engine v3 |
| UI do Airflow abre | `http://localhost:8080`; DAG de exemplo com 13 tasks em `success` |

---

## 2. O que aprendi, por tecnologia

- **Git e GitHub:** o histórico guarda tudo para sempre. Um segredo commitado precisa ser revogado, não só apagado. O `.gitignore` vem antes do primeiro commit.
- **AWS IAM e Identity Center:** o IAM é o sistema inteiro de permissões (usuários, roles, políticas). O Identity Center é o login central para pessoas, e o permission set vira uma **role** dentro da conta. Quem executa os comandos é a role (`assumed-role/AWSReservedSSO_...`), e o `ronald` é só o nome da sessão. Credenciais temporárias limitam o estrago de um vazamento; access keys permanentes, não.
- **Políticas IAM:** tudo é negado por padrão (negação implícita); um `Deny` explícito vence um `Allow`. Ações de bucket usam o ARN do bucket; ações de objeto usam o ARN com `/*`.
- **Terraform:** é declarativo; o estado é a memória (perdê-lo é amnésia). Leia o `plan` antes do `apply` procurando `-/+`. O código vence o console (drift). Para trocar de backend, use `-migrate-state`, nunca `-reconfigure`.
- **S3:** não tem pastas, só prefixos de chave. `PutObject` sobrescreve sem pedir permissão de apagar; o versionamento é a rede de proteção. O nome do bucket é global e não pode ser renomeado.
- **Glue e Athena:** é o banco de dados "desmontado" (armazenamento, catálogo e motor separados). O Glue só aponta para os dados. O Athena cobra por dado lido, e o workgroup é o freio de mão.
- **Docker:** Dockerfile (receita) → imagem (marmita congelada) → contêiner (marmita servida). Contêiner é efêmero; o que precisa sobreviver vai num volume.
- **Airflow:** orquestra, não processa. O estado mora no banco de metadados (dá para consultar com SQL nas tabelas `dag_run` e `task_instance`). DAG nova nasce pausada.

---

## 3. Erros cometidos (e o que ensinaram)

**Do Ronald:**
- Um `.git` acidental na pasta pessoal, com 3,1 GB de cópias de arquivos (incluindo `.ssh/`) vindas de um `git add .` interrompido. Removido. Lição: o Git procura o repositório subindo pelas pastas.
- MFA do root perdido. Recuperado, mas com um só dispositivo (pendente: cadastrar o segundo).
- No `.tfvars.example`, um valor de texto sem aspas (`prefixo = rmartins`). O `validate` não pega isso, porque o `.example` nunca é lido.
- Na política do Airflow: `for_each` no recurso inteiro (criaria 6 políticas), ações de bucket com ARN de objeto e ações do Athena apontando para um bucket.
- No gate: confundir o usuário do Identity Center com o usuário IAM, e dizer que o drift "recria" quando na verdade "altera no lugar".

**Do Claude Code (registrados por honestidade):**
- Informou um formato desatualizado do endereço do portal do Identity Center.
- Afirmou que a tag `projeto` permitiria filtrar custos, sem lembrar que é preciso ativá-la como cost allocation tag.
- Deixou o `*.tfplan` fora do `.gitignore`. O plano salvo guardava o e-mail; foi corrigido antes de qualquer commit.
- Comentou a saída de comandos que o Ronald não estava vendo (as saídas ficam recolhidas no chat). Agora as saídas relevantes são coladas na mensagem.
- Atrasou a inclusão dos termos das Aulas 3 e 4 no glossário.
- Esperava a UI do Airflow em `airflow.localhost`, que o Safari não resolve; a solução foi `localhost:8080`.

---

## 4. Decisões tomadas

| Decisão | Registro |
|---|---|
| AWS (S3 + Glue + Athena) como plataforma | [ADR 0001](../adr/0001-escolha-aws.md) |
| PBIP no lugar do `.pbix` | ADR 0011 (a decidir na Fase 4) |
| Estado do Terraform no S3, com versionamento e trava nativa | [ADR 0012](../adr/0012-estado-terraform-s3.md) |
| Dev no prefixo `dev/` do mesmo bucket; dev lê a Bronze de prod | [ADR 0013](../adr/0013-layout-dev-no-s3.md) |
| IAM Identity Center (credencial temporária) no lugar de usuário IAM com chave | esta página, seção 2 |
| Airflow 3.3 (Astro Runtime 3.3-9) + Cosmos 1.15.x | spec, seção 4 e risco R8 |
| Credencial do Airflow para a AWS adiada para a Fase 2 | memória do projeto; decidir quando a primeira DAG tocar na AWS |

---

## 5. Gate de domínio

### Explicação com as próprias palavras (resumo da avaliação)

| Tecnologia | Avaliação |
|---|---|
| Git e GitHub | Firme. Faltou: branch/PR, histórico e segredos, "por que aqui" |
| AWS, IAM e Identity Center | Imprecisa na explicação (IAM × Identity Center); corrigida na revisão |
| Terraform | Firme. Faltou: `plan` × `apply`, declarativo |
| S3 | Rasa na explicação; demonstrada na prática (pergunta 4) |
| Glue | Correta no essencial |
| Athena | Correta no essencial; workgroup vago |
| Docker | A melhor resposta |
| Airflow e Astro | Rasa na explicação; revisada com a analogia do despachante |

### Autoavaliação

| # | Tipo | Resultado |
|---|---|---|
| 1 | Conceitual: que identidade executa dentro da conta | Parcial; revisada (tópico A) |
| 2 | Conceitual: "orquestra, não processa" | Parcial; revisada (tópico C) |
| 3 | Aplicada: drift no workgroup | Errada na consequência; revisada (tópico B) |
| 4 | Aplicada: sobrescrita na Bronze | Correta |
| 5 | Diagnóstico: `ListBucket` com ARN de objeto | Correta |

**Pergunta de entrevista:** "Como garante que a infraestrutura é reproduzível e não gera conta surpresa?" A resposta acertou os pilares (IaC e budget). Faltou: estado versionado e `plan` revisado; a diferença entre alertar (budget) e prevenir (limite do workgroup, expiração dos resultados, serviços sem servidor).

**Revisão:** três tópicos repetidos com analogias novas (locadora e placa do carro; planta da casa; despachante da central), mais uma mini-checagem: A ✅, B ✅, C parcial (retry é conteúdo da Fase 2).

**Resultado:** ✅ Passou.

**Reforços para as próximas fases:**
1. Ao ler um `plan`, dizer sempre a consequência do `apply`, e não só o símbolo.
2. Semântica de retry e falha no Airflow (`failed`, `upstream_failed`), na Fase 2.

---

## 6. Pendências e melhorias anotadas

- Cadastrar o segundo dispositivo de MFA do root.
- Regra de ciclo de vida que expire versões antigas no bucket do estado (os arquivos de trava se acumulam).
- Declarar explicitamente a criptografia (SSE-S3) nos buckets.
- Ativar a cost allocation tag `projeto` quando houver custo a acompanhar.
- Conferir se as métricas do workgroup no CloudWatch têm custo.
- Fase 1: validar a política do Airflow com o dbt-athena (pode faltar alguma ação); confirmar o comportamento de `DROP TABLE` em tabelas Iceberg.
- Fase 2: decidir a credencial do Airflow; resolver o conflito entre o manifesto Iceberg em `bronze/` e a Bronze sem `DeleteObject` (ADR 0013).
