"""Contrato de schema: confere um arquivo contra a ficha escrita em include/contratos/ (Fase 2, D7).

Fluxo: ler o rodapé do Parquet -> traduzir os tipos para o vocabulário do Athena ->
calcular o schema_hash -> comparar com o contrato -> aceito ou rejeitado, com os alertas.

A comparação (validar) é uma função pura: recebe dicionários e devolve o resultado, sem ler
arquivo nem rede. Por isso é testada sem precisar de S3 nem da TLC.
"""

from __future__ import annotations

import calendar
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

PASTA_CONTRATOS = Path(__file__).resolve().parent.parent / "contratos"

# Valores aceitos nas regras do YAML. Outro valor é erro de digitação no contrato, não drift.
_REGRAS_VALIDAS = {
    "coluna_nova": {"alertar", "rejeitar"},
    "coluna_faltante": {"alertar", "rejeitar"},
    "tipo_diferente": {"alertar", "rejeitar"},
    "tipo_nulo_compativel": {True, False},
}
_REGRAS_VALIDAS_CLIMA = {
    "variavel_nova": {"alertar", "rejeitar"},
    "variavel_faltante": {"alertar", "rejeitar"},
    "unidade_diferente": {"alertar", "rejeitar"},
    "ponto_diferente": {"alertar", "rejeitar"},
    "horas_incompletas": {"alertar", "rejeitar"},
    "variavel_toda_nula": {"alertar"},
}


def tipo_athena(tipo: pa.DataType) -> str:
    """Traduz o tipo do pyarrow para o vocabulário do Athena (o mesmo da tabela da Bronze).

    string e large_string são o mesmo "texto" para o Athena; a diferença é só de memória.
    Tipo desconhecido volta como está e, por isso, nunca bate com o contrato: falha alto.
    """
    if pa.types.is_null(tipo):
        return "null"
    if pa.types.is_string(tipo) or pa.types.is_large_string(tipo):
        return "string"
    if pa.types.is_int32(tipo):
        return "int"
    if pa.types.is_int64(tipo):
        return "bigint"
    if pa.types.is_float32(tipo):
        return "float"
    if pa.types.is_float64(tipo):
        return "double"
    if pa.types.is_boolean(tipo):
        return "boolean"
    if pa.types.is_timestamp(tipo):
        return "timestamp"
    return str(tipo)


def ler_colunas(caminho_parquet: str | Path) -> dict[str, str]:
    """Lê só o rodapé do Parquet e devolve {nome em minúsculas: tipo do Athena}."""
    schema = pq.read_schema(caminho_parquet)
    return {campo.name.lower(): tipo_athena(campo.type) for campo in schema}


def contar_linhas(caminho_parquet: str | Path) -> int:
    """Número de linhas, também lido do rodapé (sem carregar os dados)."""
    return pq.ParquetFile(caminho_parquet).metadata.num_rows


def calcular_schema_hash(colunas: dict[str, str]) -> str:
    """Impressão digital da lista nome:tipo.

    Ordenada por nome (a ordem das colunas no arquivo não conta como drift) e com nomes em
    minúsculas (ler_colunas já cuida disso). Mudou um nome ou um tipo: muda o hash.
    """
    texto = ",".join(f"{nome}:{tipo}" for nome, tipo in sorted(colunas.items()))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def carregar_contrato(fonte: str) -> dict:
    """Lê include/contratos/<fonte>.yml e confere se as regras são valores conhecidos."""
    contrato = yaml.safe_load((PASTA_CONTRATOS / f"{fonte}.yml").read_text(encoding="utf-8"))
    validas = _REGRAS_VALIDAS_CLIMA if fonte == "open_meteo" else _REGRAS_VALIDAS
    for regra, valor in contrato["regras"].items():
        if valor not in validas.get(regra, set()):
            raise ValueError(f"Contrato {fonte}: regra {regra!r} com valor inválido {valor!r}")
    return contrato


@dataclass
class ResultadoContrato:
    status: str  # "aceito" ou "rejeitado"
    schema_hash: str
    versao_contrato: int
    colunas_novas: list[str] = field(default_factory=list)
    colunas_faltantes: list[str] = field(default_factory=list)
    tipos_diferentes: list[str] = field(default_factory=list)
    colunas_tipo_nulo: list[str] = field(default_factory=list)

    @property
    def alertas(self) -> list[str]:
        """Frases curtas para o log e para a coluna motivo do manifesto."""
        frases = []
        if self.tipos_diferentes:
            frases.append("tipo diferente: " + "; ".join(self.tipos_diferentes))
        if self.colunas_novas:
            frases.append("coluna nova: " + ", ".join(self.colunas_novas))
        if self.colunas_faltantes:
            frases.append("coluna faltante: " + ", ".join(self.colunas_faltantes))
        if self.colunas_tipo_nulo:
            # Schema ok, mas uma coluna inteira vazia é alerta de QUALIDADE (Aula 4, caso c)
            frases.append("coluna toda vazia (tipo nulo): " + ", ".join(self.colunas_tipo_nulo))
        return frases

    @property
    def motivo(self) -> str | None:
        return " | ".join(self.alertas) or None


def validar(colunas_arquivo: dict[str, str], contrato: dict, source_month: str) -> ResultadoContrato:
    """Compara as colunas de um arquivo com o contrato, para um mês de referência (YYYY-MM).

    Uma coluna com `desde` posterior ao mês não é esperada naquele mês: a falta dela é normal.
    """
    regras = contrato["regras"]
    conhecidas = {c["nome"]: c["tipo"] for c in contrato["colunas"]}
    # "YYYY-MM" compara como texto na mesma ordem do tempo; sem `desde`, vale desde sempre
    esperadas = {
        c["nome"] for c in contrato["colunas"] if c.get("desde", "0000-00") <= source_month
    }

    novas = sorted(set(colunas_arquivo) - set(conhecidas))
    faltantes = sorted(esperadas - set(colunas_arquivo))

    diferentes, tipo_nulo = [], []
    for nome, tipo in sorted(colunas_arquivo.items()):
        if nome not in conhecidas or tipo == conhecidas[nome]:
            continue
        if tipo == "null" and regras["tipo_nulo_compativel"]:
            tipo_nulo.append(nome)
        else:
            diferentes.append(f"{nome} esperado {conhecidas[nome]}, veio {tipo}")

    rejeitar = (
        (diferentes and regras["tipo_diferente"] == "rejeitar")
        or (novas and regras["coluna_nova"] == "rejeitar")
        or (faltantes and regras["coluna_faltante"] == "rejeitar")
    )

    return ResultadoContrato(
        status="rejeitado" if rejeitar else "aceito",
        schema_hash=calcular_schema_hash(colunas_arquivo),
        versao_contrato=contrato["versao_contrato"],
        colunas_novas=novas,
        colunas_faltantes=faltantes,
        tipos_diferentes=diferentes,
        colunas_tipo_nulo=tipo_nulo,
    )


# ---------------------------------------------------------------------------------------------
# Clima (Open-Meteo, etapa 9). A resposta é JSON; o "schema" é variáveis + unidades + ponto + horas.
# ---------------------------------------------------------------------------------------------

def horas_esperadas_clima(mes: str) -> int:
    """Horas do arquivo do mês: o mês inteiro + o dia 1 do mês seguinte (W3), em UTC."""
    ano, numero = map(int, mes.split("-"))
    return (calendar.monthrange(ano, numero)[1] + 1) * 24


def validar_clima(dados: dict, contrato: dict, mes: str) -> ResultadoContrato:
    """Confere a resposta da API do clima contra o contrato. Função pura, como validar()."""
    regras = contrato["regras"]
    esperadas = {v["nome"]: v["unidade"] for v in contrato["variaveis"]}
    horario = dados.get("hourly", {})
    unidades = dados.get("hourly_units", {})
    recebidas = {nome: unidades.get(nome) for nome in horario if nome != "time"}

    novas = sorted(set(recebidas) - set(esperadas))
    faltantes = sorted(set(esperadas) - set(recebidas))
    unidades_erradas = [
        f"{nome} esperado {esperadas[nome]}, veio {recebidas[nome]}"
        for nome in sorted(set(esperadas) & set(recebidas))
        if recebidas[nome] != esperadas[nome]
    ]

    ponto = contrato["ponto"]
    ponto_errado = (
        abs(dados.get("latitude", 999) - ponto["latitude_grade"]) > ponto["tolerancia_graus"]
        or abs(dados.get("longitude", 999) - ponto["longitude_grade"]) > ponto["tolerancia_graus"]
    )

    horas = horas_esperadas_clima(mes)
    tamanhos = {nome: len(valores) for nome, valores in horario.items()}
    horas_erradas = not tamanhos or any(tamanho != horas for tamanho in tamanhos.values())

    toda_nula = sorted(nome for nome in recebidas if all(v is None for v in horario[nome]))

    # Mensagens (vão para o motivo do manifesto) e decisão, cada problema com a sua regra
    diferentes = list(unidades_erradas)
    if ponto_errado:
        diferentes.append(f"ponto esperado ({ponto['latitude_grade']}, {ponto['longitude_grade']}), "
                          f"veio ({dados.get('latitude')}, {dados.get('longitude')})")
    if horas_erradas:
        diferentes.append(f"horas esperadas {horas}, vieram {tamanhos}")

    rejeitar = (
        (unidades_erradas and regras["unidade_diferente"] == "rejeitar")
        or (ponto_errado and regras["ponto_diferente"] == "rejeitar")
        or (horas_erradas and regras["horas_incompletas"] == "rejeitar")
        or (novas and regras["variavel_nova"] == "rejeitar")
        or (faltantes and regras["variavel_faltante"] == "rejeitar")
    )
    # "schema" do clima: variável:unidade (mais o formato do tempo), ordenado
    assinatura = {nome: str(unidade) for nome, unidade in unidades.items()}
    return ResultadoContrato(
        status="rejeitado" if rejeitar else "aceito",
        schema_hash=calcular_schema_hash(assinatura),
        versao_contrato=contrato["versao_contrato"],
        colunas_novas=novas,
        colunas_faltantes=faltantes,
        tipos_diferentes=diferentes,
        colunas_tipo_nulo=toda_nula,
    )
