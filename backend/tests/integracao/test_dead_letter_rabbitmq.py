"""A contagem da fila morta (ADR 0004) contra um RabbitMQ de verdade: é o que a `/operacao` mostra."""

from collections.abc import Iterator

import pytest
from kombu import Connection, Producer
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from sinkfi.fila import FilaCelery, fila_morta


@pytest.fixture(scope="session")
def rabbitmq() -> Iterator[str]:
    """A URL do broker. Sobe uma vez por sessão, como o Postgres do `conftest.py`."""
    container = DockerContainer("rabbitmq:4.1-management-alpine").with_exposed_ports(5672)
    with container.waiting_for(LogMessageWaitStrategy("Server startup complete")):
        url = f"amqp://guest:guest@{container.get_container_host_ip()}:{container.get_exposed_port(5672)}//"
        yield url


@pytest.fixture
def broker(rabbitmq: str) -> Iterator[str]:
    """O broker sem a fila morta: cada teste começa como o RabbitMQ antes de o worker subir."""
    yield rabbitmq
    with Connection(rabbitmq) as conexao:
        fila_morta.bind(conexao.default_channel).delete()


def test_dead_letter_sem_a_fila_declarada_conta_zero(broker: str):
    # O worker nunca subiu e não declarou a fila: não há mensagem perdida, e a rota não cai.
    assert FilaCelery(broker).mensagens_na_dead_letter() == 0


def test_dead_letter_conta_as_mensagens_da_fila(broker: str):
    with Connection(broker) as conexao:
        produtor = Producer(conexao.default_channel)
        for cliente_id in ["cli_marina", "cli_outro"]:
            produtor.publish(
                {"cliente_id": cliente_id},
                exchange=fila_morta.exchange,
                routing_key=fila_morta.routing_key,
                declare=[fila_morta],
            )

    fila = FilaCelery(broker)

    assert fila.mensagens_na_dead_letter() == 2
    # Contar não consome: as mensagens continuam lá para o suporte olhar.
    assert fila.mensagens_na_dead_letter() == 2


def test_dead_letter_com_credencial_errada_vem_nula(broker: str):
    # O RabbitMQ responde, mas recusa o login: para a rota, é o mesmo que fora do ar.
    assert FilaCelery(broker.replace("guest:guest", "guest:errada")).mensagens_na_dead_letter() is None
