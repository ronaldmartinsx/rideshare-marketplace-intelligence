# Fase 2: Bronze completa e ingestão automatizada — registro de aprendizado

- **Período:** 16/10/2026 a 18/10/2026
- **Objetivo:** ingestão real, idempotente e com detecção de republicação.
- **Resultado:** "pronto quando" cumprido (rodar duas vezes não duplica; republicação vira versão nova vigente), backfill de 31 meses em produção, Bronze imutável garantida pelo armazenamento. Gate de domínio aprovado, com três reforços ([relatório de validação](../validacao/fase-2.md)).

---

## 1. O que foi construído

| Peça | Como | Onde |
|---|---|---|
| Bronze imutável | Política do bucket nega `PutObject` sem `If-None-Match`; código grava com `If-None-Match` + `ChecksumSHA256` | `infra/terraform/s3.tf`, `airflow/include/ingestao/bronze.py` |
| Partition projection na Bronze | `year` date, `month` enum, `ingest_ts` injected; tabela da Fase 1 adotada por `import` | `infra/terraform/bronze_tabelas.tf` |
| Identidade do Airflow | Usuário que só assume a role `rideshare-airflow`; chave direto no `.env` | `infra/terraform/iam_airflow.tf`, `airflow/.env` (fora do Git) |
| Manifesto de ingestão | Iceberg só de acréscimo + view `manifesto_vigente`; linha retroativa da Fase 1 | `scripts/fase-2/controle_manifesto.sql`, `scripts/fase-2/registro_retroativo_fase1.sql` |
| Contratos de schema | YAML no vocabulário do Athena (TLC) e de variáveis/unidades/ponto/horas (clima) | `airflow/include/contratos/` + `contrato.py` |
| ✍️ Decisão da ingestão | `decidir_acao` e `classificar_download` (ver a nota na seção 3) | `airflow/include/ingestao/decisao.py` |
| Entrada e saída | HEAD e download com SHA-256; Bronze; manifesto via Athena | `fonte_http.py`, `bronze.py`, `manifesto.py`, `fonte_open_meteo.py` |
| DAGs | `tlc_ingest` (diária, guiada pelo manifesto) e `weather_ingest` (disparada pelo Asset `bronze_tlc`) | `airflow/dags/` |
| Ambiente de teste | "TLC de mentira" (nginx) + bancos `teste_*`; 7 cenários | `airflow/docker-compose.override.yml`, `scripts/fase-2/gerar_amostra.sql` |
| Silver lendo a versão vigente | Macro `ingest_ts_vigente` | `dbt/macros/` |
| Backfill | 31 meses (14,3 GiB) em ~13 min; 32 meses de clima | Produção |
| Testes automatizados | 66 testes (`astro dev pytest`) | `airflow/tests/` |
| Documentação | ADRs 0003, 0008, 0009, 0015 (novos), 0013 e 0014 (revisados); spec; README mínimo com a atribuição do Open-Meteo | `docs/` |

**Critérios de pronto:**

| Critério | Evidência |
|---|---|
| Rodar a DAG duas vezes não duplica nada | Teste: 7 runs, 6 linhas no manifesto. Produção: run manual depois do backfill ignorou os 32 meses |
| Republicação simulada gera nova versão e marca a vigente | Teste, cenário 3: versão nova de 2026-07 virou a vigente; a anterior continua guardada |
| Backfill de jan/2024 até hoje | 32 meses vigentes por fonte; reconciliação manifesto × Bronze 32/32; 651.246.843 corridas |
| ADRs de Bronze imutável e de fuso horário | ADR 0003 e ADR 0009 |

**Custo da fase:** ~US$ 0,34/mês de armazenamento (14,73 GiB na Bronze); consultas no Athena abaixo de US$ 0,05 no total.

---

## 2. O que aprendi, por tecnologia

- **Airflow (DAG, task, operator, sensor):** a DAG é um grafo de dependências **sem ciclos**; tasks independentes rodam em paralelo. O operator é o molde de uma task (o `@task` é um operator Python). O sensor espera uma condição **dentro** da DAG; quem dispara **outra** DAG é o Asset. Aqui não usamos sensor porque a TLC publica sem data fixa e o run diário + HEAD já faz o papel de "voltar a conferir", quase de graça.
- **Retries:** reexecutam a task inteira **quando ela falha**, com espera crescente. Servem para erro **transitório** (rede, 5xx, conflito de commit do Iceberg); para erro **determinístico** (arquivo fora do contrato) a task falha sem retry. Por reexecutar tudo, exigem idempotência.
- **Agendamento, `catchup` e backfill:** `catchup` recupera **execuções**; backfill recupera **dados**. O histórico foi carregado pelo próprio código diário, guiado pelo **manifesto** (decisão D1): o primeiro run encontrou 31 meses faltando.
- **Idempotência:** não é um mecanismo, é uma camada em cada passo repetível: decidir (manifesto + HEAD), baixar (SHA-256), gravar (`ingest_ts` fixo + `If-None-Match`), registrar (conferir antes do `INSERT`), rodar (`max_active_runs=1`), transformar (delete + append, ADR 0014).
- **HEAD, ETag, Last-Modified e SHA-256:** um funil. O HEAD (menos de 1 KB) e o ETag filtram quase tudo; o SHA-256, calculado depois do download, é a prova do conteúdo. O ETag sozinho não basta (o mesmo arquivo reenviado em partes de outro tamanho ganha outro ETag). Numa API sem ETag, o SHA-256 só funciona sobre um JSON **canônico** (sem o campo volátil).
- **Manifesto e linhagem:** uma linha por **evento** de ingestão; o `status` descreve o evento (`aceito` e `rejeitado` trazem arquivo novo; `mesmo_conteudo` é conferência, sem arquivo). A versão vigente é **calculada** pela view (não há coluna `is_current`). Linhagem: `source_month` + `ingest_ts` da Silver levam à linha do manifesto (URL, ETag, SHA-256, arquivo, run do Airflow).
- **Contrato de schema e drift:** a referência é uma decisão versionada, nunca "o mês anterior" (a analogia do pneu). A política é por fonte: na TLC, coluna nova ou faltante alerta e segue, tipo diferente vai para quarentena; no clima, variável faltante também rejeita. Escrito no vocabulário do Athena porque o pyarrow chama texto de `large_string` e porque a pergunta real é "o Athena lê este arquivo com a tabela declarada?".
- **Assets:** o evento sai quando a **task** que declara o Asset em `outlets` termina com sucesso; task pulada não gera evento. A regra "só com dado novo aceito" é nossa (o `publicar` pula).
- **Partition projection:** o Athena **calcula** as partições pelas regras da tabela e ignora as do Glue. Com `ingest_ts` injected, toda consulta precisa informar a versão: ler duas versões sem querer ficou impossível. Versão inexistente devolve zero sem erro, por isso a Silver usa a macro.
- **S3 e IAM:** gravação condicional (`If-None-Match`, `412`); política do bucket × política IAM; `Deny` explícito vale até para o administrador; versionamento e ciclo de vida (versão não corrente, marca de apagado); trust policy e `AssumeRole`.
- **Fuso horário:** quando a documentação não responde, a evidência sai do dado (o teste do horário de verão).

---

## 3. Erros cometidos (e o que ensinaram)

**Do Ronald:**
- Aula 2: propôs evitar o arquivo órfão olhando se o `ingest_ts` era "de poucos minutos atrás": a mesma armadilha do relógio. A solução foi fixar o `ingest_ts` antes do upload.
- Aula 3: tratou um 403 em mês já ingerido com "retry", sem perceber que 403 é determinístico.
- Aula 4: não soube por que comparar com o mês anterior falha (explicado com o pneu; acertou na checagem seguinte). No caso da coluna toda nula, viu o schema mas não o alerta de qualidade.
- Etapa 5: misturou 403 e 503 ("instabilidade de rede"), `ignorar` e `aguardar`, e entendeu o `ingest_ts` como "horário da linha". Corrigido com o extrato do banco e o número da vaga.
- Ao longo da fase: confundiu o HEAD + comparação de ETag (leitura, na TLC) com o `If-None-Match: *` (gravação, no nosso S3), e as nossas versões por `ingest_ts` com o versionamento do S3.
- No gate: sensor × Asset, `is_current` como coluna, projection "cria" partições, coluna faltante na TLC "falha", e a pergunta 5 (zero sem erro atribuído à política do bucket).

**Do Claude Code (registrados por honestidade):**
- Na Aula 2, afirmou que a política do bucket resolvia "dois runs ao mesmo tempo" ("o primeiro ganha"). Errado: runs diferentes gravam em `ingest_ts` diferentes. A correção (`max_active_runs=1`) veio de uma pergunta do Ronald.
- Na Aula 3, usou o "chassi" como analogia do ETag, em conflito com o glossário (chassi = SHA-256). Corrigido na avaliação.
- O primeiro desenho da DAG tentou mapear sobre `plano["trabalho"]`; o Airflow recusa mapear sobre um pedaço de dicionário. Redesenhado para uma lista (e ficou mais claro: um mês com problema fica vermelho com o próprio nome).
- O contêiner da "TLC de mentira" subiu fora da rede `airflow` na primeira tentativa.
- O import da tabela da Bronze trouxe diferenças "de carona" (`owner`, `number_of_buckets`, `skewed_info`) e uma mudança fantasma na tabela de teste; resolvidas declarando os valores e com `ignore_changes`.
- Escreveu um teste confuso no contrato e uma regra de rejeição do clima que misturava categorias; os dois foram corrigidos antes de serem apresentados.
- O script auxiliar de consultas ficou na pasta temporária e foi apagado pela limpeza do sistema entre um dia e outro.

**Nota de transparência sobre a peça ✍️:** as regras da `decidir_acao` e da `classificar_download` foram desenhadas pelo Ronald numa tabela de cenários, revisada em duas rodadas (pistas, depois correção). A pedido dele, o **código** e os **testes** foram escritos pelo Claude Code, com explicação bloco a bloco e um teste de mesa (cenário 10 e "volta ao antigo"); o Ronald acertou a checagem do cenário 3. Combinado para as próximas fases: em peças ✍️ de Python, o Ronald desenha a regra; peças ✍️ de SQL e DAX continuam sendo escritas por ele.

---

## 4. Decisões tomadas

| Decisão | Registro |
|---|---|
| D1: `tlc_ingest` diária guiada pelo manifesto, sem sensor; histórico pelo mesmo código | spec, seção 7 |
| D2: HEAD em todos os meses do recorte, todo dia | spec, seção 7 |
| D3: `ingest_ts` fixo, `If-None-Match`, política do bucket, manifesto por último | [ADR 0003](../adr/0003-bronze-imutavel-versionada.md) |
| D4: banco `controle` para o manifesto | [ADR 0013](../adr/0013-layout-dev-no-s3.md) (revisado) |
| D5: `is_current` calculado por view; manifesto só de acréscimo; status `mesmo_conteudo` | ADR 0003 |
| D6: partition projection com `ingest_ts` injected; Silver lê a versão vigente | [ADR 0015](../adr/0015-leitura-da-bronze-por-projection.md) |
| D7: contrato em YAML; arquivo fora do contrato em quarentena | ADR 0003 |
| D8: usuário que só assume a role do Airflow | [ADR 0008](../adr/0008-airflow-local-e-credencial.md) |
| D9: corridas no horário local de NY; máquina e clima em UTC | [ADR 0009](../adr/0009-fuso-horario.md) |
| D10: manter o limite de 1 GiB até a Fase 3 | spec, seção 11.4 |
| D11: ciclo de vida do bucket (fora da Bronze) | ADR 0013 |
| W1 a W4: clima sem ETag, JSON canônico, mês + dia seguinte em UTC, ponto da grade | ADR 0003, ADR 0009, spec 3.3 |

---

## 5. Gate de domínio

Formato híbrido (o mesmo da Fase 1).

### Explicação com as próprias palavras (resumo da avaliação)

| Item | Avaliação |
|---|---|
| Airflow por dentro | Base certa. Impreciso: DAG "sequencial", sensor "dispara DAGs", retry "quando uma condição é atendida". Faltou o porquê dos retries com espera crescente |
| Agendamento, `catchup`, backfill | Firme ("recuperação de dados × de execução"). Faltou nomear o manifesto como fonte do "o que falta" |
| Idempotência | Definição certa; citou 2 de 3 mecanismos; faltou a idempotência do retry |
| HEAD, ETag, Last-Modified, SHA-256 | Firme ("carimbo do conteúdo"). Faltou o JSON canônico do clima |
| Manifesto e linhagem | Impreciso: `mesmo_conteudo` como "arquivo aceito"; vigente por `is_current` (não existe: D5). Faltou a chave da linhagem (`ingest_ts`) |
| Contrato e schema drift | Firme. Impreciso: coluna faltante na TLC "falha" (alerta e segue) |
| Assets e projection | Impreciso: quem gera o evento (a task com `outlets`) e a projection "cria" partições (ela calcula) |

### Autoavaliação (quiz)

| # | Tipo | Resultado |
|---|---|---|
| 1 | Conceitual: sensor × Asset | ✅ |
| 2 | Conceitual: como a view decide a vigente | ✅ |
| 3 | Aplicada: retry depois do upload | ✅ |
| 4 | Aplicada: ETag novo, mesmo conteúdo, hoje e amanhã | ✅ |
| 5 | Diagnóstico: zero linhas sem erro na Bronze | ❌ (atribuiu à política do bucket; é o `ingest_ts` errado + projection) |

As três perguntas sobre os pontos fracos da Parte 1 (2, 3 e 4) foram acertadas.

**Pergunta de entrevista:** "Como garante que rodar de novo não duplica, que a republicação é detectada e que um arquivo com problema não chega ao dashboard?" Boa estrutura (manifesto no centro, funil ETag → SHA-256). Faltaram o retry (`If-None-Match` + política do bucket), a republicação como versão nova preservando a antiga, a quarentena como **proteção** (a falha é só o alarme) e a evidência numérica. Resposta-modelo entregue.

**Mini-checagem:** A (projection calcula e ignora o Glue; zero sem erro) ✅ com ajuste fino; B (arquivo fora do contrato: Bronze, manifesto, vigente, Silver) ✅, com a nuance de que, num mês novo, a Silver não é construída (erro da macro).

**Resultado:** ✅ Passou.

**Reforços para as próximas fases:**
1. Nomear o mecanismo, não só o efeito ("a view calcula", "a task com `outlets`").
2. Separar proteção (vigência, contrato, política) de alarme (task vermelha). O gate de qualidade da Fase 3 segue a mesma lógica.
3. Fechar respostas de entrevista com evidência medida.

---

## 6. Pendências e melhorias anotadas

- **Fase 3:**
  - `OPTIMIZE` + `VACUUM` do manifesto (285 arquivos pequenos em `controle/`);
  - DAG `dbt_build` disparada pelos Assets, perguntando ao manifesto o que mudou; Silver montada mês a mês (32 meses); recalibrar o limite de 1 GiB;
  - Silver do clima (`UNNEST`, UTC → `America/New_York`, recorte do mês local, agregação da hora repetida de novembro);
  - marcar as horas de troca do horário de verão; investigar as 85 corridas da hora inexistente;
  - contrato conferindo também `isAdjustedToUTC`;
  - tabela de zonas da TLC e seeds;
  - alerta de "aguardando" longo.
- **DAGs despausadas:** a `tlc_ingest` roda todo dia às 9h UTC enquanto o Docker estiver ligado no Mac.
- ⚠️ Não verificado: "portfólio = uso não comercial" do Open-Meteo; se o Open-Meteo revisa dados históricos.
