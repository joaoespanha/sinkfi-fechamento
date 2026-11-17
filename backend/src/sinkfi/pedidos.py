"""Pedido de fechamento: o que o worker faz com uma mensagem da fila (ADR 0004).

Não conhece o Celery nem faz commit: a casca em `sinkfi.tarefas` abre a sessão e é dona da transação.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from sinkfi.fechamentos import corte_atual
from sinkfi.rodadas import rodar_fechamento
from sinkfi.tipos import Rodada


class ClienteDesconhecido(LookupError):
    """O pedido cita um cliente que não existe. Tentar de novo não resolve."""


def processar_pedido(
    sessao: Session, cliente_id: str, agora: datetime, ancora: datetime | None = None
) -> Rodada:
    """Roda o fechamento atual em `agora` (ADR 0007). O pedido repetido devolve a rodada que já existe.

    O pedido da ingestão não leva corte (#11): o fechamento atual é calculado aqui, na hora.
    """
    corte = corte_atual(sessao, cliente_id, agora, ancora)
    if corte is None:
        raise ClienteDesconhecido(cliente_id)
    return rodar_fechamento(sessao, cliente_id, corte)
