"""Pedido de fechamento: o que o worker faz com uma mensagem da fila (ADR 0004).

Não conhece o Celery nem faz commit: a casca em `sinkfi.tarefas` abre a sessão e é dona da transação.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.rodadas import fechamento_vigente, rodar_fechamento
from sinkfi.tipos import Rodada


class ClienteDesconhecido(LookupError):
    """O pedido cita um cliente que não existe. Tentar de novo não resolve."""


def processar_pedido(
    sessao: Session, cliente_id: str, agora: datetime, corte_fixo: datetime | None = None
) -> Rodada:
    """Roda o fechamento vigente em `agora`. O pedido repetido devolve a rodada que já existe.

    `corte_fixo` só existe na demonstração e passa por cima do fechamento vigente.
    """
    config = repositorios.config_do_cliente(sessao, cliente_id)
    if config is None:
        raise ClienteDesconhecido(cliente_id)
    return rodar_fechamento(sessao, cliente_id, corte_fixo or fechamento_vigente(config, agora))
