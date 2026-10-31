"""Regra de pendência da dbt_build: quais meses construir (Fase 3, etapa 8). ✍️ Peça do Ronald.

Regra desenhada pelo Ronald na tabela de cenários (25/10/2026); código e testes escritos pelo
Claude a pedido dele (tests/test_dbt_construcao.py, um teste por linha da tabela).

Funções puras: recebem dados prontos e devolvem decisões. Não acessam o Athena. Quem lê a
manifesto_vigente e a dbt_meses_construidos_vigente é a DAG, antes de chamá-las.

    manifesto (versões vigentes) + registro (última construção, deste ambiente) + forcar_meses
        -> planejar_construcao(...) -> uma Decisao por mês, do mais antigo para o mais novo

A regra, na ordem em que é aplicada:
    1. Sem TLC ou sem clima vigente -> não constrói (o dbt não teria o que ler).
       Se o mês foi forçado, é um pedido não atendido: o run termina vermelho.
    2. Nunca construído, ou construído com outras versões -> constrói, motivo "manifesto".
    3. Forçado -> constrói, motivo "forcado".
    4. Senão -> não constrói (já está em dia).
O manifesto vem antes do forçado: se o dado mudou, esse é o motivo que fica registrado.

Quais meses são avaliados: em prod, todos do manifesto. Em dev (amostra, decisão de 25/10/2026),
só os que já estão no registro de dev e os forçados: um mês entra em dev quando é forçado uma vez.
"""

from __future__ import annotations

from dataclasses import dataclass

# Motivos gravados no registro (coluna motivo de controle.dbt_meses_construidos)
MOTIVO_MANIFESTO = "manifesto"
MOTIVO_FORCADO = "forcado"


@dataclass(frozen=True)
class Construcao:
    """A última construção que deu certo de um mês, neste ambiente (dbt_meses_construidos_vigente)."""

    ingest_ts_tlc: str
    ingest_ts_clima: str


@dataclass(frozen=True)
class Decisao:
    """O que fazer com um mês neste run."""

    mes: str
    construir: bool
    # Construir: "manifesto" | "forcado" (vai para o registro). Não construir: o porquê (vai para o log).
    motivo: str
    # Alguém pediu este mês em forcar_meses e ele não pode ser construído (linhas 7 e 8 da tabela)
    pedido_nao_atendido: bool = False


def decidir_mes(
    mes: str,
    tlc_vigente: str | None,
    clima_vigente: str | None,
    ultima_construcao: Construcao | None,
    forcado: bool,
) -> Decisao:
    """Decide um mês. Os argumentos são as colunas da tabela de cenários.

    Args:
        mes: 'YYYY-MM'.
        tlc_vigente: ingest_ts vigente da TLC no manifesto, ou None se não há versão aceita.
        clima_vigente: ingest_ts vigente do clima no manifesto, ou None.
        ultima_construcao: a última construção registrada NESTE ambiente, ou None se nunca houve.
        forcado: o mês está no parâmetro forcar_meses.
    """
    # 1) Dá para construir? A staging chama a macro ingest_ts_vigente, que quebra sem versão.
    if tlc_vigente is None or clima_vigente is None:
        faltando = [
            nome for nome, versao in (("TLC", tlc_vigente), ("clima", clima_vigente)) if versao is None
        ]
        motivo = f"sem versão vigente de {' e '.join(faltando)} na Bronze"
        # Sem pedido (linha 2): espera normal, o clima chega e dispara a dbt_build de novo.
        # Com pedido (linhas 7 e 8): alguém espera este mês; não pode passar em silêncio.
        return Decisao(mes, construir=False, motivo=motivo, pedido_nao_atendido=forcado)

    # 2) Já foi construído com estas versões? (linhas 1, 4 e 5)
    if ultima_construcao != Construcao(tlc_vigente, clima_vigente):
        return Decisao(mes, construir=True, motivo=MOTIVO_MANIFESTO)

    # 3) Em dia com o manifesto, mas alguém pediu (linha 6: o código do dbt mudou)
    if forcado:
        return Decisao(mes, construir=True, motivo=MOTIVO_FORCADO)

    # 4) Em dia e ninguém pediu (linha 3)
    return Decisao(mes, construir=False, motivo="já construído com as versões vigentes")


def planejar_construcao(
    tlc_vigentes: dict[str, str],
    clima_vigentes: dict[str, str],
    construidos: dict[str, Construcao],
    forcar_meses: list[str],
    somente_meses_conhecidos: bool = False,
) -> list[Decisao]:
    """Decide todos os meses de uma vez, do mais antigo para o mais novo.

    A ordem importa: o gate de volume de um mês compara com os 3 meses anteriores, então eles
    precisam estar construídos antes. "YYYY-MM" ordena como texto na mesma ordem do tempo.

    Args:
        tlc_vigentes: {mês: ingest_ts} da TLC na manifesto_vigente.
        clima_vigentes: {mês: ingest_ts} do clima na manifesto_vigente.
        construidos: {mês: Construcao} na dbt_meses_construidos_vigente, JÁ filtrada pelo ambiente.
        forcar_meses: meses pedidos à mão (parâmetro da dbt_build). Pode trazer mês inexistente.
        somente_meses_conhecidos: True em dev (amostra): avalia só os meses já construídos neste
            ambiente e os forçados; os outros meses do manifesto nem entram na lista.
    """
    # Os meses forçados entram sempre: um mês forçado sem dado nenhum também precisa de decisão
    if somente_meses_conhecidos:
        meses = sorted(set(construidos) | set(forcar_meses))
    else:
        meses = sorted(set(tlc_vigentes) | set(clima_vigentes) | set(forcar_meses))
    return [
        decidir_mes(
            mes,
            tlc_vigente=tlc_vigentes.get(mes),
            clima_vigente=clima_vigentes.get(mes),
            ultima_construcao=construidos.get(mes),
            forcado=mes in forcar_meses,
        )
        for mes in meses
    ]
