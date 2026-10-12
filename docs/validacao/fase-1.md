# Relatório de validação — Fase 1 (fatia vertical)

Evidências que respondem aos riscos R1, R2 e R3 e às hipóteses ⚠️ da Seção 3 da spec. Documento construído ao longo da fase.

- **Mês da fatia vertical:** 2025-01 (primeiro mês com `cbd_congestion_fee`).
- **Ferramenta de inspeção local:** DuckDB 1.5.6. Consultas reproduzíveis em [`scripts/fase-1/inspecao_parquet.sql`](../../scripts/fase-1/inspecao_parquet.sql).

---

## 1. O arquivo (R1: tamanho)

Medido em 12/10/2026.

| Item | 2024-01 | 2025-01 | 2026-08 |
|---|---|---|---|
| Tamanho (HTTP `Content-Length`) | 451 MB | 468 MB (491.076.642 bytes) | 479 MB |
| `Last-Modified` | 21/03/2024 | 23/04/2025 | 01/10/2026 |
| `ETag` | `"6fbcb726…-28"` | `"82b3922b…-94"` | `"766f4422…-30"` |

**Arquivo 2025-01 baixado:**

| Item | Valor |
|---|---|
| Linhas | **20.405.666** |
| Row groups | 20 (19 × 1.048.576 linhas + 1 × 482.722) |
| Compressão | ZSTD em todas as colunas |
| Gerado por | `parquet-cpp-arrow version 16.1.0` |
| SHA-256 | `fcdef276f4e9887f2beab30590165cdea74caef50a1313d71fa01ff6afacca3a` |
| Tempo de download | 16 s |

**Observações:**
- Cerca de 450–480 MB e ~20 milhões de linhas por mês: confirma a estimativa da spec ("dezenas de milhões de linhas, centenas de MB").
- Ago/2026 publicado em 01/10/2026: confirma o atraso de ~2 meses.
- O sufixo `-N` dos ETags indica upload em várias partes: **o ETag não é um hash do conteúdo** e não pode ser comparado com o SHA-256. Para detectar republicação (Fase 2), comparar ETag com ETag (ou `Last-Modified`), e usar o SHA-256 como identidade do arquivo baixado.
- As 4 colunas de data/hora ocupam ~211 MB comprimidos (~45% do arquivo). Uma consulta que não usa datas lê bem menos que o arquivo inteiro. A medição de bytes lidos no Athena fica para a próxima etapa.
- A coluna "taxa" da inspeção mede só o ganho do ZSTD sobre dados já codificados (dicionário/RLE); o ganho total em relação a um CSV não foi medido.

## 2. Schema real × esperado (Seção 3.1 da spec)

Comparação feita lendo só o rodapé dos arquivos 2024-01 e 2025-01, direto da internet.

- **As 25 colunas esperadas existem, com os nomes da spec.** Nenhuma coluna inesperada.
- **Schema drift confirmado:** `cbd_congestion_fee` (DOUBLE) existe em 2025-01 e não existe em 2024-01.
- **Nenhuma mudança de tipo** entre 2024-01 e 2025-01 nas 24 colunas comuns.
- Tipos reais: datas `TIMESTAMP`; `PULocationID`/`DOLocationID` `INTEGER`; `trip_time` `BIGINT` (segundos); valores `DOUBLE`; flags `VARCHAR` (`Y`/`N`); códigos `VARCHAR`.
- Nomes com maiúsculas (`PULocationID`, `DOLocationID`): a staging deve convertê-los para minúsculas (spec 6.1).

## 3. Hipóteses verificadas no dicionário oficial

Fonte: *Data Dictionary – High Volume FHV Trip Records*, versão de 18/03/2025.

| Hipótese da spec | Resultado |
|---|---|
| R6: HV0003 = Uber, HV0005 = Lyft | ✅ Confirmado (também listados HV0002 Juno e HV0004 Via, inativos) |
| `on_scene_datetime` só para veículos acessíveis | ⚠️ **Diverge dos dados** (ver seção 4) |
| Data de início da taxa do CBD | Dicionário: **"starting Jan. 5, 2025"** (a spec diz só "jan/2025") |
| Fuso horário dos timestamps (R5) | ❌ O dicionário não informa. Continua em aberto para a Fase 2 |

## 4. Achados nos dados (2025-01)

| Licença | Corridas | % | `on_scene_datetime` preenchido | Pedido de WAV | `request_datetime > pickup_datetime` |
|---|---|---|---|---|---|
| HV0003 (Uber) | 15.356.455 | 75,3% | **100,0%** | 0,24% | 120.967 (0,79%) |
| HV0005 (Lyft) | 5.049.211 | 24,7% | **0,3%** | 0,28% | 78.821 (1,56%) |

1. **`on_scene_datetime` depende da operadora.** O dicionário diz "Accessible Vehicles-only", mas a Uber preenche em 100% das corridas e a Lyft em 0,3% (próximo da taxa de WAV). A decisão da spec continua certa (não usar essa coluna para tempo de espera), e o motivo fica mais forte: usá-la mediria só a Uber.
2. **Espera negativa existe:** ~200 mil corridas (~1%) têm o pedido depois do embarque. Confirma a regra de qualidade `wait_time_s < 0` da Silver e dá a primeira calibração: ~0,8% na Uber e ~1,6% na Lyft.
3. **O arquivo é do mês de embarque:** `pickup_datetime` vai de 01/01 00:00 a 31/01 23:59:59. Já `request_datetime` começa em 31/12 e vai até 01/02, e `dropoff_datetime` vai até 01/02. Relevante para o ADR 0005 (partição por `source_month`).
4. **Predicate pushdown viável:** os row groups estão em ordem de embarque, com ~1 hora de sobreposição entre blocos vizinhos (ex.: RG 0 vai até 02/01 18:59; RG 1 começa em 02/01 18:00). Um filtro de data pula a maior parte dos blocos.
5. `cbd_congestion_fee` vai de `-0.0` a `3.0`, sem nulos.

## 5. Pendências desta validação

- [ ] R1 (custo): bytes lidos no Athena — `SELECT *` × uma coluna × com filtro de data (próxima etapa).
- [ ] R2: estratégia incremental do dbt-athena com Iceberg.
- [ ] R3: Power BI conectado ao Athena; atualização no Service.
- [x] Spec atualizada (seções 2.3, 2.4, 2.5 e 3.1) com estas evidências, sem ADR novo: nenhuma decisão mudou.
