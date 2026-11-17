"""O relay do outbox (ADR 0004): publica os pedidos de fechamento pendentes na fila.

Não conhece o Celery nem faz commit: a casca `sinkfi.tarefas.publicar_pedidos` é dona da transação.
"""

from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.fila import Fila

LOTE = 100


def publicar_pendentes(sessao: Session, fila: Fila, limite: int = LOTE) -> int:
    """Publica e marca na mesma transação. Se o commit falhar depois de publicar, o pedido sai
    de novo no próximo tick; a rodada idempotente absorve a duplicata. Devolve quantos publicou."""
    pedidos = repositorios.travar_pedidos_pendentes(sessao, limite)
    for pedido in pedidos:
        fila.pedir_fechamento(pedido.cliente_id)
    repositorios.marcar_publicados(sessao, [p.id for p in pedidos])
    return len(pedidos)
