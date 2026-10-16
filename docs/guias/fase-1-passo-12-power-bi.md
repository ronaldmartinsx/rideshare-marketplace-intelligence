# Guia — Fase 1, passo 12: primeiro visual no Power BI (máquina Windows)

> **Para quem:** o Ronald, na máquina Windows, e o Claude Code que o acompanhar lá.
> **Contexto:** a engenharia da Fase 1 está pronta no Mac (Bronze, `stg_tlc__hvfhv_trips`, `fct_demanda_zona_hora`). Falta testar o risco **R3** (Power BI ↔ Athena) e fechar a fase. Combinados de trabalho: ver `CLAUDE.md`. Evidências até aqui: `docs/validacao/fase-1.md`.

## Estado antes deste passo (15/10/2026)

| Item | Situação |
|---|---|
| Branch | `fase-1-fatia-vertical` |
| Tabela a consumir | `dev_gold.fct_demanda_zona_hora` (Iceberg) |
| Linhas esperadas | **364.630** |
| Soma esperada de `qtd_corridas` | **20.405.666** |
| Grão | hora de embarque × zona de origem × operadora |
| Colunas | `hora_embarque`, `zona_origem_id`, `licenca_operadora`, `qtd_corridas`, `milhas_total`, `segundos_corrida_total`, `tarifa_base_total`, `repasse_motorista_total`, `gorjetas_total`, `taxa_cbd_total`, `qtd_corridas_compartilhadas` |
| Custo esperado | Uma atualização lê ~7,7 MB no Athena (fração de centavo) |

## 0. (Opcional) Clonar o repositório no Windows

Necessário só se for usar o Claude Code no Windows ou editar os documentos de fechamento lá.

```powershell
git clone https://github.com/ronaldmartinsx/rideshare-marketplace-intelligence.git
cd rideshare-marketplace-intelligence
git switch fase-1-fatia-vertical
```

## 1. Instalar o driver ODBC da Athena

- Baixar o instalador **64 bits (MSI)** do **Amazon Athena ODBC 2.x**: https://docs.aws.amazon.com/athena/latest/ug/odbc-v2-driver.html
- Versão **2.1 ou mais nova** (login SSO com PKCE). Usada em 15/10/2026: **2.4.0.0**. A partir da 2.2, desinstalar a versão anterior antes de instalar.
- Pré-requisitos (conferidos): Visual C++ Redistributable x64 e porta de saída **444** liberada (é por onde o driver recebe os resultados).
- Instalar com as opções padrão.
- ⚠️ O instalador cria um **System DSN `Amazon Athena`** (workgroup `primary`). Não usar: o `primary` não tem o limite de 1 GiB.

## 2. Criar o DSN

1. Menu Iniciar → **"Fontes de Dados ODBC (64 bits)"**. ⚠️ Tem que ser o de **64 bits** (o Power BI Desktop é 64 bits).
2. Aba **DSN de Usuário** → **Adicionar** → driver **Amazon Athena ODBC (x64)**.
3. Preencher:

| Campo | Valor |
|---|---|
| Data Source Name | `rideshare-athena` |
| Region | `us-east-1` |
| Catalog | `AwsDataCatalog` |
| Database | `dev_gold` |
| Workgroup | **`rideshare`** (tem o limite de 1 GiB por consulta; nunca usar o `primary`) |
| S3 Output Location | `s3://rmartins-rideshare-athena-results/resultados/` |
| Authentication | **Browser SSO OIDC** (login do IAM Identity Center, sem chave permanente) |
| IAM Identity Center Start URL | o **AWS access portal URL** (no console: IAM Identity Center → Dashboard; ou no `~/.aws/config` do Mac, campo `sso_start_url`) |
| IAM Identity Center Region | `us-east-1` |
| Account ID | o ID da conta AWS (aparece no access portal). **Fica só na máquina; nunca no repositório** |
| Role name | `AdministratorAccess` |

   Os campos de login (Authentication Type em diante) ficam na janela do botão **Authentication Options**.
4. **Test** → o navegador abre → login com o usuário `ronald` + MFA → o teste deve dar sucesso.
5. **OK na janela de configuração.** ⚠️ O Test só testa; quem grava o DSN é o OK.

Notas:
- **User DSN** basta para o Desktop. **System DSN** só seria necessário com gateway (fora do escopo da v1).
- `AdministratorAccess` é só para este teste. Na Fase 4, o Power BI ganha uma identidade **somente leitura da Gold** (spec 11.5).
- O driver guarda a credencial temporária em `%USERPROFILE%\.athena-odbc\` (texto puro, como o cache da AWS CLI).

## 3. Conectar o Power BI Desktop

1. **Obter dados** → buscar **Amazon Athena** → **Conectar**.
2. **DSN:** `rideshare-athena`. **Modo de conectividade:** **Import**.
3. Autenticação: **"Use Data Source Configuration"** (usar a configuração do DSN).
4. Navegador: **AwsDataCatalog → dev_gold → fct_demanda_zona_hora** → **Carregar**.

## 4. Conferir e fazer o primeiro visual

1. Conferir: **364.630 linhas** e soma de `qtd_corridas` = **20.405.666**.
2. Um visual simples (sugestão: **gráfico de linhas, corridas por dia, uma linha por operadora**). Usar somas diretas das colunas; as medidas DAX são ✍️ do Ronald na Fase 4.
3. Tirar um print do visual.

## Se travar

| Sintoma | Causa provável |
|---|---|
| O driver não aparece na lista ao criar o DSN | Abriu o administrador ODBC de 32 bits |
| `Data source name not found` | DSN criado no administrador errado, ou nome digitado diferente de `rideshare-athena` |
| O navegador não abre ou o login não volta | Porta local 7890 bloqueada (parâmetro `listen_port` do driver), ou URL do portal/região errados |
| `AccessDenied` | Account ID ou Role name errados no DSN |
| Consulta cancelada por limite | Algo lendo além de 1 GiB: conferir se a tabela é a da `dev_gold` (pequena) e o workgroup é o `rideshare` |
| Tabela não aparece no navegador | Database diferente de `dev_gold` no DSN |
| O teste passou, mas o DSN não aparece na lista | A janela de configuração foi fechada sem **OK** (o Test não salva) |
| Aparece um DSN `Amazon Athena` que você não criou | É o DSN de exemplo do instalador (System, workgroup `primary`). Ignorar |

## 5. Registrar o resultado (R3)

Em `docs/validacao/fase-1.md`, nova seção "Power BI ↔ Athena (R3)":
- **Desktop:** conectou? Contagens conferidas? (colar os números e anexar o print, por exemplo em `docs/validacao/img/`).
- **Service:** pela documentação da Microsoft, o conector do Athena exige **on-premises data gateway** (driver ODBC na máquina do gateway, **System DSN**) e uma **identidade de máquina** para atualização agendada (o login por navegador exige uma pessoa e expira). Fonte: https://learn.microsoft.com/en-us/power-query/connectors/amazon-athena. Conclusão: atualização no Service fica **fora do escopo da v1** (spec 2.6); plano B: PBIP no repositório + prints + vídeo (Fase 4).
- Atualizar o risco **R3** na seção 13 da spec e marcar a pendência como feita na seção 8 do relatório.

## 6. Fechar a Fase 1 (checklist)

Pelo ciclo da spec (seção 1.4):

- [x] Passos 1 a 5 acima (R3 respondido com evidência em 15/10/2026: `docs/validacao/fase-1.md`, seção 8).
- [x] **ADR 0002** (`docs/adr/0002-iceberg-silver-gold.md`): Iceberg na Silver e na Gold, com as evidências da Fase 1 (snapshots, time travel `FOR TIMESTAMP AS OF TIMESTAMP '...'`, `DROP TABLE` apaga dados, rename na materialização `table`, ADR 0014).
- [x] **Gate de domínio da Fase 1** (✅ passou em 15/10/2026, formato híbrido) (Apêndice C da spec): explicação com as próprias palavras de Parquet, particionamento Hive, tabela externa × gerenciada, Iceberg, dbt, dbt-athena, ODBC/conector do Athena; 5 perguntas + 1 de entrevista. Pontos a sondar: aspas SQL em volta de `{{ }}` (erro recorrente), regra do predicate pushdown (max/min), time travel × rollback, `merge` × republicação.
- [x] `docs/aprendizados/fase-1.md` (o que aprendeu, erros, decisões, gate).
- [x] `docs/glossario.md` revisado.
- [x] `CLAUDE.md`: "Fase atual: 2".
- [x] PR `fase-1-fatia-vertical` → `main` (#2, aberto em 15/10/2026; merge pelo Ronald).

**Pendências que passam para a Fase 2** (não bloqueiam o fechamento): recalibrar o limite de 1 GiB do workgroup antes do backfill; decidir a credencial do Airflow; partition projection na Bronze; manifesto de ingestão (conflito com Bronze sem `DeleteObject`, ADR 0013); escrever o ADR 0008 (Airflow local).
