"""A fila (ADR 0004): o app do Celery, a dead letter e a porta que a api e o relay do outbox usam para pedir
trabalho e para contar a fila morta.

A api importa daqui só a porta `Fila`; as tarefas ficam em `sinkfi.tarefas`, que só o worker e o beat carregam.
"""

import os
from datetime import datetime
from typing import Protocol

from amqp.exceptions import NotFound
from celery import Celery
from kombu import Exchange, Queue
from kombu.exceptions import OperationalError as BrokerFora

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
    # Mas o processo que morre conta como tentativa: acabadas as tentativas, vai para a dead letter.
    # Sem isso, a mensagem que derruba o processo (falta de memória, por exemplo) volta para sempre.
    task_retry_on_worker_lost=True,
    # O limite brando lança `SoftTimeLimitExceeded` dentro da tarefa, e ela vai para a dead letter.
    # O duro mata o processo e a mensagem recebe ack, sem dead letter: é só a rede de segurança.
    task_soft_time_limit=120,
    task_time_limit=150,
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

    def mensagens_na_dead_letter(self) -> int | None:
        """Quantas mensagens esperam na fila morta. `None` quando o broker não responde."""
        ...

    def broker_responde(self) -> bool:
        """O broker aceita conexão e login (`/health`)."""
        ...


class FilaCelery:
    """Publica pelo nome da tarefa, sem importar `sinkfi.tarefas`. O corte vai como texto ISO.

    `broker` troca a URL só da contagem da fila morta: é para os testes contra um RabbitMQ descartável.
    """

    def __init__(self, broker: str | None = None) -> None:
        self._broker = broker

    def pedir_fechamento(self, cliente_id: str) -> None:
        app.send_task("sinkfi.fechar_cliente", args=[cliente_id])

    def pedir_fechamento_da_semana(self, cliente_id: str, corte: datetime) -> None:
        app.send_task("sinkfi.fechar_semana", args=[cliente_id, corte.isoformat()])

    def pedir_reprocessamento(self, cliente_id: str, corte: datetime) -> None:
        app.send_task("sinkfi.reprocessar_cliente", args=[cliente_id, corte.isoformat()])

    def mensagens_na_dead_letter(self) -> int | None:
        # `passive` só pergunta: não cria a fila nem consome. Uma tentativa de até 2s, para a rota não travar.
        with app.connection_for_write(self._broker, connect_timeout=2) as conexao:
            try:
                conexao.ensure_connection(max_retries=0)
                return conexao.default_channel.queue_declare(FILA_MORTA, passive=True).message_count
            except NotFound:
                # O worker declara a fila ao subir (`tarefas._declarar_fila_morta`). Sem ela, nada se perdeu.
                return 0
            except (BrokerFora, *conexao.connection_errors, *conexao.channel_errors):
                # Fora do ar, porta recusada ou login recusado (`AccessRefused`, que é erro de canal).
                return None

    def broker_responde(self) -> bool:
        # A mesma tentativa única de até 2s da contagem: a sonda do compose não pode travar.
        with app.connection_for_write(self._broker, connect_timeout=2) as conexao:
            try:
                conexao.ensure_connection(max_retries=0)
                return True
            except (BrokerFora, *conexao.connection_errors, *conexao.channel_errors):
                return False


def obter_fila() -> Fila:
    """Dependência da api. Os testes trocam por `dependency_overrides`."""
    return FilaCelery()
