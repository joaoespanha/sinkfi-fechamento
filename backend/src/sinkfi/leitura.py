"""O fechamento como a tela lê: a rodada mais recente da semana e o resumo com o limite de agora (ADR 0006 e 0007).

A rodada guarda as pendências, não a recomendação: o limite pode mudar depois do cálculo.
As resoluções (ADR 0014) também são lidas na hora: a pendência resolvida sai do resumo, e a rodada não muda.
"""

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from fechamento import Pendencia, Resumo, Severidade, resumo
from sinkfi.banco import repositorios
from sinkfi.semanas import dia_do_item
from sinkfi.tipos import Conferencia, ItemRodada, Resolucao, Rodada


@dataclass(frozen=True)
class ItemDoDia:
    item: ItemRodada
    # O dia da semana em que o item aparece (#26). None = antes desta semana.
    dia: date | None
    # A resolução em vigor que vale para este item (ADR 0014). None = não resolvido.
    resolucao: Resolucao | None = None


@dataclass(frozen=True)
class FechamentoLido:
    rodada: Rodada
    resumo: Resumo
    limite_trava_centavos: int | None
    itens: list[ItemDoDia]
    # A conferência mais recente das rodadas desta semana. A tela compara a rodada dela com a mostrada.
    ultima_conferencia: Conferencia | None
    # A última ingestão do cliente (ADR 0011), não a hora da rodada. None = nunca teve ingestão.
    ultima_ingestao_em: datetime | None


def fechamento_da_semana(sessao: Session, cliente_id: str, data: date) -> FechamentoLido | None:
    """A rodada mais recente com aquela data de fechamento. None quando a semana não tem rodada."""
    rodada = next(
        (r for r in repositorios.rodadas_do_cliente(sessao, cliente_id) if r.data_fechamento == data), None
    )
    return fechamento_da_rodada(sessao, rodada) if rodada else None


def fechamento_da_rodada(sessao: Session, rodada: Rodada) -> FechamentoLido:
    itens = repositorios.itens_da_rodada(sessao, rodada.id)
    limite = repositorios.limite_do_cliente(sessao, rodada.cliente_id)
    # O corte pode voltar do banco em UTC: o dia de cada item é no fuso do cliente.
    fuso = ZoneInfo(repositorios.config_do_cliente(sessao, rodada.cliente_id).fuso)
    da_semana = {
        r.id for r in repositorios.rodadas_do_cliente(sessao, rodada.cliente_id)
        if r.data_fechamento == rodada.data_fechamento
    }
    conferencias = [t for t in repositorios.conferencias_do_cliente(sessao, rodada.cliente_id) if t.rodada_id in da_semana]
    resolucoes = repositorios.resolucoes_do_cliente(sessao, rodada.cliente_id)
    do_dia = [ItemDoDia(i, dia_do_item(i, rodada.corte, fuso), resolucao_do_item(i, resolucoes)) for i in itens]
    return FechamentoLido(
        rodada=rodada,
        resumo=resumo(_pendencias([d.item for d in do_dia if d.resolucao is None]), limite),
        limite_trava_centavos=limite,
        itens=do_dia,
        ultima_conferencia=conferencias[-1] if conferencias else None,
        ultima_ingestao_em=repositorios.ultima_ingestao_do_cliente(sessao, rodada.cliente_id),
    )


def resolucao_do_item(item: ItemRodada, resolucoes: dict[str, Resolucao]) -> Resolucao | None:
    """A resolução vale para o item de lançamento para conferir com o mesmo valor (ADR 0014)."""
    if item.recebiveis or item.severidade is not Severidade.PARA_CONFERIR or len(item.creditos) != 1:
        return None
    resolucao = resolucoes.get(item.creditos[0].id)
    if resolucao is None or resolucao.valor_centavos != item.pendencia_centavos:
        return None
    return resolucao


def _pendencias(itens: list[ItemRodada]) -> list[Pendencia]:
    """Os itens com severidade já são as pendências da rodada: nada é recalculado."""
    return [
        Pendencia(severidade=i.severidade, motivo=i.motivo, valor_centavos=i.pendencia_centavos)
        for i in itens
        if i.severidade and i.motivo and i.pendencia_centavos is not None
    ]
