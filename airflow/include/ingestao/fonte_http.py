"""Conversa com a fonte por HTTP: HEAD (o arquivo mudou?) e download (Fase 2, etapa 6).

Separação de papéis (Aula 1, cenário 11 da etapa 5):
- erro TRANSITÓRIO (rede caiu, 5xx, 429): esta camada LANÇA exceção, e o retry do Airflow,
  com espera crescente, tenta de novo. Se não passar, a task fica vermelha.
- resposta DEFINITIVA (200, 403, outros 4xx): esta camada DEVOLVE a resposta, e quem decide
  o que ela significa é decidir_acao (decisao.py).
"""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

from include.ingestao.decisao import RespostaHead

# URL pública dos arquivos da TLC (spec, seção 3.1). No ambiente de teste, a DAG troca a base
# pela "TLC de mentira" (etapa 8).
BASE_URL_TLC = "https://d37ci6vzurychx.cloudfront.net/trip-data"

# (conectar, ler) em segundos. Ler = tempo máximo SEM receber nenhum byte, não o download inteiro.
TIMEOUT = (10, 60)

# 1 MiB por pedaço: o arquivo de ~480 MB nunca fica inteiro na memória
TAMANHO_PEDACO = 1024 * 1024


class ErroTransitorio(Exception):
    """Falha que pode passar sozinha. Deixar subir: o retry do Airflow cuida."""


def url_do_mes(mes: str, base_url: str = BASE_URL_TLC) -> str:
    """'2025-01' -> .../fhvhv_tripdata_2025-01.parquet"""
    return f"{base_url}/fhvhv_tripdata_{mes}.parquet"


def _e_transitorio(status: int) -> bool:
    # 5xx: problema do servidor. 429: "muitos pedidos, espere". Os dois costumam passar.
    return status >= 500 or status == 429


def consultar_head(url: str) -> RespostaHead:
    """Pede só os cabeçalhos do arquivo (Aula 3). Menos de 1 KB, sem baixar o conteúdo."""
    try:
        resposta = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as erro:  # conexão recusada, DNS, tempo esgotado...
        raise ErroTransitorio(f"HEAD {url} falhou: {erro}") from erro

    if _e_transitorio(resposta.status_code):
        raise ErroTransitorio(f"HEAD {url} respondeu {resposta.status_code}")

    cabecalhos = resposta.headers  # o requests ignora maiúsculas: "ETag" = "etag"
    ultima_modificacao = cabecalhos.get("Last-Modified")
    tamanho = cabecalhos.get("Content-Length")
    return RespostaHead(
        status=resposta.status_code,
        etag=cabecalhos.get("ETag"),  # guardado com as aspas, como o servidor manda
        last_modified=parsedate_to_datetime(ultima_modificacao) if ultima_modificacao else None,
        content_length=int(tamanho) if tamanho else None,
    )


@dataclass(frozen=True)
class ArquivoBaixado:
    caminho: Path  # arquivo temporário local; quem chamou deve apagá-lo no fim
    sha256: str
    tamanho: int


def baixar(url: str, tamanho_esperado: int | None = None, pasta: str | None = None) -> ArquivoBaixado:
    """Baixa o arquivo em pedaços, calculando o SHA-256 enquanto grava no disco.

    Calcular durante o download evita ler os ~480 MB duas vezes. Se o tamanho final não bater
    com o Content-Length do HEAD, o download veio cortado: erro transitório (tentar de novo).
    """
    hash_sha256 = hashlib.sha256()
    tamanho = 0
    destino = Path(tempfile.mkstemp(suffix=".parquet", dir=pasta)[1])
    try:
        with requests.get(url, stream=True, timeout=TIMEOUT) as resposta:
            if _e_transitorio(resposta.status_code):
                raise ErroTransitorio(f"GET {url} respondeu {resposta.status_code}")
            resposta.raise_for_status()  # outro 4xx aqui é inesperado (o HEAD deu 200): falha alta
            with destino.open("wb") as arquivo:
                for pedaco in resposta.iter_content(chunk_size=TAMANHO_PEDACO):
                    arquivo.write(pedaco)
                    hash_sha256.update(pedaco)
                    tamanho += len(pedaco)
    except requests.RequestException as erro:
        destino.unlink(missing_ok=True)
        if isinstance(erro, requests.HTTPError):
            raise
        raise ErroTransitorio(f"GET {url} falhou: {erro}") from erro
    except BaseException:
        destino.unlink(missing_ok=True)
        raise

    if tamanho_esperado is not None and tamanho != tamanho_esperado:
        destino.unlink(missing_ok=True)
        raise ErroTransitorio(f"GET {url}: baixados {tamanho} bytes, esperados {tamanho_esperado}")

    return ArquivoBaixado(caminho=destino, sha256=hash_sha256.hexdigest(), tamanho=tamanho)
