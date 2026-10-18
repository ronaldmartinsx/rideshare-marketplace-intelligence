"""Testes da gravação na Bronze (Fase 2, etapa 6).

O S3 é substituído por um "S3 de mentira" em memória que imita o If-None-Match: grava se a
chave está livre e responde 412 se não está. A prova contra o S3 real (teste_bronze/) é feita
à parte, com a política do bucket ativa.
"""

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from botocore.exceptions import ClientError

from include.ingestao.bronze import (
    _sha256_em_base64,
    chave_bronze,
    gravar_sem_sobrescrever,
    novo_ingest_ts,
)
from include.ingestao.fonte_http import ErroTransitorio


def erro_s3(status: int, codigo: str) -> ClientError:
    return ClientError({"Error": {"Code": codigo}, "ResponseMetadata": {"HTTPStatusCode": status}}, "PutObject")


class S3DeMentira:
    def __init__(self):
        self.objetos = {}  # chave -> checksum em base64
        self.falhar_com = None

    def put_object(self, Bucket, Key, Body, IfNoneMatch, ChecksumSHA256):
        if self.falhar_com:
            raise self.falhar_com
        assert IfNoneMatch == "*"  # o código nunca pode esquecer a fechadura
        if Key in self.objetos:
            raise erro_s3(412, "PreconditionFailed")
        self.objetos[Key] = ChecksumSHA256

    def head_object(self, Bucket, Key, ChecksumMode):
        return {"ChecksumSHA256": self.objetos[Key]}


@pytest.fixture
def arquivo(tmp_path):
    caminho = tmp_path / "a.parquet"
    caminho.write_bytes(b"conteudo")
    return caminho, hashlib.sha256(b"conteudo").hexdigest()


def test_ingest_ts_e_utc_no_formato_da_pasta():
    agora = datetime(2026, 10, 18, 3, 4, 5, tzinfo=timezone(timedelta(hours=-4)))  # 03:04 em NY
    assert novo_ingest_ts(agora) == "20261018T070405"  # 07:04 em UTC


def test_chave_segue_o_molde_da_projection():
    chave = chave_bronze("bronze", "tlc_hvfhv", "2025-01", "20261012T230806", "fhvhv_tripdata_2025-01.parquet")
    assert chave == "bronze/tlc_hvfhv/year=2025/month=01/ingest_ts=20261012T230806/fhvhv_tripdata_2025-01.parquet"


def test_caminho_livre_grava(arquivo):
    s3, (caminho, sha) = S3DeMentira(), arquivo
    assert gravar_sem_sobrescrever(s3, "k", caminho, sha) == "gravado"


def test_retry_com_o_mesmo_conteudo_e_ja_existia(arquivo):
    """O cenário do D3: o upload deu certo, a task caiu antes do manifesto, o retry chega."""
    s3, (caminho, sha) = S3DeMentira(), arquivo
    gravar_sem_sobrescrever(s3, "k", caminho, sha)
    assert gravar_sem_sobrescrever(s3, "k", caminho, sha) == "ja_existia"


def test_caminho_com_outro_conteudo_falha_alto_sem_sobrescrever(arquivo):
    s3, (caminho, sha) = S3DeMentira(), arquivo
    s3.objetos["k"] = _sha256_em_base64(hashlib.sha256(b"outro").hexdigest())
    with pytest.raises(RuntimeError, match="OUTRO conteúdo"):
        gravar_sem_sobrescrever(s3, "k", caminho, sha)
    assert s3.objetos["k"] == _sha256_em_base64(hashlib.sha256(b"outro").hexdigest())


def test_conflito_409_e_transitorio(arquivo):
    s3, (caminho, sha) = S3DeMentira(), arquivo
    s3.falhar_com = erro_s3(409, "ConditionalRequestConflict")
    with pytest.raises(ErroTransitorio):
        gravar_sem_sobrescrever(s3, "k", caminho, sha)


def test_acesso_negado_falha_alto(arquivo):
    s3, (caminho, sha) = S3DeMentira(), arquivo
    s3.falhar_com = erro_s3(403, "AccessDenied")
    with pytest.raises(ClientError):
        gravar_sem_sobrescrever(s3, "k", caminho, sha)
