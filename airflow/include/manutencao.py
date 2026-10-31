"""Manutenção das tabelas Iceberg: quais tabelas e quais comandos (Fase 3, etapa 8, decisão F12).

- tabelas_iceberg: descobre no Glue as tabelas Iceberg dos bancos pedidos (tabela nova entra sozinha).
- comandos: o que rodar em cada tabela.

Por que existe: o delete + append do dbt e cada INSERT no manifesto deixam arquivos antigos no S3,
guardados para o time travel. Sem VACUUM, ficam para sempre (medido em dev, 25/10/2026: a int tinha
11,87 GB no S3 para 8,74 GB vivos).
"""

from __future__ import annotations

import re

# Bancos varridos por padrão. A Bronze não é Iceberg (Parquet + projection) e nunca apaga nada.
BANCOS = ["controle", "silver", "gold", "dev_silver", "dev_gold"]

# Bancos com tabelas de controle: um arquivo minúsculo por INSERT, então vale compactar (OPTIMIZE).
# Nas tabelas do dbt, não: cada mês já é gravado de uma vez em arquivos grandes (~180 MB), e o
# OPTIMIZE da int leria ~9 GB, acima do freio de 3 GiB por consulta do workgroup.
BANCOS_COMPACTAR = {"controle"}

# Tabelas temporárias do dbt-athena 1.11.1 (sufixos conferidos no código do adapter). Existem só
# durante uma construção. Atenção: "__" sozinho não serve, porque as stagings usam "__" no nome
# (stg_tlc__hvfhv_trips).
_TEMPORARIA_DO_DBT = re.compile(r"__(dbt_tmp|bkp|ha|tmp_not_partitioned)")


def tabelas_iceberg(glue, bancos: list[str]) -> list[dict]:
    """[{"tabela": "banco.nome", "compactar": bool}] para cada tabela Iceberg dos bancos.

    Banco que ainda não existe (ex.: silver de prod antes da etapa 10) é ignorado, assim como as
    temporárias do dbt.
    """
    encontradas = []
    for banco in bancos:
        try:
            paginas = glue.get_paginator("get_tables").paginate(DatabaseName=banco)
            tabelas = [tabela for pagina in paginas for tabela in pagina["TableList"]]
        except glue.exceptions.EntityNotFoundException:
            continue
        for tabela in tabelas:
            iceberg = tabela.get("Parameters", {}).get("table_type", "").upper() == "ICEBERG"
            if iceberg and not _TEMPORARIA_DO_DBT.search(tabela["Name"]):
                encontradas.append(
                    {"tabela": f"{banco}.{tabela['Name']}", "compactar": banco in BANCOS_COMPACTAR}
                )
    return sorted(encontradas, key=lambda item: item["tabela"])


def comandos(tabela: str, compactar: bool) -> list[str]:
    """Os comandos de uma tabela, na ordem: compactar primeiro, para o VACUUM já limpar os
    arquivos pequenos que o OPTIMIZE substituiu (quando tiverem passado da retenção)."""
    lista = [f"OPTIMIZE {tabela} REWRITE DATA USING BIN_PACK"] if compactar else []
    return lista + [f"VACUUM {tabela}"]
