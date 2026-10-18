"""Gravação na Bronze: caminho da versão e upload que nunca sobrescreve (Fase 2, etapa 6; D3).

As quatro peças do D3, e onde cada uma mora:
1. ingest_ts decidido uma vez por run, antes do upload    -> novo_ingest_ts() + XCom (na DAG)
2. gravar com If-None-Match: *                            -> gravar_sem_sobrescrever()
3. política do bucket exigindo a condição                 -> infra/terraform/s3.tf
4. linha do manifesto por último                          -> manifesto.py (na DAG)
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path

from botocore.exceptions import ClientError

from include.ingestao.fonte_http import ErroTransitorio

BUCKET_LAKE = "rmartins-rideshare-lake"


def novo_ingest_ts(agora: datetime | None = None) -> str:
    """Identidade da versão: momento da ingestão em UTC, 'YYYYMMDDTHHMMSS' (ordena como o tempo)."""
    agora = agora or datetime.now(timezone.utc)
    return agora.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S")


def chave_bronze(prefixo: str, fonte: str, mes: str, ingest_ts: str, nome_arquivo: str) -> str:
    """Caminho da versão na Bronze (spec 6.2), igual ao molde da projection (bronze_tabelas.tf).

    prefixo: 'bronze' (produção) ou 'teste_bronze' (ambiente de teste).
    """
    ano, mes_numero = mes.split("-")
    return f"{prefixo}/{fonte}/year={ano}/month={mes_numero}/ingest_ts={ingest_ts}/{nome_arquivo}"


def _sha256_em_base64(sha256_hex: str) -> str:
    """O S3 recebe o SHA-256 em base64 (os mesmos 32 bytes, escritos de outro jeito)."""
    return base64.b64encode(bytes.fromhex(sha256_hex)).decode("ascii")


def gravar_sem_sobrescrever(s3, chave: str, caminho_local: Path, sha256_hex: str,
                            bucket: str = BUCKET_LAKE) -> str:
    """Grava o arquivo na Bronze só se o caminho estiver vazio.

    Devolve:
        "gravado"     o arquivo entrou agora.
        "ja_existia"  o caminho já tinha EXATAMENTE este conteúdo (ex.: retry depois de um
                      upload que deu certo). Seguro seguir: o resultado é o mesmo (idempotência).
    Lança:
        ErroTransitorio  conflito momentâneo (409) ou falha de rede: o retry do Airflow cuida.
        RuntimeError     o caminho já tinha OUTRO conteúdo. Não deveria acontecer nunca:
                         falha alta, e o arquivo existente fica intacto.
    """
    checksum = _sha256_em_base64(sha256_hex)
    try:
        with caminho_local.open("rb") as corpo:
            s3.put_object(
                Bucket=bucket,
                Key=chave,
                Body=corpo,
                IfNoneMatch="*",  # a fechadura: só grava se o caminho estiver vazio
                ChecksumSHA256=checksum,  # o S3 confere a integridade do que recebeu
            )
        return "gravado"
    except ClientError as erro:
        status_http = erro.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_http == 412:  # PreconditionFailed: o caminho já existe
            existente = s3.head_object(Bucket=bucket, Key=chave, ChecksumMode="ENABLED")
            if existente.get("ChecksumSHA256") == checksum:
                return "ja_existia"
            raise RuntimeError(
                f"s3://{bucket}/{chave} já existe com OUTRO conteúdo. Nada foi sobrescrito."
            ) from erro
        if status_http == 409 or (status_http or 0) >= 500:
            raise ErroTransitorio(f"PUT s3://{bucket}/{chave} respondeu {status_http}") from erro
        raise  # 403 (permissão, política do bucket) e outros: falha alta, com a mensagem da AWS
