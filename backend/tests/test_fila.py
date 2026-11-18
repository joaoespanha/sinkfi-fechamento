"""A fila (ADR 0004): o que tenta de novo, o que vai para a dead letter, e quando o beat dispara.

Sem RabbitMQ e sem Postgres. A tarefa roda com `apply()`, que faz as novas tentativas na hora,
sem esperar; o serviço que ela chama é trocado por um que falha.
"""

from contextlib import nullcontext

import pytest
from celery.utils.time import get_exponential_backoff_interval
from sqlalchemy.exc import IntegrityError, OperationalError

from sinkfi import tarefas
from sinkfi.pedidos import ClienteDesconhecido

TAREFAS_COM_RETRY = [tarefas.ingerir_cliente, tarefas.fechar_cliente, tarefas.fechar_semana, tarefas.reprocessar_cliente]

# O padrão do RabbitMQ 4.1: a mensagem sem ack por mais tempo que isso derruba o canal do worker.
CONSUMER_TIMEOUT = 30 * 60


class SessaoFalsa:
    def __init__(self, *_):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def begin(self):
        return nullcontext()


@pytest.fixture
def pedido_que_falha(monkeypatch: pytest.MonkeyPatch):
    """Troca o serviço do `fechar_cliente` por um que lança `erro`. Devolve a lista das chamadas."""

    def preparar(erro: Exception) -> list[str]:
        chamadas = []

        def processar_pedido(_sessao, cliente_id, *_, **__):
            chamadas.append(cliente_id)
            raise erro

        monkeypatch.setattr(tarefas, "engine", lambda: None)
        monkeypatch.setattr(tarefas, "Session", SessaoFalsa)
        monkeypatch.setattr(tarefas, "processar_pedido", processar_pedido)
        return chamadas

    return preparar


def test_banco_fora_do_ar_tenta_de_novo(pedido_que_falha):
    chamadas = pedido_que_falha(OperationalError("SELECT 1", {}, Exception("conexão recusada")))

    resultado = tarefas.fechar_cliente.apply(args=["cli_marina"])

    assert len(chamadas) > 1
    assert resultado.failed()


@pytest.mark.parametrize(
    "erro",
    [
        ClienteDesconhecido("cli_sumido"),
        IntegrityError("INSERT", {}, Exception("chave duplicada")),
        ValueError("dado ruim"),
    ],
    ids=["cliente desconhecido", "integridade", "bug"],
)
def test_erro_que_nao_e_passageiro_falha_de_primeira(pedido_que_falha, erro):
    # Falhou de primeira: o worker rejeita a mensagem e o RabbitMQ manda para a dead letter.
    chamadas = pedido_que_falha(erro)

    resultado = tarefas.fechar_cliente.apply(args=["cli_marina"])

    assert chamadas == ["cli_marina"]
    assert resultado.failed()


@pytest.mark.parametrize("tarefa", TAREFAS_COM_RETRY, ids=lambda t: t.name)
def test_aguenta_dez_minutos_de_banco_fora_do_ar(tarefa):
    # A espera cheia de cada tentativa. O sorteio escolhe entre zero e ela: na média, a janela é a metade.
    esperas = [
        get_exponential_backoff_interval(factor=1, retries=n, maximum=tarefa.retry_backoff_max)
        for n in range(tarefa.max_retries)
    ]

    # Uma queda curta do Postgres não manda o pedido para a dead letter: o outbox já o deu por publicado.
    assert sum(esperas) >= 10 * 60
    # A tentativa agendada fica no worker sem ack até a hora; mais que o `consumer_timeout`, o RabbitMQ a devolve.
    assert max(esperas) < CONSUMER_TIMEOUT
