# Glossário

Termos técnicos do projeto, agrupados por afinidade. Dentro de cada grupo, a ordem segue a lógica de aprendizado: do conceito base para o que depende dele. Cada termo entra aqui na primeira vez que aparece numa aula.

---

## Negócio: mobilidade em Nova York

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **TLC (Taxi and Limousine Commission)** | Órgão da prefeitura de Nova York que regula táxis e aplicativos e publica os dados de corridas, um arquivo por mês | A secretaria de transportes que publica os dados abertos | 3 |
| **HVFHV (High Volume For-Hire Vehicle)** | Categoria da TLC para as empresas de aplicativo de grande volume. No recorte: Uber (`HV0003`) e Lyft (`HV0005`) | — | 3 |
| **Zona de táxi (`LocationID`)** | Divisão da cidade em ~263 zonas numeradas. A corrida só diz a zona de origem e a de destino, nunca o endereço. 264 e 265 = desconhecida e fora de NY (viagens reais, ~4%) | Um CEP curto que agrupa bairros | 3 |
| **MTA (Metropolitan Transportation Authority)** | Autarquia estadual que opera metrô, ônibus, pontes e túneis de NY. Cobra a taxa de congestionamento e publica a lista oficial das zonas de táxi dentro do CBD (fonte do `seed_zonas_cbd`) | — | 3 |
| **CBD (Central Business District)** | O centro comercial de Manhattan, onde se paga a taxa de congestionamento (nome oficial: *Congestion Relief Zone*). No projeto: 38 zonas de táxi da lista da MTA (ADR 0007) | O centro expandido do rodízio de São Paulo | 3 |
| **Taxa de congestionamento (`cbd_congestion_fee`)** | Cobrança para entrar no CBD, desde 05/01/2025. Na TLC, aparece por corrida nos arquivos a partir de 2025-01. É valor em dinheiro: **não** define destino no CBD (nula em 2024; corridas que só atravessam o CBD também pagam, hipótese não verificada) | Pedágio urbano: o rodízio que cobra em vez de proibir | 3 |

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
| **Trust policy (política de confiança)** | Parte da role que diz **quem** pode assumi-la (`assume_role_policy`). A política de permissões diz **o que** a role pode fazer; a trust policy, **quem** pode vesti-la. A `rideshare-airflow` só pode ser assumida pelo usuário `rideshare-airflow-local` | Quem pode usar o crachá de um cargo | 2 |
| **`sts:AssumeRole` (assumir uma role)** | Pedido ao STS (serviço de credenciais temporárias) para "vestir" uma role: devolve uma credencial que expira (`max_session_duration`, 1 hora na do Airflow) | O service principal do Entra ID pegando um token para agir com uma função atribuída | 2 |
| **Política do bucket (resource-based policy)** | Política gravada **no recurso** (o bucket), que vale para **qualquer** identidade que tente usá-lo, inclusive administradores. A política IAM fica **na identidade**. Um `Deny` em qualquer uma das duas vence | A RLS gravada no modelo (vale para quem consultar) × a função do usuário no workspace | 2 |
| **Condição (`Condition`) e `Null`** | Parte opcional de uma declaração que limita quando ela vale. `Null = "true"` significa "a chave de condição está **ausente**" (ex.: o cabeçalho `If-None-Match` não veio) | O "somente se" de uma regra | 2 |
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
| **Variável de ambiente e `.env`** | Valor entregue a um programa pelo ambiente, fora do código. O `airflow/.env` (fora do Git) é lido pelo Astro e vira variáveis dentro dos contêineres. Lugar certo para segredos locais | Parâmetros do Power Query guardados fora da consulta | 2 |
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
| **Bloco `import`** | Diz ao Terraform que um recurso **já existe** na nuvem e deve ser adotado pelo código, sem recriar (`import { to = ..., id = "..." }`). O `plan` mostra "imported from" e só altera o que o código pedir de diferente | Adotar no inventário um veículo que já estava no pátio | 2 |
| **`ignore_changes`** | Lista (dentro de `lifecycle`) de atributos que o Terraform não deve tentar "corrigir": valores que a própria AWS mexe (ex.: `transient_lastDdlTime` do Glue). Evita "mudanças fantasma" em todo `plan` | — | 2 |
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
| **Versão não corrente e marca de apagado (delete marker)** | Com versionamento, sobrescrever deixa a versão antiga **escondida** (não corrente), e "apagar" só põe uma **marca de apagado** por cima. O espaço só é liberado quando uma regra de ciclo de vida expira as versões escondidas (`noncurrent_version_expiration`) e remove a marca que sobrou (`expired_object_delete_marker`) | A lixeira do OneDrive, que só esvazia sozinha se houver regra | 2 |
| **Gravação condicional (`If-None-Match: *`)** | Cabeçalho na gravação que diz "só grave se não existir nada neste caminho". Se existir, o S3 recusa com `412 Precondition Failed` e o objeto fica intacto. Funciona no `put_object` e no `complete_multipart_upload`; o upload gerenciado do boto3 (`upload_file`) **não** repassa | `INSERT` numa tabela com chave primária × upsert | 2 |
| **Checksum na gravação (`ChecksumSHA256`)** | O SHA-256 enviado junto com o arquivo; o S3 recalcula e recusa o upload se não bater. Prova de ponta a ponta de que a Bronze guarda exatamente o que veio da TLC | O lacre conferido na entrega | 2 |
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
| **Mínimo cobrado por consulta (Athena)** | Cada consulta é cobrada por pelo menos 10 MB lidos, mesmo que leia menos (⚠️ regra de preço da AWS, não reconferida na Fase 4). No DirectQuery, muitos visuais pequenos somam muitos mínimos | Bandeirada do táxi | 4 |
| **Particionamento estilo Hive** | Organizar os arquivos em prefixos `coluna=valor` (`year=2025/month=01/`) para o motor ler só as pastas que interessam. Cada partição deve ter dezenas a centenas de MB | A atualização incremental do Power BI (partições por período); o arquivo morto com uma pasta por mês | 1 |
| **Coluna de partição** | Coluna que não existe dentro do arquivo: o motor a lê do caminho (`year`, `month`, `ingest_ts`) | A etiqueta da pasta, não o conteúdo da folha | 1 |
| **JsonSerDe e arrays no Athena** | Leitor de JSON do Athena: um objeto por linha. Listas viram `array<...>` dentro de uma coluna `struct`; para virar uma linha por item, usa-se `CROSS JOIN UNNEST(...)` | Expandir uma coluna de lista no Power Query | 2 |
| **Partition pruning** | O motor pula pastas inteiras olhando só o caminho, sem abrir arquivos. Só acontece com filtro na coluna de partição | Ir direto à estante certa | 1 |
| **Registro de partição** | O Glue precisa saber que uma pasta nova existe: `ALTER TABLE ADD PARTITION` (à mão), `MSCK REPAIR TABLE` (varre as pastas) ou partition projection (o Athena deduz o padrão). Sem isso, a pasta é invisível | Cadastrar a pasta nova no índice do arquivo morto | 1 |
| **Partition projection** | O Athena **calcula** as partições a partir de regras nas propriedades da tabela, em vez de pedir a lista ao Glue. Tipos: `integer`, `date` (aceita `NOW`, calculado em UTC), `enum`, `injected`. Ao ligar, o Athena **ignora** as partições registradas no Glue; partição sem pasta ou fora da faixa devolve zero linhas sem erro; `SHOW PARTITIONS` não a mostra; só vale no Athena | A regra na parede ("uma pasta por mês, desde jan/2024") no lugar do fichário; no Power Query, gerar a lista de caminhos com `List.Dates` em vez de digitá-la | 2 |
| **Projection `injected`** | Tipo de projection para valor imprevisível (só `string`): a consulta **tem que** informar o valor no `WHERE`, senão falha. Na Bronze, aplicado a `ingest_ts`, impede ler todas as versões de um mês sem querer | O arquivista que só busca se você disser qual versão da pasta quer | 2 |
| **Tabela externa** | O catálogo só aponta para arquivos geridos por outra pessoa/processo. `DROP TABLE` apaga só a definição. Usada na Bronze | Files e shortcuts do Lakehouse | 1 |
| **Tabela gerenciada** | O motor/formato de tabela é dono dos arquivos: cria, reescreve e apaga. `DROP TABLE` apaga os dados. Usada na Silver e na Gold (Iceberg) | Tables (Delta) do Lakehouse | 1 |
| **Schema-on-read** | A definição da tabela é aplicada na hora da leitura: um tipo errado no `CREATE` só dá erro no primeiro `SELECT` | Um rótulo colado na caixa: só ao abrir você descobre se bate com o conteúdo | 1 |
| **Versões de tabela (Glue)** | Cada alteração de uma tabela guarda a definição anterior no Glue. O dbt-athena lê e apaga versões antigas (`GetTableVersions`, `BatchDeleteTableVersion`): sem essa permissão, o Cosmos falhou no primeiro run | O histórico de versões de um arquivo no OneDrive | 3 |

---

## Docker e rede local

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **Docker** | Ferramenta que empacota um programa com tudo de que ele precisa (sistema, bibliotecas, configuração) para rodar isolado e igual em qualquer máquina. No Mac, roda dentro de uma máquina virtual Linux | Um contêiner de navio: vai lacrado e funciona igual em qualquer porto | 0 |
| **`docker-compose.override.yml`** | Arquivo que o Astro junta aos contêineres que ele sobe. Usado para a "TLC de mentira" (nginx). O serviço extra precisa estar na rede `airflow` para ser achado pelo nome | — | 2 |
| **Dockerfile** | Arquivo de texto com as instruções para montar uma imagem | A receita escrita | 0 |
| **Imagem** | Pacote congelado e somente leitura, montado a partir do Dockerfile | A marmita pronta no congelador; um `.pbit` (template) | 0 |
| **Contêiner** | Uma imagem em execução. Dá para ter vários da mesma imagem. Mudanças dentro dele somem quando ele é apagado | A marmita aquecida e servida; um relatório aberto a partir do `.pbit` | 0 |
| **Volume** | Pasta persistente "emprestada" a um contêiner; sobrevive quando o contêiner é recriado | Um HD externo que você pluga em qualquer computador | 0 |
| **Porta** | Número que identifica um serviço numa máquina (`8080` = UI do Airflow, `5432` = Postgres). Dois serviços não podem usar a mesma porta | O ramal de um telefone: mesmo número da empresa, ramais diferentes | 0 |
| **localhost / 127.0.0.1** | O endereço da própria máquina | "Eu mesmo" | 0 |
| **DNS** | Sistema que traduz nomes (`airflow.localhost`) em endereços numéricos (`127.0.0.1`). O Safari pergunta ao macOS; Chrome e `curl` resolvem `*.localhost` sozinhos | A lista telefônica: nome → número | 0 |

---

## Airflow (orquestração)

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **Apache Airflow** | Orquestrador: define quais tarefas existem, em que ordem e quando rodam, com retry e histórico. Escrito em Python. Por princípio, manda outros processarem; não processa dados pesados | O Data Factory/pipeline do Fabric, só que em código | 0 |
| **DAG** | Fluxograma de tarefas sem ciclos, definido num arquivo Python | Um pipeline do Fabric | 0 |
| **Task** | Uma etapa da DAG | Uma atividade do pipeline | 0 |
| **Task instance** | Uma execução específica de uma task, numa execução da DAG. Tem estado próprio (`success`, `failed`, `up_for_retry`, `up_for_reschedule`, `upstream_failed`, `skipped`...) | A task é a medida; a task instance é o valor dela numa célula da matriz | 2 |
| **Operator** | Molde de task: classe Python que já sabe fazer um tipo de trabalho (rodar comando, consultar o Athena, copiar no S3). Preenchidos os parâmetros, vira task | Os tipos de atividade do pipeline do Fabric (Copy, Notebook). Quebra: no Airflow a lista é aberta, dá para escrever o seu | 2 |
| **Provider (Airflow)** | Pacote que traz operators, sensors e conexões de um sistema (AWS, HTTP...). No Airflow 3, até os básicos (`BashOperator`) mudaram para o `apache-airflow-providers-standard` | Um conector instalável do Power Query | 2 |
| **TaskFlow (`@task`)** | Forma moderna de criar task: um decorator que transforma uma função Python numa task. O `return` da função vai para a próxima task | Escrever a etapa como função, em vez de configurar uma atividade | 2 |
| **XCom** | Mecanismo para uma task passar um valor **pequeno** para outra (ex.: o caminho do arquivo no S3). Fica no banco de metadados; não serve para passar dados | Um post-it entre turnos, não um caminhão | 2 |
| **Sensor** | Operator que espera uma condição ficar verdadeira (arquivo aparecer, hora chegar). Atendida a condição, libera as próximas tasks | O porteiro esperando o caminhão-cegonha; no Fabric, Get Metadata + Until | 2 |
| **Modos do sensor** | `poke`: ocupa o slot o tempo todo. `reschedule`: libera o slot entre as checagens (estado `up_for_reschedule`). Deferrable: a espera vai para o triggerer; só funciona se o sensor tiver suporte e o triggerer estiver rodando | Porteiro parado no portão × que confere de hora em hora × que deixa um interfone | 2 |
| **Slot** | Vaga de execução. O número de tasks rodando ao mesmo tempo é limitado | Vaga de mecânico na oficina | 2 |
| **`soft_fail`** | No sensor: ao estourar o `timeout`, marca `skipped` em vez de `failed`. Para esperas em que "ainda não chegou" é normal | "Sem entrega hoje" não é ocorrência | 2 |
| **Retries** | Quantas vezes o Airflow tenta de novo uma task que falhou (`retries`, `retry_delay`). Ajuda em erro **transitório** (rede, 503); não em erro **determinístico** (dado fora do contrato). Roda a task inteira de novo, por isso exige idempotência | Rediscagem automática do telefone | 2 |
| **Backoff exponencial** | Espera crescente entre as tentativas (2, 4, 8 minutos...), com teto (`max_retry_delay`). Dá tempo ao servidor de se recuperar | Rediscar cada vez mais espaçado | 2 |
| **`execution_timeout`** | Tempo máximo de **cada tentativa** de uma task; estourou, a tentativa falha e pode ser repetida. Diferente do `timeout` do sensor, que limita a espera inteira | Limite de tempo por tentativa de conserto | 2 |
| **Trigger rule** | Regra que decide quando uma task roda, olhando as anteriores. Padrão `all_success` (todas deram certo). `all_done` = roda quando todas terminaram, com sucesso ou não (o `publicar` da `tlc_ingest`, para os meses bons seguirem mesmo com um mês falho) | "Só começa a lavagem quando todos os carros do lote chegaram" × "quando o caminhão terminar de descarregar, com ou sem avaria" | 2 |
| **Falha sem retry (`AirflowFailException`)** | Exceção que marca a task como falha **sem** tentar de novo. Para erro determinístico: mês em `erro` ou em quarentena. Retry só serviria para baixar 480 MB à toa | — | 2 |
| **Run verde escondendo falha** | O Airflow decide o estado do run pelas **últimas** tasks. Se a última usa `all_done` e termina bem, o run fica verde mesmo com uma task vermelha no meio. A `tudo_certo` (regra padrão) existe para o run terminar como falho | — | 2 |
| **Trigger rule `none_failed`** | Roda se nenhuma task anterior **falhou**, mesmo que alguma tenha sido pulada. A `tudo_certo` da `dbt_build` usa para rodar também quando não havia mês a construir (o pedido impossível não passa em silêncio) | — | 3 |
| **`map_index_template`** | Nome de cada cópia de uma task mapeada na grade do Airflow (ex.: o mês `2025-03` em vez de `0`, `1`, `2`) | — | 2 |
| **`airflow dags test`** | Roda a DAG uma vez, direto no terminal, sem o scheduler e sem despausar o agendamento. Usado na etapa 8 com `ambiente=teste` | Testar a atualização no Desktop antes de publicar | 2 |
| **Cosmos** | Biblioteca da Astronomer que lê o projeto dbt e transforma cada model numa task do Airflow (por padrão, com os testes logo depois). Visibilidade por model, retry só do que falhou e o gate de qualidade visível na grade. Alternativa caixa-preta: uma task com `dbt build` | Ordem de serviço com cada item separado × "revisão completa"; histórico de atualização por tabela | 3 |
| **`DbtDag` × `DbtTaskGroup`** | O projeto dbt vira uma DAG inteira, ou um grupo de tasks dentro de uma DAG nossa (com tasks antes e depois, como consultar o manifesto e publicar um Asset) | — | 3 |
| **`ProfileConfig` e profile mapping** | Como o dbt conecta ao banco dentro do Cosmos: o `profiles.yml` ou uma Connection do Airflow. O `AthenaAccessKeyProfileMapping` pede ao Airflow uma credencial temporária, vestindo a role da `aws_default` | — | 3 |
| **`ExecutionConfig` e ambiente virtual do dbt** | Onde o dbt roda (no worker, num ambiente virtual ou num contêiner). Recomendado no Astro: um ambiente virtual só do dbt no `Dockerfile` (`dbt_executable_path`), porque o dbt-athena e o Airflow podem exigir versões diferentes das mesmas bibliotecas | Cada mecânico com a sua caixa de ferramentas | 3 |
| **Schedule** | Quando a DAG roda (`@daily`, cron, ou por Asset) | Gatilho de agendamento | 0 |
| **Cron** | Notação de agendamento do Unix com cinco campos: minuto, hora, dia, mês, dia da semana (`0 6 * * *` = todo dia às 6h). `@daily` e `@monthly` são atalhos | "Todo dia às 6h" da atualização agendada do Power BI | 2 |
| **DAG run** | Uma execução da DAG inteira, criada pelo schedule, por um backfill ou manualmente. Cada DAG run tem suas task instances | Uma atualização do histórico de atualizações do Power BI | 2 |
| **`logical_date`** | A "etiqueta de data" de um DAG run, que o código pode usar para saber qual período processar. Não é necessariamente o momento em que o run rodou | O parâmetro de período passado ao pipeline | 2 |
| **Intervalo de dados (data interval)** | Período que um DAG run cobre (`data_interval_start`/`end`). ⚠️ No Airflow 3, agendamento cron por padrão não tem intervalo (início = fim = momento do disparo); no Airflow 2, o run do dia X cobria o dia X e rodava depois que ele terminava. Configuração: `create_cron_data_intervals` | — | 2 |
| **`catchup`** | Se, ao ligar a DAG, o Airflow cria runs para todos os intervalos perdidos desde o `start_date`. ⚠️ Padrão `False` no Airflow 3 (era `True` no 2). Recupera **execuções**, não carrega histórico | O gestor que volta das férias e faz (ou não) as vistorias atrasadas. O agendamento do Fabric não recupera | 2 |
| **Backfill** | Rodar a DAG para um período do passado, sob demanda (`airflow backfill create --from-date ... --to-date ...`), com paralelismo controlado (`--max-active-runs`). Segue o schedule da DAG: DAG diária gera um run por dia | Um ForEach do Fabric passando a lista de meses como parâmetro | 2 |
| **Arquivo órfão** | Arquivo gravado no armazenamento sem registro no controle que diz o que vale (manifesto, metadados do Iceberg). Nasce quando um processo cai entre "gravar o arquivo" e "registrar o arquivo" | Carro no pátio sem ficha no sistema da frota | 2 |
| **Asset** (no Airflow 2: Dataset) | Representa um dado. Uma task "publica" o Asset ao terminar, e outras DAGs podem rodar quando ele é atualizado. A URI é só um nome: o Airflow não confere o S3, confia na task | "Executar quando o arquivo chegar". Ao contrário do "Invoke pipeline" do Fabric, o produtor não conhece o consumidor | 0 |
| **Evento de Asset (`outlets`)** | Registro de que um Asset foi atualizado. Só sai quando a task que o declara em `outlets` termina **com sucesso** (`skipped` ou `failed` não geram). Vários eventos antes de o consumidor rodar podem virar **um** run só | A sirene do recebimento: toca só quando o lote foi conferido | 2 |
| **Connection (Airflow)** | Cadastro de como chegar num sistema externo (tipo, login, segredo, extras). As tasks pedem a connection pelo ID (`aws_default`), sem ver o segredo. Uma variável `AIRFLOW_CONN_<ID>` cria a connection a partir do ambiente | A credencial de uma fonte de dados no Power BI Service | 2 |
| **DAG pausada** | Estado inicial de toda DAG nova: não roda até ser ligada (toggle) | Pipeline criado mas com o gatilho desativado | 0 |
| **Dynamic task mapping** | Uma task que vira N instâncias em tempo de execução, uma por item de uma lista (`map_index` 0, 1, 2...) | O `for_each` do Terraform, só que decidido na hora de rodar | 0 |
| **Scheduler** | Componente que decide quando cada task está pronta para rodar | O gerente de pátio com o cronograma | 0 |
| **DAG processor** | Componente que lê os arquivos Python das DAGs. Código solto no arquivo roda a cada leitura | O planejador que lê as ordens de serviço | 0 |
| **Executor** | Define onde e como as tasks rodam. `LocalExecutor`: no próprio scheduler. Celery/Kubernetes: em workers separados | O modelo de oficina: um mecânico só ou uma equipe | 0 |
| **Banco de metadados** | Banco (Postgres) onde o Airflow guarda tudo: execuções, estados, histórico. Tabelas como `dag_run` e `task_instance` | O livro de registro da oficina | 0 |
| **API server** (no Airflow 2: webserver) | Componente que serve a interface web e a API REST | O painel do escritório | 0 |
| **Triggerer** | Componente que cuida de tarefas que ficam esperando um evento, sem ocupar um worker | O porteiro que avisa quando o caminhão chegar | 0 |
| **Astro Runtime** | Imagem Docker do Airflow empacotada pela Astronomer (ex.: `runtime:3.3-9` = Airflow 3.3) | A distribuição "pronta para usar" do Airflow | 0 |
| **Astro CLI** | Ferramenta que cria o projeto (`astro dev init`) e sobe o Airflow local em contêineres (`astro dev start`). `astro dev stop` preserva os dados; `astro dev kill` apaga os volumes | O instalador e o painel de liga/desliga do Airflow local | 0 |
| **`TriggerDagRunOperator`** | Task que dispara **outra DAG**, passando parâmetros (`conf`). Com `wait_for_completion=True`, espera ela terminar e herda o resultado: se a DAG disparada falha, a task falha. A `construir_mes` da `dbt_build` dispara uma `dbt_mes` por mês | O despachante que abre a OS na oficina e fica esperando o carro sair | 3 |
| **`max_active_tis_per_dagrun`** | Quantas cópias de uma task mapeada rodam ao mesmo tempo no mesmo run. Com 1, os meses saem um por vez, na ordem do `map_index` (o gate de um mês compara com os 3 anteriores) | Uma baia só no lava-rápido: a fila anda na ordem de chegada | 3 |
| **`max_active_runs`** | Quantos runs da mesma DAG podem rodar juntos. Com 1, dois disparos não decidem nem gravam o mesmo mês ao mesmo tempo | — | 3 |
| **Teste destacado (Cosmos)** | Teste com dois "pais" (ex.: reconciliação Silver × Gold) vira uma task própria, que roda depois dos dois (`should_detach_multiple_parents_tests`) | — | 3 |
| **`airflow dags reserialize`** | Força o DAG processor a ler os arquivos de novo e atualizar a versão das DAGs guardada no banco. Resolveu a DAG nova que não aparecia | Atualizar o cache do relatório | 3 |

---

## Ingestão: HTTP, versões e manifesto

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **HTTP** | A "língua" dos pedidos a servidores web. Cada pedido tem um método (`GET` = me manda o arquivo; `HEAD` = só os dados sobre ele) e a resposta traz um código de status e cabeçalhos | — | 2 |
| **Código de status HTTP** | Número que resume a resposta: `200` ok, `304` não mudou, `403` proibido, `404` não existe. Um S3 que não permite listar responde **403** (não 404) para arquivo inexistente: na TLC, mês ainda não publicado dá 403 | — | 2 |
| **HEAD (requisição HTTP)** | Pede só os cabeçalhos de um arquivo (tamanho, data, ETag), sem baixar o conteúdo. Menos de 1 KB contra ~480 MB do arquivo | O conector Pasta do Power Query mostra `Date modified` e tamanho sem abrir os arquivos | 1 |
| **ETag / Last-Modified** | Cabeçalhos que identificam a versão de um arquivo na web. ETag igual = mesmo arquivo; ETag diferente = **provavelmente** outro (o mesmo conteúdo reenviado em partes de outro tamanho ganha outro ETag). Com sufixo `-N`, o ETag veio de upload em N partes e não é um hash do conteúdo. Opaco: só se compara igualdade | O número do lote impresso na embalagem (ETag) e a data da última vistoria (Last-Modified) | 1 |
| **Hash (SHA-256)** | "Impressão digital" de um arquivo, calculada do conteúdo: qualquer byte diferente gera um hash totalmente diferente. Calculado por nós depois de baixar; é a prova de que o conteúdo mudou | O número do chassi: identifica aquele exato veículo | 1 |
| **Pedido condicional** | O cliente manda o ETag que já tem (`If-None-Match`); se nada mudou, o servidor responde `304 Not Modified` sem mandar o arquivo | "Só me mande se mudou" | 2 |
| **CDN (CloudFront)** | Rede de servidores que entrega arquivos perto de quem pede. A TLC guarda os arquivos num S3 e os entrega pelo CloudFront, a CDN da AWS | Filiais de distribuição de um mesmo depósito | 2 |
| **Republicação** | A fonte substitui um arquivo já publicado (correção). Detectada por ETag diferente e confirmada por SHA-256 diferente; vira nova versão na Bronze (novo `ingest_ts`), que passa a ser a vigente na view `manifesto_vigente` | Recall: o fornecedor troca um lote já entregue | 2 |
| **JSON canônico** | O JSON reescrito sempre do mesmo jeito: sem campos voláteis (`generationtime_ms`), chaves em ordem fixa, numa linha só. Mesma informação → mesmos bytes → mesmo SHA-256. Permite detectar mudança numa API sem ETag | Classificar as colunas e remover o carimbo de data antes de comparar duas versões no Power Query | 2 |
| **Campo volátil** | Campo que muda a cada pedido sem ser dado (ex.: tempo de processamento do servidor). Se entrar no hash, toda resposta parece "nova" | O número do protocolo de atendimento: muda a cada ligação, o assunto é o mesmo | 2 |
| **Célula da grade (modelo meteorológico)** | O modelo divide o mapa em quadrados; a API devolve o valor do quadrado mais próximo do ponto pedido. Pedimos Central Park (40.78, −73.97) e recebemos o centro da célula (40.81, −74.02), a ~4 km | O pixel de um mapa de calor | 2 |
| **Manifesto de ingestão** | Tabela de controle (`controle.ingestion_manifest`, Iceberg, só de acréscimo) com uma linha por **evento** de ingestão: origem, mês, URL, ETag, SHA-256, linhas, schema, caminho, `ingest_ts`, `status` (`aceito`, `rejeitado`, `mesmo_conteudo`), motivo e run do Airflow. Decide o que baixar, diz o que vale (pela view `manifesto_vigente`; não há coluna `is_current`) e guarda a linhagem. Gravado **por último** (a linha é o commit). Não confundir com os manifestos internos do Iceberg | O livro de entrada do pátio; no Fabric, a tabela de controle de um pipeline guiado por metadados | 2 |
| **Linhagem (lineage)** | Rastrear um dado até a origem. De objetos: qual tabela alimenta qual (DAG do dbt). De dados: esta linha veio de qual arquivo e versão (manifesto + `ingest_ts` na Silver) | A exibição de linhagem do workspace do Power BI (só o nível de objetos) | 2 |
| **View `manifesto_vigente`** | Consulta salva sobre o manifesto que devolve a versão **aceita mais recente** de cada fonte e mês (`row_number()` por mês, ordem decrescente de `ingest_ts`, fica a nº 1). É onde o `is_current` "mora": vigente é o que aparece nela | Um `RANKX` por mês filtrando o 1º lugar | 2 |
| **Status `mesmo_conteudo` (conferência)** | Linha do manifesto que registra "ETag novo, conteúdo idêntico ao da última versão". Nenhum arquivo entra; a linha copia o `ingest_ts` da versão existente e guarda o ETag novo, para o run seguinte não baixar tudo de novo | No extrato do banco: "consulta de saldo", não "depósito" | 2 |
| **Injeção de SQL e escape de aspas** | Texto vindo de fora, colado direto num SQL, pode quebrá-lo ou virar comando. Aspas simples dentro de um texto viram duas (`d'água` → `'d''água'`) | — | 2 |
| **`IS NOT DISTINCT FROM`** | O `=` que trata `NULL` como valor: `NULL IS NOT DISTINCT FROM NULL` é verdadeiro (com `=`, dá "desconhecido") | `==` × `=` com `BLANK()` no DAX | 2 |
| **Teste de mesa** | Simular o código à mão, linha por linha, anotando o valor de cada condição. Usado para entender o `etag_conhecido` da `decidir_acao` | Avaliar um `FILTER` do DAX linha a linha | 2 |
| **Schema drift** | Mudança no schema da fonte ao longo do tempo, sem aviso: coluna nova (alertar e seguir), coluna faltante (alertar), tipo diferente (parar e decidir). Na TLC: `cbd_congestion_fee` a partir de 2025-01; `PULocationID` INT64 até 2022 e INT32 depois | O `Expression.Error: The column ... wasn't found` do Power Query na atualização | 1 |
| **Contrato de schema** | Documento explícito e versionado (no Git) com as colunas e tipos esperados e desde quando. Cada arquivo é conferido contra ele na ingestão. A referência é uma **decisão**, não "o que veio no mês passado". "Data contract", no mercado, é mais amplo (acordo entre produtor e consumidor, com dono, significado e prazos) | A ficha de especificação do pedido de compra, conferida no recebimento | 2 |
| **`schema_hash`** | Hash da lista `nome:tipo` das colunas (lida só do rodapé do Parquet). Igual a um hash aprovado = schema ok, sem comparar coluna a coluna. O que entra no hash (ordem, maiúsculas) define o que conta como drift | A impressão digital da ficha técnica | 2 |
| **Promoção de tipo (alargar × estreitar)** | Alargar (INT32 → INT64, `float` → `double`) não perde informação; estreitar pode estourar valores; mudar de família (número → texto) quebra contas. O Iceberg aceita promoções seguras sem reescrever arquivos | Trocar a caixa por uma maior × por uma menor | 2 |
| **Tipo nulo (NullType)** | Tipo que um gravador de Parquet usa quando a coluna inteira está vazia e ele não sabe o tipo. É compatível com qualquer tipo no schema, mas uma coluna 100% nula é um alerta de **qualidade** | Campo da ficha que veio em branco | 2 |
| **UTC e `isAdjustedToUTC`** | UTC: horário de referência mundial, sem horário de verão. No Parquet, `isAdjustedToUTC = false` marca um horário "de relógio de parede", sem fuso. É o caso dos arquivos da TLC: o fuso não está no dado, precisa de decisão (ADR 0009) | Horário anotado na ficha sem dizer de qual cidade | 2 |
| **Registro de construção (checkpoint)** | Tabela `controle.dbt_meses_construidos` (só INSERT): uma linha por mês construído **com sucesso**, por ambiente, com as versões que a Silver leu e o motivo. Responde "a Gold já foi feita a partir da versão vigente?" (ADR 0016) | O manifesto é o livro de entrada do almoxarifado; o registro é a ficha de cada OS concluída, com o lote das peças usadas | 3 |
| **Regra de pendência** | ✍️ do Ronald: decide **SE** um mês é construído. Sem versão vigente: espera. Registro ≠ manifesto: constrói (`manifesto`). Forçado: constrói (`forcado`). Senão: nada. **QUAL** versão é lida, quem decide é a macro `ingest_ts_vigente` | — | 3 |
| **`forcar_meses`** | Parâmetro da `dbt_build` para reconstruir meses já em dia (ex.: depois de mudar o código do dbt, que o registro não detecta). Pedido impossível deixa o run vermelho no fim | Recall: chamar de volta carros que já saíram da oficina | 3 |

---

## Arquivos e formatos de dados

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **Armazenamento colunar** | Guardar uma tabela coluna por coluna, e não linha por linha. Ler uma coluna não obriga a ler as outras; valores parecidos juntos comprimem muito | O VertiPaq do Power BI | 1 |
| **Parquet** | Formato de arquivo colunar, comprimido, com tipos preservados e um rodapé com schema e estatísticas. Não pode ser editado: mudar uma linha exige reescrever o arquivo | As tabelas Delta do Lakehouse no Fabric são pastas de arquivos Parquet + um log | 1 |
| **Row group** | Bloco de linhas dentro de um arquivo Parquet; cada coluna do bloco é guardada e comprimida separadamente, com seu min/max | Um capítulo do livro, com o resumo do capítulo | 1 |
| **Footer (rodapé)** | Final do arquivo Parquet com o schema, a lista de row groups e as estatísticas de cada coluna. É lido primeiro | O sumário do livro | 1 |
| **Predicate pushdown** | O motor usa as estatísticas (min/max) para pular row groups que com certeza não atendem ao `WHERE`. Pula quando o intervalo [min, max] inteiro fica fora do filtro. Só é eficaz se os dados estiverem minimamente ordenados | Pular os capítulos que o sumário prova não ter o que você procura | 1 |
| **Dictionary encoding** | Compressão que guarda cada texto distinto uma vez e substitui as repetições por números | "Manhattan" guardado uma vez; as linhas guardam só o código 1 | 1 |
| **Small files problem** | Muitos arquivos pequenos deixam a leitura lenta e cara: cada arquivo exige abrir o rodapé e uma requisição ao S3 | Mil envelopes de uma folha × um fichário | 1 |
| **CSV** | Texto separado por vírgulas: sem tipos, sem compressão inteligente, guardado por linha | Planilha exportada como texto | 1 |
| **DuckDB** | Motor SQL que roda localmente e lê Parquet direto (inclusive pela internet). Usado só para inspeção; não faz parte da arquitetura | Um "Athena de bolso" | 1 |

---

## Iceberg (formato de tabela)

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **Formato de tabela (table format)** | Camada de metadados sobre arquivos (ex.: Parquet) que os transforma numa tabela com transações, versões e schema controlado. Exemplos: Iceberg, Delta, Hudi | A lista oficial da frota sobre os carros | 1 |
| **Apache Iceberg** | Formato de tabela aberto e neutro de fornecedor, lido por Athena, Spark, Trino, Snowflake etc. Usado na Silver e na Gold (ADR 0002). No Athena é tabela gerenciada: `DROP TABLE` apaga os dados | A tabela Delta do Fabric (concorrente com a mesma proposta) | 1 |
| **Metadados do Iceberg** | `metadata.json` (schema, partições, histórico), manifest list (arquivos de um snapshot) e manifestos (arquivos + min/max). O catálogo guarda só o ponteiro para o `metadata.json` vigente | O `_delta_log` do Delta | 1 |
| **Snapshot** | Uma versão da tabela **inteira** (a lista de arquivos que a formam), criada a cada escrita (commit). Não registra mudança linha a linha | A lista da frota de uma data | 1 |
| **Transação ACID / commit atômico** | Cada escrita é "tudo ou nada": quem lê vê a versão anterior inteira ou a nova inteira, nunca a metade. O commit é a troca atômica do ponteiro no catálogo | Trocar a lista do quadro de avisos num gesto só | 1 |
| **Time travel** | Consultar uma versão antiga da tabela (`FOR TIMESTAMP AS OF` / `FOR VERSION AS OF`). Só lê; não restaura | Ler a lista antiga no arquivo morto | 1 |
| **Rollback** | Tornar vigente de novo uma versão antiga. Diferente de time travel | Recolocar a lista antiga no quadro | 1 |
| **Evolução de schema** | Acrescentar, renomear ou remover colunas sem reescrever os arquivos antigos (colunas identificadas por ID, não por nome) | Renomear uma coluna no modelo sem reimportar os dados | 1 |
| **Partição oculta (hidden partitioning)** | Particionar por uma transformação (`month(pickup_datetime)`): quem consulta filtra a coluna normal e a poda acontece sozinha | O motor sabe que a pasta "janeiro" corresponde às datas de janeiro | 1 |
| **Sobrescrita por partição** | Substituir atomicamente só uma partição (ex.: `source_month=2025-01`). Base do reprocessamento idempotente. O Iceberg suporta; o dbt-athena não expõe (ver `insert_overwrite` em Estratégia incremental) | Atualização incremental do Power BI refazendo só um período | 1 |
| **OPTIMIZE (compactação)** | Junta arquivos pequenos de uma tabela Iceberg em arquivos maiores | Juntar folhas avulsas num fichário | 1 |
| **VACUUM (expiração de snapshots)** | Expira snapshots antigos e apaga os arquivos que nenhuma versão vigente usa. Depois disso, aquele passado não existe mais: **o prazo de retenção é o limite do time travel**. No Athena: `vacuum_max_snapshot_age_seconds` (padrão 5 dias) e `vacuum_min_snapshots_to_keep` (padrão 1); só roda quando alguém executa. Sem `s3:DeleteObject`, o comando "dá certo" mas não apaga nada | Descartar listas antigas do arquivo morto e os carros que só elas citavam | 1 |
| **Arquivo órfão (Iceberg)** | Arquivo de dados que nenhuma versão vigente usa mais: sobra de delete + append ou de commit que falhou. Só o `VACUUM` o apaga, e só depois da retenção. Medido: a `int` de dev tinha 11,87 GB no S3 para 8,74 GB vivos | — | 3 |

---

## dbt (transformação)

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **ELT** | Extrair e carregar o dado bruto primeiro (Bronze), transformar depois, dentro do warehouse. O dbt é o "T" | Carregar a fonte no Power BI e transformar no Power Query | 1 |
| **dbt (data build tool)** | Ferramenta em que cada transformação é um `SELECT` num arquivo; o dbt monta o SQL completo, manda o Athena executar e cuida da ordem, dos testes e da documentação. Não processa dados nem agenda nada | O Power Query escrito em SQL e versionado no Git | 1 |
| **Projeto dbt (`dbt_project.yml`)** | Arquivo que define o projeto: nome, pastas e configurações padrão por pasta | As configurações do arquivo PBIP | 1 |
| **`profiles.yml` e target** | Como o dbt se conecta ao warehouse. Cada target (`dev`, `prod`) aponta para bancos diferentes | Trocar a fonte de dados entre homologação e produção | 1 |
| **Adaptador (dbt-athena)** | Plugin que traduz o dbt para um warehouse específico (Athena, BigQuery, Databricks, Fabric...) | O conector do Power Query | 1 |
| **Source** | Tabela que vem de fora do dbt, declarada em YAML e usada com `{{ source('tlc', 'hvfhv') }}`. Fica na fronteira | A fonte de dados de uma consulta | 1 |
| **Model** | Um arquivo `.sql` com um `SELECT`. O nome do arquivo vira o nome da tabela; o dbt escreve o `CREATE` | Uma consulta do Power Query | 1 |
| **`ref()`** | Referência a outro model: define a ordem (DAG), troca o banco conforme o ambiente e registra a linhagem | "Referência" no Power Query | 1 |
| **Jinja e compilação** | O `{{ }}` é Jinja (modelo de texto). O dbt compila para SQL puro antes de executar; o resultado fica em `target/compiled/`. Erro de Jinja falha antes de chegar ao Athena | Uma fórmula com parâmetros que vira o valor final | 1 |
| **Materialização** | Como o resultado do model existe: `view` (consulta salva, recalcula a cada leitura), `table` (reconstruída inteira), `incremental` (só o novo), `ephemeral` (vira CTE) | "Habilitar carga", atualização completa e incremental do Power BI | 1 |
| **`is_incremental()`** | Macro que diz se o model está rodando em modo incremental; usada para filtrar só o dado novo | O filtro `RangeStart`/`RangeEnd` da atualização incremental | 1 |
| **Estratégia incremental** | Como o pedaço novo entra na tabela: `insert_overwrite` (substitui partições), `append` (só acrescenta; pode duplicar), `merge` (linha a linha pela `unique_key`; não apaga o que sumiu da fonte). No dbt-athena, tabelas Iceberg aceitam só `append`, `merge` e `microbatch` (por isso o ADR 0014) | — | 1 |
| **Chave surrogate** | Identificador criado por nós quando o dado não traz um: hash das colunas da própria linha. Mesma linha → mesma chave, sempre. Precisa de colunas suficientes para separar registros reais: em jan/2025, licença + horários + zonas deram 27 colisões (corridas compartilhadas); as 25 colunas, zero | Diferente da "Coluna de Índice" do Power Query, que depende da ordem e muda a cada atualização | 3 |
| **`generate_surrogate_key` (dbt-utils)** | Macro do pacote `dbt-utils` que monta o hash tratando `NULL` (em SQL, `'a' \|\| NULL` dá `NULL` e zeraria a chave) | — | 3 |
| **Unidade de reprocessamento** | O pedaço que se substitui inteiro quando a fonte muda. Aqui é o `source_month`, porque a TLC republica arquivos mensais. O `merge` por chave falha porque uma tarifa corrigida gera chave nova (a antiga fica) e corridas removidas nunca saem | Uma partição da atualização incremental do Power BI | 3 |
| **Hook (`pre_hook` / `post_hook`)** | SQL que o dbt roda antes ou depois de um model. Na Silver, o `pre_hook` apaga o mês antes do `append` | Uma etapa "antes de carregar" no pipeline | 1 |
| **Variável (`var()` / `--vars`)** | Valor passado ao dbt na hora de rodar (`--vars '{"source_month": "2025-01"}'`) e lido no model com `{{ var('source_month') }}`. O Jinja insere o texto ao pé da letra: em SQL, precisa de aspas em volta | Um parâmetro do Power Query | 1 |
| **`s3_data_naming`** | Configuração do dbt-athena que define o caminho no S3 de cada tabela. `schema_table_unique` dá uma pasta nova por versão, exigida pela materialização `table` em Iceberg (cria a tabela nova e troca o nome) | — | 1 |
| **uv** | Gerenciador de ambientes e pacotes Python. Cria o ambiente isolado do dbt e fixa as versões (`pyproject.toml` + `uv.lock`) | O instalador que garante a mesma versão do conector em todas as máquinas | 1 |
| **Idempotência** | Rodar o mesmo processamento duas vezes dá o mesmo resultado, sem duplicar. Três regras: chave pelo dado (não pelo relógio); substituir em vez de acumular; conferir antes de escrever. Na Bronze imutável, vem da regra 3: só se grava quando a fonte mudou | Apertar o botão do elevador duas vezes não chama dois elevadores; em SQL, `DELETE` + `INSERT` do mês × só `INSERT` | 1 |
| **`--full-refresh`** | Reconstrói um model incremental do zero | Atualização completa de uma tabela com atualização incremental | 1 |
| **Seed** | CSV pequeno e versionado dentro do projeto, transformado em tabela pelo dbt (`seed_operadoras.csv`) | "Inserir dados" no Power BI, só que no Git | 1 |
| **Teste genérico** | Teste declarado em YAML: `unique`, `not_null`, `accepted_values`, `relationships`. Por baixo, é um `SELECT` que procura problemas | Relacionamento válido e coluna sem vazios no modelo semântico | 1 |
| **Teste singular** | Arquivo `.sql` que devolve as linhas problemáticas; zero linhas = passou | Uma consulta de auditoria que deveria voltar vazia | 1 |
| **Severidade do teste (`warn` × `error`, `warn_if` / `error_if`)** | `warn` avisa e segue; `error` falha e faz o `dbt build` pular os dependentes. `warn_if`/`error_if` graduam pela quantidade (oscilação pequena avisa, explosão barra), evitando a fadiga de alerta | Alerta amarelo × vermelho num painel de monitoramento | 3 |
| **Teste com `where` (custo)** | Restringe o teste a um recorte (ex.: o `source_month` processado). No Athena, que cobra por leitura, um `unique` sem filtro numa Silver de 32 meses relê ~15 GB a cada build | — | 3 |
| **`store_failures`** | Guarda as linhas reprovadas num teste numa tabela, para investigar (suporte no dbt-athena não verificado) | — | 3 |
| **`source freshness`** | Confere quão recente é o dado de uma fonte, com limite de aviso e de erro. Pega a fonte que **parou de chegar** sem erro nenhum. Aqui é medido no manifesto (`max(registrado_em)` das linhas aceitas), porque a Bronze exige o `ingest_ts` na consulta | Controle de revisão: o carro não quebrou, mas está atrasado | 3 |
| **Gate de qualidade** | Testes com `error` entre a Silver e a Gold: se falham, a Gold não é atualizada (**proteção**) e a task do Airflow fica vermelha (**alarme**). O painel fica no último mês bom em vez de mostrar um ruim | Atualização que para se a validação falhar | 3 |
| **`dbt build`** | Roda seeds, models e testes na ordem do grafo; se o teste de um model falha, os dependentes são pulados | Uma atualização que para se a validação falhar | 1 |
| **Grão** | O que exatamente uma linha de uma tabela representa (ex.: hora × zona × operadora). Primeira decisão de qualquer tabela fato; vira o `GROUP BY` | A granularidade da tabela fato no modelo estrela do Power BI | 1 |
| **Método de Kimball (4 passos)** | 1) processo de negócio; 2) **grão**; 3) dimensões; 4) fatos (medidas). O grão vem antes das colunas: o que não respeita o grão não entra | O roteiro para montar um modelo estrela do zero | 3 |
| **Fato de transação × fato agregado** | Transação: uma linha por evento (cada corrida). Agregado: uma linha por combinação do grão (hora × zona × operadora). Aqui a Gold só tem fatos agregados: 651 milhões de corridas não cabem num modelo do Power BI. O que não está no grão não se recupera sem voltar à Silver | Importar cada venda × importar o resumo diário por loja | 3 |
| **Dimensão conformada** | Uma única definição de uma dimensão (ex.: `dim_zona`) compartilhada por vários fatos, para os números de fatos diferentes baterem no mesmo visual | A mesma tabela de calendário ligada a duas fatos | 3 |
| **Dimensão com papéis (role-playing)** | A mesma dimensão usada mais de uma vez no mesmo fato (zona de origem e zona de destino na `fct_od_diario`) | Relacionamento inativo + `USERELATIONSHIP` | 3 |
| **One big table (tabela larga)** | Uma tabela plana com tudo junto, sem estrela. Serve a exploração pontual e a ML; a estrela serve ao consumo recorrente e consistente | Uma consulta "achatada" exportada para Excel | 3 |
| **Métrica aditiva** | Pode ser somada em qualquer nível (somas, contagens). Médias e percentis não são aditivos: guarde soma e contagem e divida no consumo | `DIVIDE(SUM(...), SUM(...))` em vez de `AVERAGE` sobre valores já agregados | 1 |
| **Razão das somas × média das razões** | Taxa de um conjunto = soma do numerador / soma do denominador. A média das taxas de cada linha dá o mesmo peso a linhas pequenas e grandes. Ex.: take rate de US$ 10 (10%) e US$ 100 (30%): média 20%, real 28,2%. No DAX: `DIVIDE(SUM, SUM)`, não `AVERAGEX(DIVIDE)` | Consumo médio da frota = km totais / litros totais, não a média do km/l de cada carro | 4 |
| **Percentil não aditivo** | O P90 de um conjunto não é a média (nem a média ponderada) dos P90 das partes: depende da forma da distribuição inteira. Jan/2025: P90 da cidade 8,05 min; média simples dos P90 das zonas 8,55; ponderada 7,90 | `PERCENTILEX` só funciona com as linhas individuais no modelo | 3 |
| **Histograma de faixas (percentil aproximado)** | A Gold guarda quantas corridas caíram em cada faixa de espera (contagens são aditivas). O percentil sai no fim: somar as faixas do recorte, acumular até passar do alvo (ex.: 90%) e interpolar dentro da faixa. A precisão depende da largura da faixa onde o percentil cai: jan/2025, faixas da spec (6–10 min) deram P90 8,81; faixas de 1 min deram 8,06 (verdadeiro 8,05). Faixa aberta ("30+") não interpola: a resposta é "≥ 30 min" | Compartimentos do Power BI + frequência acumulada, só que decididos antes, na Gold | 3 |
| **Reconciliação** | Conferir que totais batem entre camadas (ex.: soma de corridas na Gold = corridas na Silver) | Conferir o total do relatório contra o sistema de origem | 1 |
| **Macro** | Função em Jinja reutilizável (ex.: `generate_schema_name`, que decide o nome do banco) | Uma função personalizada do Power Query | 1 |
| **Jinja (`{{ }}`, `{% %}`, `{# #}`)** | Linguagem de modelo de texto: o `.sql` do model é um molde que o dbt preenche antes de mandar ao banco. `{{ }}` escreve um valor (literal: as aspas do SQL vão por fora); `{% %}` comanda (`if`, `for`, `set`) e some do SQL final, deixando só o efeito; `{# #}` é comentário do molde | Mala direta do Word: a carta com campos e parágrafos condicionais vira a carta pronta. `dbt compile` mostra a carta pronta | 3 |
| **Pacote do dbt (`dbt deps`)** | Conjunto de macros prontas instalado no projeto (ex.: `dbt-utils`, com `generate_surrogate_key`) | Um conector ou função personalizada importada | 3 |
| **"SQL primeiro, Jinja quando doer"** | Regra prática: macro só para lógica que se repete ou depende do ambiente; o resto fica em SQL legível. Model cheio de `{% %}` vira um programa difícil de revisar | — | 3 |
| **`meta` (YAML do dbt)** | Metadado livre por model ou coluna. Aqui guarda o grão e a fórmula única de cada métrica (spec 2.5), lida pelo DAX (Fase 4) e pelo agente (Fase 6). O dbt não valida o conteúdo | A descrição nas propriedades de uma medida, só que uma vez, no repositório, para todos os consumidores | 3 |
| **`dbt docs`** | `generate` lê o projeto e o catálogo; `serve` abre um site com a documentação e o grafo de linhagem dos models. Documentação como código: gerada do que está no repositório | A exibição de linhagem do workspace, no nível dos models | 3 |
| **Camadas do dbt (staging, intermediate, marts)** | `stg_`: espelha uma fonte, limpa (renomear, tipar), sem joins nem regra de negócio. `int_`: junta e deriva o que vários marts reusam (ex.: `is_valid`). `fct_`/`dim_`: o produto pronto, com grão claro. Nome `stg_<fonte>__<entidade>` | Consultas de preparo com "Habilitar carga" desligado → consultas que mesclam → tabelas que carregam no modelo. Quebra: no dbt cada camada é um objeto no banco, testado e reaproveitado | 3 |
| **Marcar × usar a marca** | A regra de qualidade (`is_valid`, `invalid_reason`) é **calculada** uma vez na Silver (`int_`); a decisão de **usar** (excluir inválidas da contagem) acontece na Gold (`fct_`) | Coluna calculada `É Válida` na consulta × filtro dentro da medida | 3 |
| **Validade em dois níveis** | **Corrida** (`is_valid`: aconteceu como registrado?) × **métrica** (`is_valid_wait_metric`, `is_valid_economic_metrics`: esta medida serve?). Uma corrida com espera negativa conta na demanda, mas fica fora do P90 | Carro que rodou (conta no km), mas com o tacógrafo com defeito (fica fora da média de velocidade) | 3 |
| **Duplicata exata** | Duas linhas com todas as colunas iguais. A cópia ≥ 2 fica marcada (`invalid_reason = 'duplicata_exata'`), não apagada (ADR 0004). Produção: 17 em 651 milhões | Nota fiscal lançada duas vezes | 3 |
| **Gate de volume (`volume_mensal`)** | ✍️ do Ronald: média **diária** de corridas válidas do mês × média dos até 3 meses anteriores. Aviso ±20%, erro ±30%. Diária, e não o total, porque os meses têm tamanhos diferentes | — | 3 |
| **`on_schema_change`** | O que um model incremental faz quando o SELECT ganha ou perde coluna. `ignore` (padrão) descarta a coluna nova **em silêncio**; `fail` para com erro. Usamos `fail` | Power Query que ignora a coluna nova × que dá erro de coluna | 3 |
| **`-- depends_on:`** | Comentário com `ref`/`source` que avisa o dbt de uma dependência que ele não enxerga (a macro lê o manifesto com SQL próprio). Faz o manifesto aparecer na linhagem do `dbt docs` | — | 3 |
| **Seleção indireta de testes** | Ao selecionar ou excluir um model, o dbt leva junto os testes dele. `--exclude int_trips_enriched` tiraria também o gate. Solução: seleção explícita (`"int_trips_enriched,resource_type:test"`) | — | 3 |
| **Tabelas temporárias do dbt-athena** | Sufixos `__dbt_tmp`, `__bkp`, `__ha`, `__tmp_not_partitioned`: existem só durante uma construção. A manutenção as ignora (o `__` sozinho não serve: as stagings têm `__` no nome) | — | 3 |

---

## Power BI

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **ODBC** | Padrão antigo (anos 90) para programas conversarem com bancos; um driver instalado traduz para o banco específico. Precisa estar em toda máquina que conecta | Um adaptador de tomada | 1 |
| **Driver ODBC da Athena** | O "tradutor" ODBC → API do Athena, instalado no Windows. Exigido pelo conector do Athena no Power BI | O conector instalado à parte | 1 |
| **DSN (Data Source Name)** | Configuração de conexão ODBC salva com nome: driver, região, workgroup, autenticação. **User DSN** vale para um usuário; **System DSN**, para a máquina (exigido pelo gateway) | O perfil da AWS CLI, só que para o ODBC | 1 |
| **Conector Amazon Athena** | Conector do Power BI feito pela Amazon, que usa o DSN por baixo. Modos Import e DirectQuery | O conector do SQL Server, mas dependente de driver | 1 |
| **Browser SSO OIDC** | Autenticação do driver ODBC 2.x com o IAM Identity Center: abre o navegador, login + MFA, credencial temporária. Exige uma pessoa | "Entrar com conta organizacional", contra a AWS | 1 |
| **Import × DirectQuery (com Athena)** | Import consulta o Athena só na atualização; DirectQuery consulta a cada interação (custo por clique, latência de segundos, sujeito ao limite do workgroup) | O mesmo trade-off do Power BI, agravado pela cobrança por dado lido | 1 |
| **On-premises data gateway** | Serviço Windows que deixa o Power BI Service usar fontes que exigem software local (como um driver ODBC). Para o Athena, exige driver + System DSN + identidade de máquina | A ponte entre a nuvem da Microsoft e a sua máquina | 1 |
| **Identidade de máquina** | Credencial que se autentica sozinha (ex.: usuário IAM com chave somente leitura), para processos sem pessoa na frente da tela, como uma atualização agendada | Um service principal | 1 |
| **PBIP (Power BI Project)** | Formato do Power BI que salva relatório e modelo semântico em arquivos de texto, permitindo ao Git comparar as mudanças linha a linha | O `.pbix` desmontado em peças etiquetadas, em vez de uma caixa lacrada | 0 |
| **PBIR** | Formato do **relatório** dentro do PBIP: uma pasta por página e um `visual.json` por visual. Os dados importados ficam fora, no `cache.abf` (ignorado pelo Git) | A planta de cada página, visual por visual | 1 |
| **TMDL** | Linguagem de texto que descreve o **modelo semântico** no PBIP: tabelas, colunas, tipos, medidas | O DDL (`CREATE TABLE`) do modelo | 1 |
| **Agregação implícita** | Somar ou contar uma coluna direto no visual ("Soma de `qtd_corridas`"), sem medida DAX escrita. Serve para conferências; as métricas oficiais viram medidas explícitas | Arrastar a coluna para o campo Valores | 1 |
| **Data/hora automática** | Opção do Power BI que cria uma hierarquia oculta (Ano › Trimestre › Mês › Dia) para cada coluna de data. Neste projeto está desligada: sem ela, agrupar por dia exige uma coluna de data | A hierarquia de datas que aparece sozinha no eixo | 1 |
| **Direct Lake** | Modo do Fabric que lê as tabelas Delta do OneLake direto, sem copiar (Import) e sem consultar um motor SQL (DirectQuery). **Não existe para o Athena**: aqui são só Import e DirectQuery | — | 4 |
| **Filtro que não propaga (fato sem relacionamento)** | Um filtro de uma dimensão só chega à fato **ligada** a ela. Sem relacionamento, a medida **ignora o filtro em silêncio** e mostra o total: não fica vazia, fica errada. Ex.: segmentação de data (`dim_tempo_hora`) sobre o P90 da `fct_espera_histograma`, que não tem data | Filtrar a placa na planilha de multas e olhar o total da planilha de abastecimento, que não tem a coluna placa | 4 |
| **Fatos com grãos diferentes** | Fatos na mesma estrela com granularidades distintas (demanda por hora real × histograma por mês, hora do dia e tipo de dia). Cada fato só se liga a dimensões do seu grão ou mais grossas | — | 4 |
| **Consistência semântica** | A mesma métrica dá o mesmo número em todo lugar (SQL, DAX, agente). Uma definição só (o `meta` do dbt) e uma prova (reconciliação do mesmo recorte no Athena e no Power BI) | O manual de indicadores da frota: todas as filiais calculam a disponibilidade igual | 4 |
| **Camada semântica** | Ferramenta que guarda as definições das métricas e as serve a vários consumidores (ex.: Semantic Layer do dbt). Não usada no projeto: integração com o Power BI Desktop não verificada e custo alto para 6 métricas | O modelo semântico compartilhado do Fabric | 4 |
| **Percentil por histograma em DAX** | Medida que soma as contagens por faixa do recorte, acumula até o alvo (ex.: 90% do total), acha a primeira faixa que o atinge e **interpola** dentro dela. Total e acumulado **removem o filtro da faixa** e mantêm os demais; sem isso, num visual por faixa, cada barra calcula o "P90" só dentro dela | Pareto/curva ABC com um passo final de interpolação | 4 |
| **Interpolação linear** | Estimar um valor dentro de uma faixa supondo que os casos se espalham por igual nela: início + fração × largura. Ex.: alvo na 4ª de 5 corridas da faixa 8–9 min → 8 + 0,8 × 1 = 8,8 | Estimar o km no meio do trecho entre dois marcos da estrada | 4 |
| **Shapefile** | Formato de GIS para formas geográficas, em vários arquivos (`.shp`, `.dbf`, `.prj`...). É como a TLC publica as zonas de táxi | — | 4 |
| **TopoJSON** | JSON com formas geográficas que grava cada fronteira compartilhada **uma vez só** (topologia), por isso é menor que o GeoJSON. Cada forma carrega atributos, como o `LocationID` | O mapa de regiões da frota recortado em peças numeradas | 4 |
| **Reprojeção (WGS84)** | Converter as coordenadas de um sistema para outro. O shapefile da TLC vem, segundo fontes secundárias, no sistema NAD83 / New York Long Island em pés (EPSG 2263 ou 102718; ⚠️ conferir o `.prj` do arquivo baixado); mapas web usam latitude e longitude (WGS84) | Converter km para milhas antes de comparar | 4 |
| **Simplificação de geometria** | Reduzir os pontos de cada contorno para o arquivo ficar leve. Demais deforma as zonas pequenas | Reduzir a resolução de uma imagem | 4 |
| **Mapa de formas (Shape Map)** | Visual do Power BI que pinta formas de um TopoJSON próprio pela medida, ligando cada forma por uma **chave** (ex.: `LocationID` = `zona_id`). Zona sem forma não aparece; forma com medida vazia fica em branco; chave com tipo diferente não casa. Aceita TopoJSON ou GeoJSON, até 1.500 formas, com cor própria para "área em branco" (✅ documentação da Microsoft de 23/07/2026, sem menção a versão prévia) | Merge do Power Query: a forma de um lado, a tabela do outro | 4 |

---

## IA no desenvolvimento (ferramentas do agente)

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **MCP (Model Context Protocol)** | Padrão aberto que liga um agente de IA a um programa externo por meio de "ferramentas". O Power BI Modeling MCP conecta no Desktop aberto e roda DAX | Uma tomada padrão; o conector do Power Query, só que quem usa é o agente | 1 |
| **Skill** | Manual de instruções que o agente lê antes de uma tarefa específica (ex.: `powerbi-report-cli` para editar PBIR) | O procedimento operacional padrão de uma tarefa da oficina | 1 |
| **Plugin (Claude Code)** | Pacote que instala skills e MCPs de uma vez (ex.: `powerbi-authoring`, do repositório `microsoft/skills-for-fabric`) | Um kit de ferramentas com manual | 1 |
