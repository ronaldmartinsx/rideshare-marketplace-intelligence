"""Decisão da ingestão: o que fazer com cada mês (Fase 2, etapa 5). ✍️ Peça do Ronald.

Regras desenhadas pelo Ronald na tabela de cenários (18/10/2026); código escrito pelo Claude
a pedido dele; testes escritos pelo Ronald (tests/ingestao/test_decisao.py).

Duas funções puras: recebem dados prontos e devolvem uma decisão. Não acessam rede, S3 nem
Athena. Quem busca os dados (HEAD na TLC, leitura do manifesto) é a DAG, antes de chamá-las.

Onde cada uma entra no fluxo da tlc_ingest:

    HEAD na TLC + histórico do mês no manifesto
        -> decidir_acao(...)            -> "baixar" | "reprocessar" | "ignorar" | "aguardar" | "erro"
    se baixar/reprocessar: download + SHA-256
        -> classificar_download(...)    -> "nova_versao" | "mesmo_conteudo"
    contrato de schema (contrato.py) -> grava na Bronze e/ou registra no manifesto
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RespostaHead:
    """O que a TLC respondeu ao HEAD de um mês."""

    status: int  # código HTTP: 200 (existe), 403 (não existe ou proibido), outros
    etag: str | None = None  # com aspas, como o servidor manda: '"82b3...-94"'
    last_modified: datetime | None = None
    content_length: int | None = None


@dataclass(frozen=True)
class LinhaManifesto:
    """Uma linha de controle.ingestion_manifest (só as colunas que importam para decidir)."""

    ingest_ts: str  # 'YYYYMMDDTHHMMSS': a versão (pasta) do arquivo na Bronze; ordena como o tempo
    etag: str | None
    file_sha256: str | None
    # 'aceito' / 'rejeitado': um arquivo novo entrou na Bronze (passou ou falhou no contrato).
    # 'mesmo_conteudo': conferência; nenhum arquivo entrou. A linha copia o ingest_ts da versão
    # que já existia e guarda o ETag novo, para o run seguinte não baixar tudo de novo.
    status: str


# Status das linhas que correspondem a um arquivo gravado na Bronze
_STATUS_COM_ARQUIVO = ("aceito", "rejeitado")


def _ultima_versao(historico: list[LinhaManifesto]) -> LinhaManifesto | None:
    """A versão de arquivo mais recente do mês (aceita ou rejeitada), ou None se nunca houve.

    É "o que a Bronze tem de mais novo para este mês". Conferências (mesmo_conteudo) não contam:
    elas apontam para um arquivo que já existe, não trazem arquivo novo.
    """
    versoes = [linha for linha in historico if linha.status in _STATUS_COM_ARQUIVO]
    return max(versoes, key=lambda linha: linha.ingest_ts, default=None)


def decidir_acao(
    mes: str,
    resposta: RespostaHead,
    historico: list[LinhaManifesto],
    proximo_mes_esperado: str,
) -> str:
    """Decide o que fazer com um mês, ANTES de qualquer download.

    Args:
        mes: mês de referência, 'YYYY-MM'.
        resposta: o resultado do HEAD na URL do mês.
        historico: TODAS as linhas do manifesto para este mês e esta fonte, de qualquer status,
            em qualquer ordem. Lista vazia = o mês nunca passou pela ingestão.
        proximo_mes_esperado: o mês seguinte ao mais recente que tem versão aceita
            (ex.: o mais recente aceito é '2026-08' -> '2026-09'). Calculado pela DAG.

    Returns:
        "baixar"       mês inédito: baixar e gravar a primeira versão.
        "reprocessar"  mês que já tem versão, mas a fonte pode ter mudado: baixar e conferir.
        "ignorar"      nada a fazer.
        "aguardar"     o mês ainda não foi publicado: tentar de novo no próximo run (sem erro).
        "erro"         algo está errado e uma pessoa precisa olhar: a task deve falhar alto.
    """
    # 1) Nem 200 nem 403 (ex.: 503). Erro transitório é tratado ANTES, pela camada HTTP com o
    #    retry do Airflow (cenário 11). Se chegou até aqui, aquela camada falhou: falha alta.
    if resposta.status not in (200, 403):
        return "erro"

    # 2) 403: o arquivo não existe para nós. Regra do 403 (Aula 3, cenários 4 a 7):
    #    do mês esperado em diante, e nunca visto antes, é "ainda não publicado".
    #    "YYYY-MM" compara como texto na mesma ordem do tempo.
    if resposta.status == 403:
        if mes >= proximo_mes_esperado and not historico:
            return "aguardar"
        return "erro"  # mês antigo, ou que já existiu e sumiu: alguém precisa olhar

    # 3) 200 e o mês nunca passou pela ingestão (cenário 1)
    ultima = _ultima_versao(historico)
    if ultima is None:
        return "baixar"

    # 4) 200 e o mês já tem arquivo na Bronze. O ETag de hoje já foi visto ligado ao conteúdo
    #    da última versão? Vale a linha da própria versão ou uma conferência (cenários 2 e 10).
    etag_conhecido = any(
        linha.etag == resposta.etag and linha.file_sha256 == ultima.file_sha256
        for linha in historico
    )
    if not etag_conhecido:
        return "reprocessar"  # ETag novo: a fonte pode ter mudado (cenários 3 e 9)

    # 5) A fonte não mudou desde a última conferência. O que temos dela foi aceito?
    if ultima.status == "aceito":
        return "ignorar"  # cenários 2 e 10
    return "erro"  # o mesmo arquivo que o contrato rejeitou: só uma pessoa destrava (cenário 8)


def classificar_download(sha256_baixado: str, historico: list[LinhaManifesto]) -> str:
    """Depois do download, decide se o arquivo é uma versão nova ou o mesmo conteúdo de antes.

    Args:
        sha256_baixado: o SHA-256 do arquivo que acabou de ser baixado.
        historico: as mesmas linhas do manifesto que decidir_acao recebeu.

    Returns:
        "nova_versao"     conteúdo novo: gravar na Bronze com um ingest_ts novo.
        "mesmo_conteudo"  conteúdo idêntico ao da última versão: não gravar arquivo novo,
                          só a linha de conferência com o ETag novo.
    """
    # Compara com a ÚLTIMA versão, não com qualquer versão antiga: se a TLC voltar a servir um
    # arquivo de antes, ele precisa virar uma versão nova para voltar a ser o vigente.
    ultima = _ultima_versao(historico)
    if ultima is not None and sha256_baixado == ultima.file_sha256:
        return "mesmo_conteudo"  # cenários A (última aceita) e D (última rejeitada)
    return "nova_versao"  # cenários B e C
