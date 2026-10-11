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

## Power BI

| Termo | O que é | Analogia / ponte | Fase |
|---|---|---|---|
| **PBIP (Power BI Project)** | Formato do Power BI que salva relatório e modelo semântico em arquivos de texto, permitindo ao Git comparar as mudanças linha a linha | O `.pbix` desmontado em peças etiquetadas, em vez de uma caixa lacrada | 0 |
