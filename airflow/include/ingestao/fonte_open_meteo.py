"""Pedido do clima à API histórica do Open-Meteo (Fase 2, etapa 9; decisões W1 a W4).

A API não tem ETag (W1): para saber se um mês mudou, baixamos o mês (~40 KB) e comparamos o
SHA-256 do conteúdo com o da última versão. Para isso funcionar, o conteúdo precisa ser
"canônico" (W2): sem o campo que muda a cada pedido e sempre escrito do mesmo jeito.

Dados: Open-Meteo, licença CC BY 4.0 (atribuição obrigatória; ver README).
"""

from __future__ import annotations

import calendar
import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests

from include.ingestao.fonte_http import TIMEOUT, ErroTransitorio

URL_API = "https://archive-api.open-meteo.com/v1/archive"
LATITUDE, LONGITUDE = 40.78, -73.97  # Central Park (spec 3.3)
VARIAVEIS = ["temperature_2m", "precipitation", "rain", "snowfall", "wind_speed_10m"]

# Muda a cada pedido (tempo de processamento do servidor) e não é dado: sai antes do hash (W2)
CAMPOS_VOLATEIS = ("generationtime_ms",)


def janela_do_mes(mes: str) -> tuple[str, str]:
    """Do dia 1 do mês até o dia 1 do mês seguinte, inclusive (W3).

    Em UTC, as últimas 4 ou 5 horas de cada mês em Nova York caem no dia 1 do mês seguinte.
    """
    ano, numero = map(int, mes.split("-"))
    ano_seg, numero_seg = (ano + 1, 1) if numero == 12 else (ano, numero + 1)
    return f"{ano:04d}-{numero:02d}-01", f"{ano_seg:04d}-{numero_seg:02d}-01"


def url_do_mes(mes: str, base_url: str = URL_API) -> str:
    """URL completa do pedido (vai para o manifesto como source_url: linhagem)."""
    inicio, fim = janela_do_mes(mes)
    return (f"{base_url}?latitude={LATITUDE}&longitude={LONGITUDE}&start_date={inicio}&end_date={fim}"
            f"&hourly={','.join(VARIAVEIS)}&timezone=GMT")


def canonico(dados: dict) -> bytes:
    """O JSON sem os campos voláteis, com as chaves em ordem fixa e numa linha só.

    Mesma informação -> mesmos bytes -> mesmo SHA-256. Uma linha só porque o leitor de JSON do
    Athena espera um objeto por linha.
    """
    limpo = {chave: valor for chave, valor in dados.items() if chave not in CAMPOS_VOLATEIS}
    return json.dumps(limpo, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class ClimaBaixado:
    caminho: Path  # arquivo temporário local; quem chamou deve apagá-lo
    sha256: str
    tamanho: int
    dados: dict  # o JSON já lido, para o contrato


def baixar_clima(mes: str, base_url: str = URL_API, pasta: str | None = None) -> ClimaBaixado:
    """Pede o mês à API e grava o JSON canônico num arquivo temporário."""
    url = url_do_mes(mes, base_url)
    try:
        resposta = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as erro:
        raise ErroTransitorio(f"GET {url} falhou: {erro}") from erro
    if resposta.status_code >= 500 or resposta.status_code == 429:
        raise ErroTransitorio(f"GET {url} respondeu {resposta.status_code}")
    if resposta.status_code != 200:
        # A API explica o erro no corpo ({"error": true, "reason": ...}): pedido errado, falha alta
        raise RuntimeError(f"Open-Meteo recusou o pedido ({resposta.status_code}): {resposta.text[:300]}")

    dados = resposta.json()
    conteudo = canonico(dados)
    caminho = Path(tempfile.mkstemp(suffix=".json", dir=pasta)[1])
    caminho.write_bytes(conteudo)
    return ClimaBaixado(caminho, hashlib.sha256(conteudo).hexdigest(), len(conteudo), dados)
