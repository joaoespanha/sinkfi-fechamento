"""A fila (ADR 0004): o app do Celery, a dead letter e a porta que a api e o relay do outbox usam para pedir trabalho.

A api importa daqui só a porta `Fila`; as tarefas ficam em `sinkfi.tarefas`, que só o worker e o beat carregam.
"""

import os
from datetime import datetime
from typing import Protocol

from celery import Celery
from kombu import Exchange, Queue

FILA = "fechamento"
FILA_MORTA = "fechamento.morta"
FILA_OUTBOX = "outbox"

# A mensagem que falha de vez é rejeitada sem voltar para a fila, e o RabbitMQ a manda para cá.
fila_morta = Queue(FILA_MORTA, Exchange(FILA_MORTA, type="direct"), routing_key=FILA_MORTA)
fila = Queue(
    FILA,
    Exchange(FILA, type="direct"),
    routing_key=FILA,
    queue_arguments={"x-dead-letter-exchange": FILA_MORTA, "x-dead-letter-routing-key": FILA_MORTA},
)

# Só o tick do relay, e sem dead letter: a mensagem não carrega trabalho, só manda olhar a tabela.
# O pedido pendente fica no Postgres, e o tick perdido ou expirado é coberto pelo próximo.
fila_outbox = Queue(FILA_OUTBOX, Exchange(FILA_OUTBOX, type="direct"), routing_key=FILA_OUTBOX)

app = Celery("sinkfi", broker=os.environ.get("BROKER_URL", "amqp://guest:guest@localhost:5672//"))
app.conf.update(
    task_queues=[fila, fila_outbox],
    task_routes={"sinkfi.publicar_pedidos": {"queue": FILA_OUTBOX}},
    task_default_queue=FILA,
    task_default_exchange=FILA,
    task_default_routing_key=FILA,
    # Confirma só depois de rodar: se o worker cair no meio, a mensagem volta para a fila.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Falhou de vez (erro que não é passageiro, ou acabaram as tentativas): rejeita e vai para a dead letter.
    task_acks_on_failure=False,
    worker_prefetch_multiplier=1,
    # Publicar espera o RabbitMQ confirmar que guardou a mensagem; se ele recusar, `send_task` lança.
    # Sem isso, o relay do outbox marcaria como publicado um pedido perdido no caminho.
    broker_transport_options={"confirm_publish": True},
    timezone="UTC",
)


class Fila(Protocol):
    def pedir_fechamento(self, cliente_id: str) -> None: ...

    def pedir_fechamento_da_semana(self, cliente_id: str, corte: datetime) -> None: ...

    def pedir_reprocessamento(self, cliente_id: str, corte: datetime) -> None: ...


class FilaCelery:
    """Publica pelo nome da tarefa, sem importar `sinkfi.tarefas`. O corte vai como texto ISO."""

    def pedir_fechamento(self, cliente_id: str) -> None:
        app.send_task("sinkfi.fechar_cliente", args=[cliente_id])

    def pedir_fechamento_da_semana(self, cliente_id: str, corte: datetime) -> None:
        app.send_task("sinkfi.fechar_semana", args=[cliente_id, corte.isoformat()])

    def pedir_reprocessamento(self, cliente_id: str, corte: datetime) -> None:
        app.send_task("sinkfi.reprocessar_cliente", args=[cliente_id, corte.isoformat()])


def obter_fila() -> Fila:
    """Dependência da api. Os testes trocam por `dependency_overrides`."""
    return FilaCelery()
