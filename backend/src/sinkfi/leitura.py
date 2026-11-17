"""O fechamento como a tela lê: a rodada mais recente e o resumo com o limite de agora (ADR 0006).

A rodada guarda as pendências, não a recomendação: o limite pode mudar depois do cálculo.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from fechamento import Pendencia, Resumo, resumo
from sinkfi.banco import repositorios
from sinkfi.tipos import ItemRodada, Rodada


@dataclass(frozen=True)
class FechamentoLido:
    rodada: Rodada
    resumo: Resumo
    limite_trava_centavos: int | None
    itens: list[ItemRodada]


def fechamento_mais_recente(sessao: Session, cliente_id: str) -> FechamentoLido | None:
    """None quando o cliente ainda não tem rodada."""
    rodadas = repositorios.rodadas_do_cliente(sessao, cliente_id)
    if not rodadas:
        return None
    rodada = rodadas[0]
    itens = repositorios.itens_da_rodada(sessao, rodada.id)
    limite = repositorios.limite_do_cliente(sessao, cliente_id)
    return FechamentoLido(
        rodada=rodada,
        resumo=resumo(_pendencias(itens), limite),
        limite_trava_centavos=limite,
        itens=itens,
    )


def _pendencias(itens: list[ItemRodada]) -> list[Pendencia]:
    """Os itens com severidade já são as pendências da rodada: nada é recalculado."""
    return [
        Pendencia(severidade=i.severidade, motivo=i.motivo, valor_centavos=i.pendencia_centavos)
        for i in itens
        if i.severidade and i.motivo and i.pendencia_centavos is not None
    ]
