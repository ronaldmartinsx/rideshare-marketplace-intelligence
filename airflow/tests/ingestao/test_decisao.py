"""Testes da decisão da ingestão (Fase 2, etapa 5).

Um teste por cenário da tabela desenhada pelo Ronald (18/10/2026), mais o caso "a TLC volta a
servir um arquivo antigo". Rodar: cd airflow && astro dev pytest tests/ingestao/test_decisao.py
"""

from include.ingestao.decisao import (
    LinhaManifesto,
    RespostaHead,
    classificar_download,
    decidir_acao,
)

ETAG_A = '"82b3922bcddc3e88ef5b27d1329be178-94"'
ETAG_B = '"0075ffa5d0ecb2946a4b4e8f2d7158a5-30"'
SHA_1 = "fcdef276f4e9887f2beab30590165cdea74caef50a1313d71fa01ff6afacca3a"
SHA_2 = "0000000000000000000000000000000000000000000000000000000000000002"

# Em todos os cenários, o mês mais recente aceito é 2026-08
PROXIMO = "2026-09"


def linha(ingest_ts: str, etag: str, sha: str, status: str) -> LinhaManifesto:
    """Atalho para montar uma linha do manifesto."""
    return LinhaManifesto(ingest_ts=ingest_ts, etag=etag, file_sha256=sha, status=status)


# Linhas reutilizadas nos cenários
VERSAO_1_ACEITA = linha("20261012T230806", ETAG_A, SHA_1, "aceito")
# Conferência: ETag novo, mesmo conteúdo da versão 1 (copia o ingest_ts dela)
CONFERENCIA_ETAG_B = linha("20261012T230806", ETAG_B, SHA_1, "mesmo_conteudo")


# ---------------------------------------------------------------- decidir_acao: HEAD 200

def test_cenario_1_mes_inedito_publicado_e_baixado():
    resposta = RespostaHead(status=200, etag=ETAG_A)
    assert decidir_acao("2024-03", resposta, historico=[], proximo_mes_esperado=PROXIMO) == "baixar"


def test_cenario_2_mesmo_etag_da_versao_aceita_e_ignorado():
    resposta = RespostaHead(status=200, etag=ETAG_A)
    assert decidir_acao("2025-01", resposta, [VERSAO_1_ACEITA], PROXIMO) == "ignorar"


def test_cenario_3_etag_novo_e_reprocessado():
    resposta = RespostaHead(status=200, etag=ETAG_B)
    assert decidir_acao("2025-01", resposta, [VERSAO_1_ACEITA], PROXIMO) == "reprocessar"


def test_cenario_8_mesmo_arquivo_que_foi_rejeitado_e_erro():
    """Nada mudou na fonte: baixar de novo só repetiria a rejeição. Uma pessoa destrava."""
    rejeitada = linha("20261101T060000", ETAG_B, SHA_2, "rejeitado")
    resposta = RespostaHead(status=200, etag=ETAG_B)
    assert decidir_acao("2026-07", resposta, [rejeitada], PROXIMO) == "erro"


def test_cenario_9_arquivo_rejeitado_foi_corrigido_pela_tlc_e_reprocessado():
    rejeitada = linha("20261101T060000", ETAG_A, SHA_2, "rejeitado")
    resposta = RespostaHead(status=200, etag=ETAG_B)
    assert decidir_acao("2026-07", resposta, [rejeitada], PROXIMO) == "reprocessar"


def test_cenario_10_etag_ja_conferido_ontem_e_ignorado():
    """A conferência de ontem (mesmo_conteudo) evita o re-download eterno."""
    resposta = RespostaHead(status=200, etag=ETAG_B)
    historico = [VERSAO_1_ACEITA, CONFERENCIA_ETAG_B]
    assert decidir_acao("2025-01", resposta, historico, PROXIMO) == "ignorar"


# ---------------------------------------------------------------- decidir_acao: HEAD 403

def test_cenario_4_403_no_mes_esperado_e_aguardar():
    resposta = RespostaHead(status=403)
    assert decidir_acao("2026-09", resposta, [], PROXIMO) == "aguardar"


def test_cenario_5_403_depois_do_mes_esperado_e_aguardar():
    resposta = RespostaHead(status=403)
    assert decidir_acao("2026-10", resposta, [], PROXIMO) == "aguardar"


def test_cenario_6_403_em_mes_que_ja_existia_e_erro():
    resposta = RespostaHead(status=403)
    assert decidir_acao("2025-01", resposta, [VERSAO_1_ACEITA], PROXIMO) == "erro"


def test_cenario_7_403_em_mes_antigo_nunca_ingerido_e_erro():
    resposta = RespostaHead(status=403)
    assert decidir_acao("2024-03", resposta, [], PROXIMO) == "erro"


def test_403_no_mes_esperado_que_ja_foi_rejeitado_e_erro():
    """O mês mais novo foi rejeitado (proximo_mes_esperado aponta para ele) e depois sumiu."""
    rejeitada = linha("20261001T060000", ETAG_A, SHA_2, "rejeitado")
    resposta = RespostaHead(status=403)
    assert decidir_acao("2026-08", resposta, [rejeitada], "2026-08") == "erro"


# ---------------------------------------------------------------- decidir_acao: outros status

def test_cenario_11_503_que_chegou_ate_aqui_e_erro():
    """A camada HTTP + retry do Airflow deveriam ter tratado o 503 antes. Chegou: falha alta."""
    resposta = RespostaHead(status=503)
    assert decidir_acao("2025-01", resposta, [VERSAO_1_ACEITA], PROXIMO) == "erro"


# ---------------------------------------------------------------- classificar_download

def test_cenario_a_mesmo_sha_da_versao_aceita_e_mesmo_conteudo():
    assert classificar_download(SHA_1, [VERSAO_1_ACEITA]) == "mesmo_conteudo"


def test_cenario_b_sha_diferente_e_nova_versao():
    assert classificar_download(SHA_2, [VERSAO_1_ACEITA]) == "nova_versao"


def test_cenario_c_primeira_vez_e_nova_versao():
    assert classificar_download(SHA_1, []) == "nova_versao"


def test_cenario_d_mesmo_sha_do_arquivo_rejeitado_e_mesmo_conteudo():
    rejeitada = linha("20261101T060000", ETAG_B, SHA_2, "rejeitado")
    assert classificar_download(SHA_2, [rejeitada]) == "mesmo_conteudo"


def test_conferencia_nao_conta_como_versao():
    """Só a conferência no histórico (sem versão com arquivo): o conteúdo não está na Bronze."""
    assert classificar_download(SHA_1, [CONFERENCIA_ETAG_B]) == "nova_versao"


# ---------------------------------------------------------------- a TLC volta ao arquivo antigo

VERSAO_2_ACEITA = linha("20261201T060000", ETAG_B, SHA_2, "aceito")


def test_volta_ao_antigo_decidir_reprocessa():
    """O ETag A já foi visto, mas ligado ao SHA 1, que não é mais o da última versão."""
    resposta = RespostaHead(status=200, etag=ETAG_A)
    historico = [VERSAO_1_ACEITA, VERSAO_2_ACEITA]
    assert decidir_acao("2025-01", resposta, historico, PROXIMO) == "reprocessar"


def test_volta_ao_antigo_classificar_vira_nova_versao():
    """O conteúdo antigo precisa virar versão nova para voltar a ser o vigente."""
    historico = [VERSAO_1_ACEITA, VERSAO_2_ACEITA]
    assert classificar_download(SHA_1, historico) == "nova_versao"
