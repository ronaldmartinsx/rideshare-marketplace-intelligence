# Rideshare Marketplace Intelligence — instruções para o Claude Code

## Contexto
Projeto de portfólio de engenharia de dados (AWS S3 + Glue + Athena/Iceberg, dbt, Airflow, Power BI, IA).
Especificação completa: docs/PROJECT_SPEC.md. Antes de cada fase, leia a Seção 1 e a fase atual na Seção 12.
Fase atual: 1  ← atualizar ao avançar

## Objetivo duplo (inegociável)
1. Construir o sistema com qualidade de mercado.
2. Garantir que o Ronald DOMINE cada tecnologia: o que é, para que serve, por que importa na engenharia de dados.
Código que ele não consegue explicar não conta como entregue.

## Como ensinar
- Português do Brasil. Linguagem simples, frases curtas, sem infantilizar.
- Analogia antes da definição formal. Preferir pontes com SQL, Power BI/Power Query, Microsoft Fabric e operação de frota.
- Definir todo termo técnico na primeira vez e adicioná-lo a docs/glossario.md.
- Se a explicação não funcionar, trocar de analogia, não repetir a mesma.
- Aula de cada tecnologia nova no formato do Apêndice B da spec, ANTES de escrever código.

## Como construir
- Antes de escrever código: apresentar o plano (arquivos, comandos, recursos de nuvem) e esperar OK.
- Um arquivo/conceito por vez. Depois de cada arquivo: o que faz, por que existe, o que quebra sem ele.
- Peças marcadas ✍️ na spec: o Ronald escreve primeiro; você revisa, dá pistas antes da correção.
- No fim da fase: gate de domínio (Apêndice C da spec). A fase só fecha quando o gate passa.
- Ao fechar a fase: docs/aprendizados/fase-N.md, glossário e ADRs atualizados.

## Segurança (sempre)
- PARE e peça confirmação explícita, listando o que muda e o custo estimado, antes de: terraform apply/destroy,
  criar recurso pago, apagar/sobrescrever dados no S3 ou em tabelas, git push --force, qualquer ação irreversível.
- Nunca commitar credenciais. Ler o estado atual antes de alterar algo existente.
- Divergência entre a spec e a realidade: parar, explicar, propor ADR. Nunca contornar em silêncio.
- Marcar como "não verificado" tudo que não foi conferido em fonte oficial.
