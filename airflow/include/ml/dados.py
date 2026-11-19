"""Leitura das tabelas de ML do Athena para pandas (Fase 5, passo 5).

Módulo de ENTRADA E SAÍDA: aqui ficam as consultas e a conversão de tipos. A regra pura das rodadas
está em janelas.py, e as escolhas de modelagem em config.py. Mesma separação da Fase 2 e da Fase 3.

Três modos de leitura do awswrangler, conferidos na documentação oficial em 15/11/2026:

| modo     | como funciona                         | efeito colateral                        |
|----------|---------------------------------------|-----------------------------------------|
| csv      | lê o CSV que o Athena já grava        | nenhum: só o bucket de resultados       |
| ctas     | embrulha em CREATE TABLE AS, lê Parquet | CRIA TABELA TEMPORÁRIA no Glue         |
| unload   | embrulha em UNLOAD, lê Parquet        | grava Parquet no S3, SEM tabela no Glue |

O padrão da biblioteca é `ctas`. Aqui o padrão é `unload`, escolhido por medição (ver PADRAO).
O `ctas` criaria tabela temporária no banco da consulta — que em produção é o `gold` —, e o
`unload` entrega o mesmo Parquet sem tocar o catálogo. Medição em scripts/fase-5/medir_leitura.py.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from include.ml import config

CSV = "csv"
CTAS = "ctas"
UNLOAD = "unload"
MODOS = (CSV, CTAS, UNLOAD)

# Decidido por MEDIÇÃO em 15/11/2026 (decisão B do plano), sobre as 6.312.366 linhas de produção:
#   csv     159,5 s   421,4 MB
#   unload   27,6 s   421,4 MB   <- 5,8x mais rápido, mesma memória, dado idêntico
# O ctas não foi medido de propósito: ele criaria tabela temporária no banco da consulta, que em
# produção é o gold. Como o unload entrega Parquet sem tocar o catálogo, o ctas ficou irrelevante.
PADRAO = UNLOAD

# Ordem determinística das linhas. NÃO é capricho: com feature_fraction e bagging_fraction menores
# que 1, o LightGBM sorteia linhas e colunas a partir da semente, e o sorteio depende da POSIÇÃO das
# linhas. O Athena não garante ordem de retorno, então duas leituras da mesma tabela poderiam
# devolver a mesma tabela em ordem diferente, gerar amostras diferentes e produzir WAPEs diferentes.
# O "pronto quando" da fase (spec, Seção 12) exige backtest reprodutível, e isto é parte do preço.
ORDEM = ["mes_corte", "zona_id", "hora_alvo"]

# Destino do UNLOAD. Duas exigências descobertas na medição de 15/11/2026:
#   1. a pasta tem de estar VAZIA, senão o Athena falha com HIVE_PATH_ALREADY_EXISTS. O local de
#      resultados do workgroup não serve, porque ele já tem arquivos;
#   2. por isso cada leitura ganha um prefixo único, apagado depois (keep_files=False).
PREFIXO_UNLOAD = "s3://rmartins-rideshare-athena-results/unload"


def sessao_airflow():
    """Sessão boto3 da Connection aws_default.

    O import do hook é feito AQUI DENTRO, e não no topo do módulo, de propósito: assim este arquivo
    pode ser importado numa máquina sem Airflow instalado — o que é o que permite rodar a medição
    de leitura direto do Mac, com um boto3.Session de perfil.

    Chamar dentro da task, não no topo da DAG: cada task ganha a sua credencial de 1 hora (D8).
    """
    from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook

    return AwsBaseHook(aws_conn_id="aws_default").get_session()


def selecionar(colunas: Sequence[str]) -> str:
    """A lista do SELECT, com cast nos timestamps.

    O cast existe para o UNLOAD funcionar: o Iceberg cria timestamp(6) e o UNLOAD do Athena só
    exporta Parquet até milissegundo. Fica aplicado nos três modos para que todos devolvam
    exatamente o mesmo dado — modo de transporte não pode mudar o conteúdo.
    """
    return ", ".join(
        f"cast({c} as timestamp(3)) as {c}" if c in config.COLUNAS_TIMESTAMP else c
        for c in colunas
    )


def _ler(
    sql: str,
    ambiente: str,
    sessao,
    modo: str = PADRAO,
    categorias: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Roda a consulta no Athena e devolve um DataFrame, no modo pedido."""
    import uuid

    import awswrangler as wr

    if modo not in MODOS:
        raise ValueError(f"modo de leitura desconhecido: {modo!r}; use um de {MODOS}")

    # Só o UNLOAD precisa de destino próprio, e ele tem de estar vazio (ver PREFIXO_UNLOAD).
    destino = f"{PREFIXO_UNLOAD}/{uuid.uuid4()}/" if modo == UNLOAD else None

    return wr.athena.read_sql_query(
        sql=sql,
        database=config.BANCO[ambiente],
        workgroup=config.WORKGROUP,  # o padrão da biblioteca é "primary", que não existe aqui
        boto3_session=sessao,
        s3_output=destino,
        # Texto repetitivo já volta como categoria, em vez de virar 6,3 M de objetos Python para
        # depois serem convertidos (Aula 4: 673 MB contra 12 MB).
        categories=list(categorias) if categorias else None,
        ctas_approach=(modo == CTAS),
        unload_approach=(modo == UNLOAD),
        # Mantido TRUE (o padrão) por uma razão de PERMISSÃO, não de preferência: apagar exigiria
        # s3:DeleteObject no bucket de resultados, e a política do Airflow não tem essa ação DE
        # PROPÓSITO desde a Fase 0 — "sem DeleteObject: quem limpa é a regra de ciclo de vida"
        # (iam_airflow.tf). Em vez de alargar a política para o código caber, o código se adapta à
        # decisão que já existia. Custo: ~0,4 GB parado por até 7 dias, cerca de US$ 0,002.
        keep_files=True,
    )


def ler_features(
    ambiente: str,
    sessao,
    modo: str = PADRAO,
    colunas: Sequence[str] | None = None,
) -> pd.DataFrame:
    """A tabela de features inteira, já com os tipos aplicados e em ordem determinística.

    Lida UMA vez para todas as rodadas, e o backtest recorta em memória por mes_corte: 1 scan no
    Athena em vez de 7. Estimativa de memória com os dtypes de config.py: ~457 MB para 6,3 M linhas.
    """
    escolhidas = list(colunas) if colunas else config.COLUNAS_LEITURA
    sql = f"select {selecionar(escolhidas)} from {config.TABELA_FEATURES}"

    categorias = [c for c in config.COLUNAS_CATEGORIA if c in escolhidas]
    df = _ler(sql, ambiente, sessao, modo=modo, categorias=categorias)
    return ordenar(aplicar_tipos(df))


def ler_baseline(
    ambiente: str,
    sessao,
    cortes: Sequence[str] | None = None,
    modo: str = PADRAO,
) -> pd.DataFrame:
    """O palpite do baseline por linha, para a comparação do backtest.

    Vem da ml_baseline_demanda, construída em SQL pelo Ronald (passo 3): o Python NÃO recalcula o
    baseline, ele apenas lê o que o SQL já decidiu. Uma definição, um lugar — se o Python
    recalculasse, haveria duas definições de baseline e um dia elas divergiriam em silêncio.

    cortes: se dado, filtra na origem. O backtest só precisa do baseline dos cortes AVALIADOS
    (~190 mil linhas por corte), não dos 6,3 milhões — então filtrar aqui evita carregar 33 vezes
    mais dado do que se usa.
    """
    colunas = ["hora_alvo", "zona_id", "mes_corte", "mes_alvo", "tem_alvo",
               "qtd_corridas", "previsao_baseline"]
    onde = ""
    if cortes:
        lista = ", ".join(f"'{c}'" for c in cortes)
        onde = f" where mes_corte in ({lista})"
    sql = f"select {selecionar(colunas)} from {config.TABELA_BASELINE}{onde}"

    categorias = [c for c in config.COLUNAS_CATEGORIA if c in colunas]
    df = _ler(sql, ambiente, sessao, modo=modo, categorias=categorias)
    return ordenar(aplicar_tipos(df))


def aplicar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """Converte as colunas para os dtypes de config.py: numéricas e categorias.

    Tem de ser DEPOIS da leitura: o read_sql_query não aceita um mapa de dtype (conferido na
    documentação oficial e na própria biblioteca instalada; só existe dtype_backend). Como o padrão
    da biblioteca é numpy_nullable, as colunas chegam em tipos anuláveis do pandas (Int64, Float64,
    com pd.NA), que o LightGBM não lê bem. O astype para float32/int leva o pd.NA para NaN, que o
    LightGBM trata nativamente.

    As CATEGORIAS também são garantidas aqui, e não só pedidas na leitura. Medido em 15/11/2026: o
    parâmetro `categories` do awswrangler é RESPEITADO no modo csv e IGNORADO no modo unload, onde o
    texto volta como `string` — 322 MB nas quatro colunas em vez de ~12 MB, o que levava o unload de
    421 MB (csv) para 720 MB. Convertendo aqui, os dois modos terminam com os mesmos tipos e o mesmo
    tamanho: o modo de transporte não muda o conteúdo NEM a forma.

    A conversão é feita coluna por coluna de propósito: um astype do DataFrame inteiro criaria uma
    segunda cópia completa antes de liberar a primeira, e o pico de memória é o que mata contêiner.
    """
    for coluna, tipo in config.DTYPES.items():
        if coluna in df.columns:
            df[coluna] = df[coluna].astype(tipo)

    for coluna in config.COLUNAS_CATEGORIA:
        if coluna in df.columns and df[coluna].dtype.name != "category":
            df[coluna] = df[coluna].astype("category")

    return df


def ordenar(df: pd.DataFrame) -> pd.DataFrame:
    """Ordem fixa das linhas, para o treino ser reprodutível (ver ORDEM, no topo do módulo)."""
    chaves = [c for c in ORDEM if c in df.columns]
    if not chaves:
        return df
    return df.sort_values(chaves, kind="mergesort").reset_index(drop=True)


def recortar(df: pd.DataFrame, cortes: Sequence[str], somente_com_alvo: bool = True) -> pd.DataFrame:
    """As linhas de um conjunto de cortes. É o que transforma uma Rodada em dados de verdade.

    somente_com_alvo: no treino e na avaliação, linha sem gabarito não serve para nada. Na previsão
    de produção é justamente o contrário — ali o alvo não existe e é o que se quer descobrir.
    """
    filtro = df["mes_corte"].isin(list(cortes))
    if somente_com_alvo:
        filtro &= df["tem_alvo"]
    return df.loc[filtro]
