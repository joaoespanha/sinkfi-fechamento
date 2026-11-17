"""O fechamento como a tela lê: a rodada mais recente da semana e o resumo com o limite de agora (ADR 0006 e 0007).

A rodada guarda as pendências, não a recomendação: o limite pode mudar depois do cálculo.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from fechamento import Pendencia, Resumo, resumo
from sinkfi.banco import repositorios
from sinkfi.tipos import ItemRodada, Rodada, Termino


@dataclass(frozen=True)
class FechamentoLido:
    rodada: Rodada
    resumo: Resumo
    limite_trava_centavos: int | None
    itens: list[ItemRodada]
    # O "Terminei" mais recente das rodadas desta semana. A tela compara a rodada dele com a mostrada.
    ultimo_termino: Termino | None


def fechamento_da_semana(sessao: Session, cliente_id: str, data: date) -> FechamentoLido | None:
    """A rodada mais recente com aquela data de fechamento. None quando a semana não tem rodada."""
    rodada = next(
        (r for r in repositorios.rodadas_do_cliente(sessao, cliente_id) if r.data_fechamento == data), None
    )
    return fechamento_da_rodada(sessao, rodada) if rodada else None


def fechamento_da_rodada(sessao: Session, rodada: Rodada) -> FechamentoLido:
    itens = repositorios.itens_da_rodada(sessao, rodada.id)
    limite = repositorios.limite_do_cliente(sessao, rodada.cliente_id)
    da_semana = {
        r.id for r in repositorios.rodadas_do_cliente(sessao, rodada.cliente_id)
        if r.data_fechamento == rodada.data_fechamento
    }
    terminos = [t for t in repositorios.terminos_do_cliente(sessao, rodada.cliente_id) if t.rodada_id in da_semana]
    return FechamentoLido(
        rodada=rodada,
        resumo=resumo(_pendencias(itens), limite),
        limite_trava_centavos=limite,
        itens=itens,
        ultimo_termino=terminos[-1] if terminos else None,
    )


def _pendencias(itens: list[ItemRodada]) -> list[Pendencia]:
    """Os itens com severidade já são as pendências da rodada: nada é recalculado."""
    return [
        Pendencia(severidade=i.severidade, motivo=i.motivo, valor_centavos=i.pendencia_centavos)
        for i in itens
        if i.severidade and i.motivo and i.pendencia_centavos is not None
    ]
