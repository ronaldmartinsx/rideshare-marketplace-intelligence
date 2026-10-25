"""Leitura do manifesto e leitura/escrita do registro de construção via Athena (Fase 3, etapa 8).

Mesma separação da Fase 2 (decisao.py × manifesto.py): a regra de pendência (dbt_construcao.py)
é pura; aqui ficam as consultas que buscam os dados para ela e a gravação do registro.

- ler_vigentes: as versões vigentes da TLC e do clima, por mês (manifesto_vigente).
- ler_construidos: a última construção de cada mês, num ambiente (dbt_meses_construidos_vigente).
- versoes_na_silver: as versões que a Silver de fato usou num mês (depois da construção).
- gravar_construcao: uma linha no registro. Só INSERT; retry não duplica.
- meses_registrados_desde: quais meses ganharam linha no registro a partir de um instante.
"""

from __future__ import annotations

from datetime import datetime, timezone

from include.dbt_construcao import Construcao
from include.ingestao.manifesto import _executar, _literal  # mesmo cliente Athena da Fase 2

BANCO_CONTROLE = "controle"  # dev e prod do dbt leem a mesma Bronze de produção
FONTE_TLC = "tlc_hvfhv"
FONTE_CLIMA = "open_meteo"

# Banco da Silver de cada ambiente do dbt (a macro generate_schema_name monta os mesmos nomes)
BANCO_SILVER = {"dev": "dev_silver", "prod": "silver"}


def ler_vigentes(athena) -> tuple[dict[str, str], dict[str, str]]:
    """({mês: ingest_ts da TLC}, {mês: ingest_ts do clima}) na manifesto_vigente."""
    linhas = _executar(
        athena,
        f"SELECT source, source_month, ingest_ts FROM {BANCO_CONTROLE}.manifesto_vigente "
        f"WHERE source IN ({_literal(FONTE_TLC)}, {_literal(FONTE_CLIMA)})",
    )
    tlc = {mes: ingest_ts for fonte, mes, ingest_ts in linhas if fonte == FONTE_TLC}
    clima = {mes: ingest_ts for fonte, mes, ingest_ts in linhas if fonte == FONTE_CLIMA}
    return tlc, clima


def ler_construidos(athena, ambiente: str) -> dict[str, Construcao]:
    """{mês: Construcao} da última construção que deu certo, SÓ deste ambiente."""
    linhas = _executar(
        athena,
        f"SELECT source_month, ingest_ts_tlc, ingest_ts_clima "
        f"FROM {BANCO_CONTROLE}.dbt_meses_construidos_vigente WHERE ambiente = {_literal(ambiente)}",
    )
    return {mes: Construcao(tlc, clima) for mes, tlc, clima in linhas}


def versoes_na_silver(athena, ambiente: str, mes: str) -> Construcao:
    """As versões que a construção usou de fato, lidas das stagings do mês.

    Não usa o manifesto: se a ingestão aceitou uma versão nova durante a construção, o registro
    precisa dizer a versão que o dbt LEU, não a que é vigente agora. Lê só a coluna ingest_ts de
    uma partição (source_month): poucos MB.
    """
    banco = BANCO_SILVER[ambiente]
    filtro = f"WHERE source_month = {_literal(mes)}"
    tlc, clima = _executar(
        athena,
        f"SELECT (SELECT max(ingest_ts) FROM {banco}.stg_tlc__hvfhv_trips {filtro}), "
        f"(SELECT max(ingest_ts) FROM {banco}.stg_open_meteo__weather_hourly {filtro})",
    )[0]
    if tlc is None or clima is None:
        raise RuntimeError(f"{banco} sem o mês {mes} numa das stagings: a construção não terminou")
    return Construcao(tlc, clima)


def gravar_construcao(
    athena, ambiente: str, mes: str, construcao: Construcao, motivo: str, dag_run_id: str
) -> bool:
    """Grava uma linha no registro. Devolve False se a mesma linha já existia (nada gravado).

    "Mesma" = mesmo ambiente, mês, versões e execução: é o retry depois de um INSERT que deu
    certo. Conferir e depois gravar é seguro: a dbt_mes roda um mês por vez (max_active_runs=1).
    """
    tabela = f"{BANCO_CONTROLE}.dbt_meses_construidos"
    chave = (
        f"ambiente = {_literal(ambiente)} AND source_month = {_literal(mes)} "
        f"AND ingest_ts_tlc = {_literal(construcao.ingest_ts_tlc)} "
        f"AND ingest_ts_clima = {_literal(construcao.ingest_ts_clima)} "
        f"AND dag_run_id = {_literal(dag_run_id)}"
    )
    if int(_executar(athena, f"SELECT count(*) FROM {tabela} WHERE {chave}")[0][0]) > 0:
        return False

    valores = ", ".join(
        _literal(valor)
        for valor in (
            ambiente, mes, construcao.ingest_ts_tlc, construcao.ingest_ts_clima, motivo,
            datetime.now(timezone.utc), dag_run_id,
        )
    )
    _executar(athena, f"INSERT INTO {tabela} VALUES ({valores})")
    return True


def meses_registrados_desde(athena, ambiente: str, desde: datetime) -> list[str]:
    """Meses deste ambiente gravados no registro a partir de `desde` (o início do run da dbt_build).

    O registro só ganha linha quando a dbt_mes termina verde: é a prova de que a Gold mudou.
    """
    linhas = _executar(
        athena,
        f"SELECT DISTINCT source_month FROM {BANCO_CONTROLE}.dbt_meses_construidos "
        f"WHERE ambiente = {_literal(ambiente)} AND construido_em >= {_literal(desde)} "
        f"ORDER BY source_month",
    )
    return [mes for (mes,) in linhas]
