# Glossário

Termos técnicos do projeto, agrupados por afinidade. Dentro de cada grupo, a ordem segue a lógica de aprendizado: do conceito base para o que depende dele. Cada termo entra aqui na primeira vez que aparece numa aula.

---

## Git e GitHub

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **Git** | Sistema que guarda o histórico de mudanças de uma pasta de arquivos | A ficha de manutenção completa de um veículo | 0 |
| **Repositório** | A pasta do projeto junto com todo o seu histórico de mudanças (guardado na subpasta `.git`) | O arquivo da frota: veículos e fichas de manutenção | 0 |
| **Commit** | Um ponto salvo no histórico: a foto da pasta com autor, data e mensagem explicando a mudança | Uma entrada na ficha de manutenção do veículo | 0 |
| **Conventional Commits** | Padrão de mensagem de commit com um prefixo que indica o tipo da mudança: `feat` (funcionalidade), `fix` (correção), `docs` (documentação), `chore` (manutenção) | Códigos padronizados de serviço na ficha da oficina | 0 |
| **`.gitignore`** | Arquivo com a lista de caminhos que o Git deve ignorar (segredos, arquivos gerados, dados) | Lista do que não entra na ficha: objetos pessoais esquecidos no carro | 0 |
| **Branch** | Linha paralela de trabalho dentro do repositório. Permite mudar o código sem afetar a `main` até a mudança ser aprovada | Carro reserva onde se testa uma modificação sem tirar o titular de circulação | 0 |
| **Merge** | Incorporar as mudanças de uma branch em outra (normalmente na `main`) | Aplicar no carro titular a modificação aprovada no reserva | 0 |
| **Push** | Enviar os commits locais para o repositório remoto (GitHub). Até o push, o commit existe só na sua máquina | Enviar a ficha atualizada da filial para a central | 0 |
| **GitHub** | Serviço na nuvem que hospeda repositórios Git e acrescenta colaboração: PR, revisão e CI | A central da frota, que guarda as fichas de todas as filiais | 0 |
| **Pull Request (PR)** | Pedido para incorporar uma branch na `main`, com espaço para revisão e comentários antes do merge | Pedido de aprovação da oficina antes de aplicar a modificação no titular | 0 |
| **CI (integração contínua)** | Testes e verificações que rodam automaticamente a cada mudança enviada ao repositório | Vistoria automática que todo veículo passa ao voltar para o pátio | 0 |

---

## AWS: estrutura da conta

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **Conta AWS** | O contêiner de tudo na AWS: recursos, cobrança e acessos | Uma assinatura/tenant da Microsoft | 0 |
| **AWS Organizations** | Serviço que agrupa contas AWS sob uma conta principal (management account). Foi criado ao ativar o IAM Identity Center | A matriz que administra as filiais | 0 |
| **Região (AWS)** | Local físico onde os recursos ficam (ex.: `us-east-1`, Virgínia do Norte). A maioria dos recursos é regional; o IAM é global | A região da capacidade do Fabric. Pegadinha: um recurso criado numa região "some" se o console estiver em outra | 0 |
| **ARN (Amazon Resource Name)** | Endereço completo e único de um recurso na AWS, ex.: `arn:aws:s3:::meu-bucket/gold/*` | O endereço completo de uma vaga no pátio: filial, setor, número | 0 |

---

## AWS: identidade e acesso (quem pode fazer o quê)

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **IAM (Identity and Access Management)** | Serviço da AWS que decide quem pode fazer o quê em quais recursos. É global (não pertence a uma região) | O sistema de permissões da conta | 0 |
| **Root (usuário raiz)** | O login criado com a conta AWS. Pode tudo, inclusive fechar a conta. Deve ter MFA e não ser usado no dia a dia | A conta que criou o tenant e paga a fatura: só para emergência | 0 |
| **Usuário IAM** | Identidade permanente dentro da conta, com senha e/ou access keys. Neste projeto, não é usado para pessoas | Um service principal com segredo que não expira | 0 |
| **Role (função IAM)** | Identidade sem senha nem chave própria. Quem tem autorização "entra como" ela e recebe credenciais temporárias | O papel que você está usando ao abrir um workspace | 0 |
| **Política IAM (policy)** | Documento JSON que permite (`Allow`) ou nega (`Deny`) ações em recursos. Tudo é negado por padrão; um `Deny` explícito vence um `Allow` | A lista do que um papel pode fazer, só que com milhares de ações possíveis | 0 |
| **Menor privilégio** | Princípio de dar a cada identidade só as permissões necessárias para a sua tarefa, nada além | Dar Viewer a quem só precisa ler o relatório, e não Admin | 0 |
| **Sid (statement ID)** | Nome opcional de uma declaração da política. Serve para documentar a intenção (`BronzeLerEGravarSemApagar`) | O título de uma regra | 0 |
| **Negação implícita × Deny explícito** | Implícita (`implicitDeny`): nenhuma declaração permite, então é negado por padrão. Explícita (`explicitDeny`): uma declaração com `Effect = "Deny"` proíbe e vence qualquer `Allow` | Implícita: você nunca foi adicionado ao workspace. Explícita: você está numa lista de bloqueio | 0 |
| **Ação de bucket × ação de objeto (S3)** | Ações com "Bucket" no nome (`ListBucket`, `GetBucketLocation`) usam o ARN do bucket (`arn:aws:s3:::nome`). Ações de objeto (`GetObject`, `PutObject`, `DeleteObject`) usam o ARN dos arquivos (`arn:aws:s3:::nome/prefixo/*`). Trocar dá `AccessDenied` | Pedir a lista do arquivo morto × abrir uma pasta dele | 0 |
| **Simulador de políticas (IAM)** | Ferramenta da AWS que responde se uma política permitiria uma ação num recurso, sem executar nada (`aws iam simulate-custom-policy`) | Testar uma regra de RLS com "Exibir como" no Power BI | 0 |
| **IAM Identity Center** | Login central da AWS para pessoas, com MFA e credenciais temporárias. Chamava-se "AWS SSO" até 2022 | O **Entra ID** da AWS | 0 |
| **SSO (Single Sign-On)** | Fazer login uma vez e acessar vários lugares. É o que o Identity Center oferece, não um serviço separado | Logar com a conta da empresa e entrar no Power BI, no Teams e no Fabric sem nova senha | 0 |
| **Permission set** | Molde de permissões do Identity Center (ex.: `AdministratorAccess`). Ao ser atribuído a uma conta, vira uma role `AWSReservedSSO_...` | A definição do papel "Admin" do workspace | 0 |
| **Atribuição (assignment)** | A ligação entre quem (usuário), o quê (permission set) e onde (conta AWS) | "Gerenciar acesso → adicionar Ronald como Admin" no workspace | 0 |

---

## AWS: login e credenciais (como você prova quem é)

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **MFA (autenticação multifator)** | Login que exige, além da senha, um segundo fator (app autenticador, passkey ou chave física) | O código do Authenticator no login da Microsoft | 0 |
| **Access key** | Par de chaves (ID + segredo) que dá acesso programático à AWS. É permanente até ser desativada, por isso é o tipo de credencial que mais vaza | Segredo de service principal sem data de validade | 0 |
| **Credencial temporária** | Credencial que expira sozinha (minutos ou horas). É gerada ao entrar como uma role, por exemplo via Identity Center | O token que o Power BI Desktop recebe depois do login e que expira | 0 |
| **PKCE** | Proteção do login pelo navegador: o código devolvido ao `127.0.0.1` só pode ser trocado por credencial por quem guardou um segredo gerado no início (a CLI) | Senha de retirada no balcão: o ticket sozinho não basta | 0 |
| **AWS CLI** | Ferramenta de linha de comando para operar a AWS sem usar o console | Operar a frota por rádio em vez de ir ao pátio | 0 |
| **Perfil (AWS CLI)** | Nome salvo em `~/.aws/config` que aponta para um login, uma conta e uma região. Usado com `--profile <nome>` | As "configurações da fonte de dados" do Power BI Desktop | 0 |

---

## Terraform (infraestrutura como código)

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **IaC (Infraestrutura como Código)** | Descrever a infraestrutura em arquivos de texto versionados, em vez de criá-la clicando no console | O PBIP/TMDL é "modelo como código"; IaC é a mesma ideia para a nuvem | 0 |
| **Terraform** | Ferramenta de IaC declarativa: você descreve o resultado desejado e ela cria, altera ou apaga recursos até a nuvem ficar igual ao código | Como o SQL: você diz o *quê*, não o *como*. Rodar duas vezes não cria duas cópias | 0 |
| **Provider** | Plugin que traduz o código Terraform para a API de uma plataforma (`aws`, `azurerm`, `github`, `fabric`...) | O conector do Power Query | 0 |
| **Resource** | Bloco que descreve uma coisa a existir na nuvem: `resource "<tipo>" "<apelido>" { ... }` | Uma tabela descrita no TMDL | 0 |
| **Variável (`variable`)** | Parâmetro do código, com tipo e valor padrão opcional. Usada como `var.nome`; valores em `terraform.tfvars` | Parâmetro do Power Query | 0 |
| **Referência entre recursos** | Apontar para um atributo de outro recurso (`aws_s3_bucket.datalake.id`). Cria a dependência: o referenciado é criado antes | O `ref()` do dbt; um relacionamento que define a ordem | 0 |
| **`locals`** | Valores calculados dentro do código, derivados de outros valores. Ninguém os passa de fora (diferente de `variable`) | Uma etapa intermediária de uma consulta do Power Query | 0 |
| **Data source (`data`)** | Bloco que LÊ uma informação da AWS (ex.: ID da conta, região) sem criar nada. Usado em `data.<tipo>.<nome>.<atributo>` | Uma consulta somente leitura no Power Query | 0 |
| **`for_each`** | Cria um recurso para cada item de um conjunto ou mapa; dentro do bloco, `each.key` é o item da vez. Registra cada um pelo nome (`camadas["bronze"]`) | Uma coluna calculada: a mesma fórmula aplicada a cada linha | 0 |
| **`terraform console`** | Terminal interativo para testar expressões do Terraform (`local.x`, funções) sem criar nada | Testar uma fórmula DAX numa consulta no DAX Studio | 0 |
| **State (estado)** | Arquivo que liga cada bloco do código ao recurso real (ID na AWS). Sem ele, o Terraform "esquece" o que criou | O de-para entre o código e o que existe de verdade | 0 |
| **Backend** | Onde o estado fica guardado: `local` (a máquina) ou remoto (ex.: `s3`). Não aceita variáveis | Trocar o arquivo local por um no SharePoint | 0 |
| **Lock (trava de estado)** | Arquivo temporário (`.tflock`) que impede duas operações simultâneas sobre o mesmo estado | "Arquivo em uso por outra pessoa" do Excel no SharePoint | 0 |
| **Lock file (`.terraform.lock.hcl`)** | Registra a versão exata de cada provider escolhida no `init`. Vai para o Git | Não confundir com a trava de estado: este fixa versões, aquele impede execuções simultâneas | 0 |
| **`terraform init`** | Prepara a pasta: baixa os providers, cria o lock file e configura o backend | Instalar os conectores antes de abrir o relatório | 0 |
| **`terraform plan`** | Compara código e realidade e mostra o que faria (`+` criar, `~` alterar, `-` apagar, `-/+` recriar). Não muda nada | A comparação entre estágios do Deployment Pipeline do Fabric | 0 |
| **`terraform apply`** | Executa o plano e muda a nuvem. Com plano salvo (`-out`), aplica exatamente o que foi lido | O botão "Implantar" | 0 |
| **Drift (desvio)** | Diferença entre a nuvem e o código, causada por mudança manual fora do Terraform. O próximo `plan` tenta desfazê-la | Alguém editou o relatório publicado direto no Service | 0 |
| **`prevent_destroy`** | Marca (dentro de `lifecycle`) que faz o Terraform recusar qualquer plano que apague o recurso | Uma tabela marcada como "não excluir" | 0 |
| **`-migrate-state` × `-reconfigure`** | Flags do `init` ao trocar de backend: a primeira **copia** o estado; a segunda **ignora** o estado antigo | Mover o arquivo para o SharePoint × criar um arquivo novo em branco lá | 0 |
| **Budget (AWS Budgets)** | Orçamento que envia alertas quando o gasto real (`ACTUAL`) ou previsto (`FORECASTED`) passa de um limite. Só avisa, não bloqueia | Alerta de dados num cartão do Power BI; realizado × projeção de fechamento | 0 |

---

## AWS: armazenamento (S3)

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **S3 (armazenamento de objetos)** | Serviço que guarda arquivos de qualquer tipo, encontrados por uma chave. Base dos data lakes na AWS | A área Files do Lakehouse (OneLake). Quebra: o S3 não tem pastas de verdade | 0 |
| **Bucket** | O contêiner de objetos. Nome único no mundo inteiro, mas mora numa região. Não pode ser renomeado e só pode ser apagado vazio | O Lakehouse | 0 |
| **Objeto** | Um arquivo guardado no S3, com seus metadados | Um arquivo em Files | 0 |
| **Chave (key)** | O nome completo do objeto, com barras: `bronze/tlc_hvfhv/year=2024/arquivo.parquet` | O caminho do arquivo | 0 |
| **Prefixo** | O começo de uma chave (`bronze/`). As "pastas" do console são só prefixos | Um `WHERE chave LIKE 'bronze/%'` | 0 |
| **Versionamento** | Guarda a versão anterior quando um objeto é sobrescrito ou apagado | O histórico de versões do OneDrive | 0 |
| **Bloqueio de acesso público** | Quatro travas que impedem o bucket de ficar público, mesmo por engano | Não existir nenhum link "qualquer pessoa com o link" | 0 |
| **SSE-S3** | Criptografia padrão dos objetos com chaves gerenciadas pela AWS (`AES256`). Ligada por padrão desde 2023 | O disco do notebook criptografado pelo BitLocker | 0 |
| **Regra de ciclo de vida (lifecycle rule)** | Regra do bucket que apaga ou move objetos automaticamente após N dias. Não confundir com o bloco `lifecycle` do Terraform | Política de retenção: "arquivos temporários somem em 7 dias" | 0 |
| **Multipart upload** | Envio de arquivos grandes em pedaços. Pedaços de envios interrompidos ficam invisíveis no console e são cobrados até serem limpos | Uma mudança que parou no meio: caixas largadas no corredor | 0 |

---

## AWS: catálogo e consulta (Glue e Athena)

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **Lakehouse desagregado** | Arquitetura em que armazenamento (S3), catálogo (Glue) e motor SQL (Athena) são serviços separados e trocáveis | No SQL Server, os três vêm na mesma caixa; o Fabric separa por baixo, mas esconde | 0 |
| **Metadados** | Dados sobre os dados: nome da tabela, colunas, tipos, formato, localização | O `INFORMATION_SCHEMA` de um banco SQL | 0 |
| **Glue Data Catalog** | Catálogo de metadados da AWS: diz que o prefixo X no S3 é a tabela Y, com tais colunas. Não guarda dados. "Glue" também nomeia Jobs e Crawlers, que não usamos | O modelo semântico dando nome e forma a arquivos | 0 |
| **Database (Glue)** | Agrupamento lógico de tabelas no catálogo; equivale a um schema do SQL. Não há servidor | Um schema (`bronze`, `silver`, `gold`) | 0 |
| **Amazon Athena** | Motor SQL sem servidor que lê arquivos no S3 usando as definições do Glue. Cobra por dado lido. Usa o Trino por baixo | O endpoint de análise SQL do Lakehouse; quebra: sem capacidade fixa, paga por consulta | 0 |
| **Trino (antigo Presto)** | Motor SQL distribuído open source, que roda por baixo do Athena | O motor por trás do endpoint | 0 |
| **Workgroup (Athena)** | Conjunto de regras para consultas: onde gravar resultados, limite de bytes por consulta, versão do motor | Um workspace com capacidade dedicada: quem consulta por ele herda as regras | 0 |
| **Bytes scanned cutoff** | Limite de bytes lidos por consulta num workgroup. Acima dele, a consulta é cancelada | O freio de mão contra um `SELECT *` caro | 0 |

---

## Power BI

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **PBIP (Power BI Project)** | Formato do Power BI que salva relatório e modelo semântico em arquivos de texto, permitindo ao Git comparar as mudanças linha a linha | O `.pbix` desmontado em peças etiquetadas, em vez de uma caixa lacrada | 0 |
