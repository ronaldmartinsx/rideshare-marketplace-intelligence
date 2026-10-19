"""Testes da conversa por HTTP (Fase 2, etapa 6).

Sobe um servidor HTTP de verdade, local e minúsculo, que imita a TLC: responde 200 com ETag,
403 para arquivo inexistente e 503 para "servidor fora do ar".
"""

import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from include.ingestao.fonte_http import ErroTransitorio, baixar, consultar_head, url_do_mes

CONTEUDO = b"conteudo de um parquet de mentira" * 1000
ETAG = '"abc123-2"'


class TlcDeMentira(BaseHTTPRequestHandler):
    def _responder(self, com_corpo: bool):
        if self.path.endswith("2025-01.parquet"):
            self.send_response(200)
            self.send_header("ETag", ETAG)
            self.send_header("Last-Modified", "Wed, 23 Apr 2025 16:30:36 GMT")
            self.send_header("Content-Length", str(len(CONTEUDO)))
            self.end_headers()
            if com_corpo:
                self.wfile.write(CONTEUDO)
        elif self.path.endswith("2026-09.parquet"):
            self.send_response(403)  # como o S3 da TLC: arquivo inexistente dá 403
            self.end_headers()
        else:
            self.send_response(503)
            self.end_headers()

    def do_HEAD(self):
        self._responder(com_corpo=False)

    def do_GET(self):
        self._responder(com_corpo=True)

    def log_message(self, *args):  # silencia o log do servidor nos testes
        pass


@pytest.fixture(scope="module")
def base_url():
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), TlcDeMentira)  # porta 0: o sistema escolhe
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_port}/trip-data"
    servidor.shutdown()


def test_url_do_mes_segue_o_padrao_da_tlc():
    assert url_do_mes("2025-01").endswith("/trip-data/fhvhv_tripdata_2025-01.parquet")


def test_head_200_traz_etag_com_aspas_data_e_tamanho(base_url):
    resposta = consultar_head(url_do_mes("2025-01", base_url))
    assert resposta.status == 200
    assert resposta.etag == ETAG
    assert resposta.last_modified.isoformat() == "2025-04-23T16:30:36+00:00"
    assert resposta.content_length == len(CONTEUDO)


def test_head_403_e_devolvido_para_a_decisao(base_url):
    """403 é resposta definitiva: quem decide o que significa é decidir_acao."""
    assert consultar_head(url_do_mes("2026-09", base_url)).status == 403


def test_head_503_lanca_erro_transitorio_para_o_retry(base_url):
    with pytest.raises(ErroTransitorio):
        consultar_head(url_do_mes("2099-01", base_url))


def test_servidor_inexistente_e_erro_transitorio():
    with pytest.raises(ErroTransitorio):
        consultar_head("http://127.0.0.1:9/nada.parquet")  # porta 9: ninguém escutando


def test_download_calcula_o_sha256_e_confere_o_tamanho(base_url, tmp_path):
    arquivo = baixar(url_do_mes("2025-01", base_url), len(CONTEUDO), pasta=str(tmp_path))
    assert arquivo.sha256 == hashlib.sha256(CONTEUDO).hexdigest()
    assert arquivo.tamanho == len(CONTEUDO)
    assert arquivo.caminho.read_bytes() == CONTEUDO


def test_download_com_tamanho_diferente_e_transitorio_e_nao_deixa_lixo(base_url, tmp_path):
    with pytest.raises(ErroTransitorio):
        baixar(url_do_mes("2025-01", base_url), tamanho_esperado=1, pasta=str(tmp_path))
    assert list(tmp_path.iterdir()) == []
