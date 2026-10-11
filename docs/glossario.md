# Glossário

Termos técnicos do projeto, em ordem alfabética. Cada termo entra aqui na primeira vez que aparece numa aula.

| Termo | Definição | Analogia | Fase |
|---|---|---|---|
| **Access key** | Par de chaves (ID + segredo) que dá acesso programático à AWS. É permanente até ser desativada, por isso é o tipo de credencial que mais vaza | Uma cópia de chave que nunca expira | 0 |
| **ARN (Amazon Resource Name)** | Endereço completo e único de um recurso na AWS, ex.: `arn:aws:s3:::meu-bucket/gold/*` | O endereço completo de uma vaga no pátio: filial, setor, número | 0 |
| **AWS CLI** | Ferramenta de linha de comando para operar a AWS sem usar o console | Operar a frota por rádio em vez de ir ao pátio | 0 |
| **AWS Organizations** | Serviço que agrupa contas AWS sob uma conta principal (management account). Foi criado ao ativar o IAM Identity Center | A matriz que administra as filiais | 0 |
| **Branch** | Linha paralela de trabalho dentro do repositório. Permite mudar o código sem afetar a `main` até a mudança ser aprovada | Carro reserva onde se testa uma modificação sem tirar o titular de circulação | 0 |
| **CI (integração contínua)** | Testes e verificações que rodam automaticamente a cada mudança enviada ao repositório | Vistoria automática que todo veículo passa ao voltar para o pátio | 0 |
| **Commit** | Um ponto salvo no histórico: a foto da pasta com autor, data e mensagem explicando a mudança | Uma entrada na ficha de manutenção do veículo | 0 |
| **Conta AWS** | O contêiner de tudo na AWS: recursos, cobrança e acessos | A empresa locadora como um todo | 0 |
| **Conventional Commits** | Padrão de mensagem de commit com um prefixo que indica o tipo da mudança: `feat` (funcionalidade), `fix` (correção), `docs` (documentação), `chore` (manutenção) | Códigos padronizados de serviço na ficha da oficina | 0 |
| **Credencial temporária** | Credencial que expira sozinha (minutos ou horas). É gerada ao assumir uma role ou fazer login via Identity Center | Crachá de visitante que vale só para o dia | 0 |
| **Git** | Sistema que guarda o histórico de mudanças de uma pasta de arquivos | A ficha de manutenção completa de um veículo | 0 |
| **`.gitignore`** | Arquivo com a lista de caminhos que o Git deve ignorar (segredos, arquivos gerados, dados) | Lista do que não entra na ficha: objetos pessoais esquecidos no carro | 0 |
| **GitHub** | Serviço na nuvem que hospeda repositórios Git e acrescenta colaboração: PR, revisão e CI | A central da frota, que guarda as fichas de todas as filiais | 0 |
| **IAM (Identity and Access Management)** | Serviço da AWS que decide quem pode fazer o quê em quais recursos. É global (não pertence a uma região) | O sistema de crachás e chaves da locadora | 0 |
| **IAM Identity Center** | Login central da AWS para pessoas, com credenciais temporárias. Equivale ao SSO corporativo | A portaria que emite o crachá do dia para cada funcionário | 0 |
| **Menor privilégio** | Princípio de dar a cada identidade só as permissões necessárias para a sua tarefa, nada além | O manobrista recebe a chave do pátio, não a do cofre | 0 |
| **Merge** | Incorporar as mudanças de uma branch em outra (normalmente na `main`) | Aplicar no carro titular a modificação aprovada no reserva | 0 |
| **MFA (autenticação multifator)** | Login que exige, além da senha, um segundo fator (app autenticador ou chave física) | Abrir o cofre exige a chave e um código que muda a cada 30 segundos | 0 |
| **PBIP (Power BI Project)** | Formato do Power BI que salva relatório e modelo semântico em arquivos de texto, permitindo ao Git comparar as mudanças linha a linha | O `.pbix` desmontado em peças etiquetadas, em vez de uma caixa lacrada | 0 |
| **Perfil (AWS CLI)** | Nome salvo que aponta para uma credencial e uma região. Usado com `--profile <nome>` | Cada funcionário tem seu crachá; o perfil diz qual crachá usar | 0 |
| **Permission set** | Modelo de permissões do IAM Identity Center. Ao ser atribuído a uma conta, vira uma role (`AWSReservedSSO_...`) que o usuário assume no login | O modelo de colete: cada filial recebe um colete igual pendurado no pátio | 0 |
| **PKCE** | Proteção do login pelo navegador: o código devolvido ao `127.0.0.1` só pode ser trocado por credencial por quem guardou um segredo gerado no início (a CLI) | Senha de retirada no balcão: o ticket sozinho não basta | 0 |
| **Política IAM (policy)** | Documento JSON que permite (`Allow`) ou nega (`Deny`) ações em recursos. Tudo é negado por padrão; um `Deny` explícito vence um `Allow` | A lista do que o crachá abre | 0 |
| **Pull Request (PR)** | Pedido para incorporar uma branch na `main`, com espaço para revisão e comentários antes do merge | Pedido de aprovação da oficina antes de aplicar a modificação no titular | 0 |
| **Push** | Enviar os commits locais para o repositório remoto (GitHub). Até o push, o commit existe só na sua máquina | Enviar a ficha atualizada da filial para a central | 0 |
| **Região (AWS)** | Local físico onde os recursos ficam (ex.: `us-east-1`, Virgínia do Norte). A maioria dos recursos é regional | A filial da locadora: um carro de uma filial não aparece no pátio da outra | 0 |
| **Repositório** | A pasta do projeto junto com todo o seu histórico de mudanças (guardado na subpasta `.git`) | O arquivo da frota: veículos e fichas de manutenção | 0 |
| **Role (função IAM)** | Identidade sem senha nem chave própria. Quem tem autorização a assume e recebe credenciais temporárias | Colete de manobrista pendurado no pátio: veste, trabalha, devolve | 0 |
| **Root (usuário raiz)** | O login criado com a conta AWS. Pode tudo, inclusive fechar a conta. Deve ter MFA e não ser usado no dia a dia | O dono da locadora, com a chave-mestra do cofre | 0 |
| **Usuário IAM** | Identidade permanente dentro da conta, com senha e/ou access keys | Funcionário com crachá permanente | 0 |
