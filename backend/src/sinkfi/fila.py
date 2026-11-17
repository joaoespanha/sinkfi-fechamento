"""A fila (ADR 0004): o app do Celery, a dead letter e a porta que a api e o relay do outbox usam para pedir trabalho.

A api importa daqui só a porta `Fila`; as tarefas ficam em `sinkfi.tarefas`, que só o worker e o beat carregam.
"""

import os
from typing import Protocol

from celery import Celery
from kombu import Exchange, Queue

FILA = "fechamento"
FILA_MORTA = "fechamento.morta"

# A mensagem que falha de vez é rejeitada sem voltar para a fila, e o RabbitMQ a manda para cá.
fila_morta = Queue(FILA_MORTA, Exchange(FILA_MORTA, type="direct"), routing_key=FILA_MORTA)
fila = Queue(
    FILA,
    Exchange(FILA, type="direct"),
    routing_key=FILA,
    queue_arguments={"x-dead-letter-exchange": FILA_MORTA, "x-dead-letter-routing-key": FILA_MORTA},
)

app = Celery("sinkfi", broker=os.environ.get("BROKER_URL", "amqp://guest:guest@localhost:5672//"))
app.conf.update(
    task_queues=[fila],
    task_default_queue=FILA,
    task_default_exchange=FILA,
    task_default_routing_key=FILA,
    # Confirma só depois de rodar: se o worker cair no meio, a mensagem volta para a fila.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Falhou de vez (erro que não é passageiro, ou acabaram as tentativas): rejeita e vai para a dead letter.
    task_acks_on_failure=False,
    worker_prefetch_multiplier=1,
    timezone="UTC",
)


class Fila(Protocol):
    def pedir_fechamento(self, cliente_id: str) -> None: ...

    def pedir_reprocessamento(self, cliente_id: str) -> None: ...


class FilaCelery:
    """Publica pelo nome da tarefa, sem importar `sinkfi.tarefas`."""

    def pedir_fechamento(self, cliente_id: str) -> None:
        app.send_task("sinkfi.fechar_cliente", args=[cliente_id])

    def pedir_reprocessamento(self, cliente_id: str) -> None:
        app.send_task("sinkfi.reprocessar_cliente", args=[cliente_id])


def obter_fila() -> Fila:
    """Dependência da api. Os testes trocam por `dependency_overrides`."""
    return FilaCelery()
