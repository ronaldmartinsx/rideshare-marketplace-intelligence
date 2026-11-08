# ADR 0011: PBIP (TMDL + PBIR) em `powerbi/` no lugar do `.pbix`

- **Status:** Decidido e aplicado na Fase 4 (passo 5)
- **Data:** 02/11/2026
- **Fase:** 4
- **Relacionado:** ADR 0001 (AWS), ADR 0006 (percentis via histograma), D1 e D6 do plano da Fase 4

## Contexto

O relatório do Power BI precisa morar no repositório, junto com o resto do sistema, por três motivos:

1. **Revisão:** as medidas DAX são ✍️ do Ronald e o Claude revisa. Revisar exige ver a diferença linha a linha.
2. **Histórico:** saber quando e por que um relacionamento ou uma medida mudou, como no dbt e no Terraform.
3. **Portfólio:** quem visita o repositório público consegue ler o modelo sem abrir o Power BI.

O `.pbix` é um arquivo binário (um pacote compactado). O Git guarda cada versão inteira e não mostra o que mudou dentro dele.

## Decisão

O relatório é salvo como **PBIP (Power BI Project)** em `powerbi/`:

```
powerbi/rideshare-marketplace/
├── Rideshare Marketplace Intelligence.pbip            ← ponto de entrada (abre no Desktop)
├── Rideshare Marketplace Intelligence.SemanticModel/  ← modelo semântico em TMDL
│   └── definition/  (model, relationships, tables/*.tmdl)
└── Rideshare Marketplace Intelligence.Report/         ← relatório em PBIR
    └── definition/  (report.json, pages/<página>/page.json, visuais)
```

- **Modelo em TMDL:** um arquivo de texto por tabela, mais `relationships.tmdl`. É o "DDL" do modelo.
- **Relatório em PBIR:** uma pasta por página e um arquivo por visual.
- Os dois formatos já vieram ativos no Desktop desta fase (versão de outubro de 2026): o projeto foi gravado em TMDL e PBIR sem ligar nenhum recurso de visualização.

### O que fica fora do Git (`.gitignore`)

| Arquivo | Por quê |
|---|---|
| `**/.pbi/cache.abf` | Dados importados: **523 MB** na carga de 02/11/2026. O dado mora no S3 (e o GitHub recusa arquivos acima de 100 MB) |
| `**/.pbi/localSettings.json` | Configuração local com uma assinatura criptografada da máquina. Não vale em outra |

O `.pbi/editorSettings.json` (preferências do editor do modelo) **entra** no Git.

O Desktop **não** criou um `.gitignore` ao salvar o projeto. As regras ficam no `.gitignore` da raiz.

### Fim de linha (`.gitattributes`)

O Desktop grava todos os arquivos de texto do PBIP com **CRLF** (conferido em 02/11/2026: `.tmdl`, `.json`, `.pbip`, `.pbir`, `.pbism`, `.platform`, sem BOM). A regra:

```gitattributes
powerbi/**/*.tmdl   text eol=crlf
...
```

- No Git, o texto fica com LF. Na cópia de trabalho, com CRLF, como o Desktop grava.
- Sem a regra, o resultado dependeria da configuração de cada máquina (no Windows, `core.autocrlf=true` vem da instalação do Git; no Mac, não). Uma máquina sem conversão veria o arquivo inteiro como alterado a cada vez que o Desktop salvasse.
- A regra é **restrita a `powerbi/`**: três seeds do dbt já estão com CRLF no Git, e uma regra global (`* text=auto`) os renormalizaria sem motivo.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| `.pbix` no Git | Binário: sem diff, sem revisão das medidas, e o histórico cresce uma cópia inteira por versão |
| `.pbix` fora do Git (só prints no README) | O relatório deixaria de fazer parte do sistema versionado. Era o plano B da Seção 10, só para o caso de o PBIP não funcionar |
| PBIP com o modelo em `model.bim` (JSON único) | Um arquivo gigante para o modelo todo; diff difícil de ler. O TMDL separa por tabela |

## Consequências

- **Um clone novo abre sem dados.** Precisa de uma atualização no Desktop: lê ~500 MB no Athena (cerca de US$ 0,0025) pelo DSN `rideshare-athena`.
- **O papel da AWS não fica no projeto.** O código M guarda só o nome do DSN (`AmazonAthena.Databases("rideshare-athena", null, [])`). Trocar o papel no DSN não muda nenhum arquivo.
- **Mudanças feitas pelo MCP do Power BI só chegam aos arquivos com Ctrl+S no Desktop.** O MCP altera o modelo aberto na memória. O `model.tmdl` registra o uso na anotação `PBI_ProTooling`.
- **Nomes com espaço** (`Rideshare Marketplace Intelligence.*`) exigem aspas em comandos de terminal.
- **Abrir só no Windows:** o Power BI Desktop não existe para Mac. No Mac, o PBIP é lido como texto (revisão de diff).
