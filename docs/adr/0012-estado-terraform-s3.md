# ADR 0012: Estado do Terraform no S3, com versionamento e trava nativa

- **Status:** Decidido
- **Data:** 11/10/2026
- **Fase:** 0

## Contexto

O Terraform guarda num arquivo de estado (`terraform.tfstate`) a ligação entre cada bloco do código e o recurso real na AWS. Se esse arquivo se perde, o Terraform "esquece" o que criou: passa a querer criar tudo de novo, falha em nomes únicos ou duplica recursos, e os originais viram órfãos.

A spec não definia onde guardar o estado. Por padrão, ele fica na máquina local.

## Decisão

1. O estado fica no bucket `rmartins-rideshare-tfstate`, na chave `infra/terraform.tfstate`, configurado em `infra/terraform/backend.tf`.
2. O bucket tem versionamento ligado, bloqueio de acesso público e `prevent_destroy` no Terraform.
3. A trava contra execuções simultâneas usa o arquivo de lock nativo do S3 (`use_lockfile = true`), sem DynamoDB.
4. Sequência adotada: estado local na criação do budget e do bucket do lake; migração para o S3 (`terraform init -migrate-state`) depois da aula de S3.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Estado local permanente | Perda do disco = perda da memória do Terraform. Não é prática de mercado |
| S3 desde o primeiro recurso | Exigiria criar o bucket antes de aprender S3. Preferimos um conceito por vez |
| S3 + tabela DynamoDB para a trava | Era o padrão antigo. O lock nativo do S3 dispensa um serviço extra |
| Terraform Cloud / HCP | Mais um serviço e uma conta. Desnecessário para um projeto de uma pessoa |

## Consequências

**Ganhamos:**
- O estado sobrevive à perda da máquina e fica disponível para o CI no futuro.
- O histórico de versões permite recuperar um estado corrompido.
- A trava impede dois `apply` ao mesmo tempo.

**Perdemos / cuidados:**
- O bloco `backend` não aceita variáveis: o nome do bucket está fixo em `backend.tf` e precisa acompanhar manualmente o `prefixo` (ver `tfstate.tf`).
- O bucket do estado é gerenciado pelo mesmo código que guarda seu estado ("ovo e galinha"). Por isso o `prevent_destroy`: um `terraform destroy` completo falha de propósito nesse bucket.
- Cada operação deixa uma versão antiga do arquivo de trava no bucket. Custo desprezível; melhoria futura: regra de ciclo de vida que expira versões antigas.
- Nunca usar `terraform init -reconfigure` para mudar de backend: ele ignora o estado existente. Para mover o estado, usar `-migrate-state`.
