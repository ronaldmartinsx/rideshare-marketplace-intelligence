# ADR 0003: Bronze imutável e versionada por `ingest_ts`, com manifesto só de acréscimo

- **Status:** Decidido (Fase 0) e implementado e validado na Fase 2 (cenários da etapa 8 em `docs/validacao/fase-2.md`)
- **Data:** 18/10/2026 (escrito); decisão original na Fase 0
- **Fase:** 2
- **Decisões da Fase 2 reunidas aqui:** D3 (escrita segura), D5 (`is_current` calculado), D7 (contrato e quarentena), W1 e W2 (clima sem ETag)

## Contexto

A Bronze guarda a fonte **exatamente como chegou** (spec 6.2). Três fatos tornam isso difícil:

1. **A TLC republica arquivos** já publicados (seção "Errata" da página oficial). Uma ingestão ingênua sobrescreveria o mês, e a versão anterior se perderia.
2. **Retries reexecutam a task inteira** (Airflow). Uma task que cai entre "gravar o arquivo" e "registrar o arquivo" deixaria cópias soltas a cada tentativa.
3. **A infraestrutura da Fase 0 não garantia a imutabilidade.** A política IAM do Airflow negava `DeleteObject` em `bronze/`, mas permitia `PutObject`, ou seja, **sobrescrever** era possível. O versionamento do bucket guardaria a versão anterior escondida, mas "imutável" dependia de o código não errar.

## Decisão

**1. Cada versão de um mês mora num caminho próprio**, com a versão no nome da pasta:

```text
bronze/<fonte>/year=AAAA/month=MM/ingest_ts=AAAAMMDDTHHMMSS/<arquivo>
```

O `ingest_ts` é o momento da gravação, em UTC. Ele é decidido **uma vez por run**, antes do upload, e passado adiante (XCom). O retry reusa o mesmo caminho.

**2. A gravação nunca sobrescreve**, garantido em duas camadas:

- **No código:** `put_object` com `If-None-Match: *` e `ChecksumSHA256`. Se o caminho já existe, o S3 responde `412`; o código confere o checksum guardado e trata "mesmo conteúdo" como sucesso (retry idempotente) e "outro conteúdo" como falha alta.
- **No armazenamento:** a política do bucket **nega** `PutObject` em `bronze/*` sem o cabeçalho, para **qualquer** identidade, inclusive administradores (`infra/terraform/s3.tf`).

**3. O manifesto (`controle.ingestion_manifest`, Iceberg) é a fonte da verdade e é só de acréscimo:**

- Uma linha por **evento** de ingestão, com `status`:
  - `aceito`: arquivo novo gravado e dentro do contrato;
  - `rejeitado`: arquivo novo gravado **em quarentena** (fora do contrato);
  - `mesmo_conteudo`: nenhum arquivo gravado; o ETag mudou, mas o SHA-256 é o da última versão. A linha copia o `ingest_ts` dessa versão e guarda o ETag novo, para o run seguinte não baixar tudo de novo.
- A linha é gravada **por último**: é o "commit". Arquivo sem linha no manifesto não conta (arquivo órfão inofensivo).
- **`is_current` não é gravado:** a view `controle.manifesto_vigente` calcula a versão vigente (a `aceito` de maior `ingest_ts` de cada fonte e mês). Uma versão nova é **uma** escrita, atômica, sem `UPDATE`.

**4. Contrato de schema na porta** (`airflow/include/contratos/*.yml`): coluna nova ou faltante gera alerta; tipo diferente rejeita (quarentena). A referência é uma **decisão versionada**, nunca "o mês anterior".

**5. Fonte sem ETag (clima, Open-Meteo):** a mudança é detectada pelo SHA-256 do **JSON canônico** (sem o campo volátil `generationtime_ms`, chaves ordenadas, uma linha). É o único desvio de "exatamente como chegou": o campo removido é o tempo de processamento do servidor, não dado.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Sobrescrever o mês na republicação | Perde a versão anterior; sem como auditar o que a TLC mudou |
| Confiar só no versionamento do S3 | A versão vigente ficaria implícita (a última gravada), sem contrato nem linhagem; um erro de código sobrescreveria em silêncio |
| `is_current` gravado como coluna | Exige duas escritas (inserir a nova e desmarcar a antiga): dois commits no Athena, com uma janela de duas ou nenhuma vigente |
| Registrar a conferência (`mesmo_conteudo`) como `aceito` | Contaria duas versões onde há um arquivo; a view escolheria entre linhas empatadas |
| Rejeitar o arquivo fora do contrato sem gravá-lo | A Bronze deixaria de ser "como chegou"; o arquivo problemático não ficaria disponível para investigação |
| Object Lock (WORM) no bucket | Garantia de nível regulatório, mais rígida que o necessário; o `If-None-Match` com política de bucket cobre o caso sem reconfigurar o bucket |
| Para o clima: guardar o JSON bruto e calcular o hash de outra coisa | O `ChecksumSHA256` do upload deixaria de bater com o hash registrado no manifesto |

## Consequências

**Ganhamos:**
- Nenhum arquivo da Bronze pode ser substituído, nem por engano humano (testado: `aws s3 cp` negado mesmo para o administrador).
- Rodar a ingestão duas vezes não duplica nada (7 runs no teste, 6 linhas no manifesto).
- Republicação vira versão nova e vigente; a anterior continua guardada.
- Arquivo fora do contrato fica em quarentena **sem** mudar a versão vigente: a Silver continua lendo a versão boa.
- Linhagem completa: qualquer linha da Silver leva, pelo `ingest_ts`, à linha do manifesto (URL, ETag, SHA-256, run do Airflow).

**Perdemos / cuidados:**
- Toda leitura da Bronze precisa saber qual versão quer. Isso é imposto pela projection (ADR 0015).
- A Bronze cresce a cada republicação (versões antigas nunca expiram, de propósito).
- Arquivos órfãos podem existir (task que caiu antes do commit) e não podem ser apagados pela role do Airflow. São inofensivos, porque não estão no manifesto.
- A imutabilidade **lógica** do manifesto (só `INSERT`) é garantida pelo código e pela revisão, não pela permissão: a manutenção do Iceberg exige `DeleteObject` em `controle/`. Um `DELETE` indevido fica registrado no histórico de snapshots e pode ser desfeito por time travel (retenção de 90 dias).
- Uma rejeição repetida (o mesmo arquivo fora do contrato) deixa a task vermelha todo dia até alguém agir: escolha consciente por "falhar alto". O destravamento é manual (parâmetro `reprocessar_meses`).
