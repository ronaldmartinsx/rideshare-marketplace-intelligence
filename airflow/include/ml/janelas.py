"""A regra das rodadas do backtest walk-forward (Fase 5, passo 5).

Módulo PURO: só strings de mês entram e saem. Nenhuma consulta, nenhuma credencial, nenhum pandas.
Mesma separação da Fase 2 (decisao.py × manifesto.py) e da Fase 3 (dbt_construcao.py × dbt_registro.py).

Por que isso merece arquivo próprio: "treinar com os cortes ANTERIORES a C e prever C" é exatamente
onde cabe um erro de um-a-mais. E um erro aqui não daria exceção nem teste vermelho — daria um WAPE
melhor, porque o modelo teria treinado com o mês que deveria adivinhar. É vazamento (Aula 2), cuja
assinatura é parecer sucesso. Sendo pura, a regra é provada por teste de unidade, sem nuvem.

Vocabulário (ver docs/glossario.md):
- corte: a última hora de um mês. Tudo depois dele é desconhecido para o modelo.
- mês-alvo: o mês seguinte ao corte, que é o que se prevê.
- corte avaliável: corte cujo mês-alvo já aconteceu, e portanto tem gabarito.
- corte de produção: o último corte, cujo mês-alvo ainda não aconteceu. É o "dia de valer".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

RODADAS_PADRAO = 6  # spec 9.1: backtest walk-forward mensal nos últimos 6 meses

# Uma rodada precisa de pelo menos um corte de treino: não se treina modelo com nada.
MIN_CORTES_TREINO = 1

TIPO_BACKTEST = "backtest"
TIPO_PRODUCAO = "producao"


@dataclass(frozen=True)
class Rodada:
    """Uma rodada: com que cortes treinar, e qual mês prever."""

    tipo: str                        # backtest (tem gabarito) ou producao (não tem)
    corte: str                       # mes_corte de onde a previsão parte (AAAA-MM)
    mes_alvo: str                    # mês previsto (AAAA-MM)
    cortes_treino: tuple[str, ...]   # mes_corte das linhas usadas no treino

    @property
    def avaliavel(self) -> bool:
        """Só a rodada de backtest pode ser medida: a de produção não tem gabarito."""
        return self.tipo == TIPO_BACKTEST


def proximo_mes(ano_mes: str) -> str:
    """'2026-12' -> '2027-01'. Evita date_add só para somar um mês a uma string."""
    ano, mes = (int(parte) for parte in ano_mes.split("-"))
    return f"{ano + 1}-01" if mes == 12 else f"{ano}-{mes + 1:02d}"


def planejar_rodadas(
    cortes_avaliaveis: Sequence[str],
    corte_producao: str | None = None,
    rodadas: int = RODADAS_PADRAO,
    min_cortes_treino: int = MIN_CORTES_TREINO,
) -> list[Rodada]:
    """As rodadas do backtest, da mais antiga para a mais nova, e a de produção no fim.

    cortes_avaliaveis: cortes cujo mês-alvo já aconteceu (ordem não importa, são ordenados aqui).
    corte_producao: o corte sem gabarito, se houver. Treina com TODOS os avaliáveis.
    rodadas: quantas rodadas de backtest pedir. Se houver menos cortes, devolve o que couber.
    min_cortes_treino: rodada com menos cortes de treino que isso é descartada.

    A regra de cada rodada de backtest: treinar com os cortes ESTRITAMENTE anteriores e prever o
    mês-alvo do corte da rodada. Como o mês-alvo de um corte é o mês seguinte a ele, treinar com
    cortes anteriores a C significa treinar com alvos de meses até C — todos já observados em C.
    Nenhum alvo do futuro entra no treino, e é essa a garantia que o teste de unidade prova.
    """
    ordenados = sorted(set(cortes_avaliaveis))

    planejadas: list[Rodada] = []
    for corte in ordenados[-rodadas:] if rodadas > 0 else []:
        treino = tuple(c for c in ordenados if c < corte)
        if len(treino) < min_cortes_treino:
            # Descartada de propósito, e o chamador compara len(planejadas) com o que pediu.
            continue
        planejadas.append(
            Rodada(
                tipo=TIPO_BACKTEST,
                corte=corte,
                mes_alvo=proximo_mes(corte),
                cortes_treino=treino,
            )
        )

    if corte_producao is not None:
        planejadas.append(
            Rodada(
                tipo=TIPO_PRODUCAO,
                corte=corte_producao,
                mes_alvo=proximo_mes(corte_producao),
                # Produção usa tudo que tem gabarito, inclusive os cortes do backtest
                cortes_treino=tuple(ordenados),
            )
        )

    return planejadas
