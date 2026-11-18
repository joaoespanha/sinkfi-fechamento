"""A fila (ADR 0004): o que tenta de novo, o que vai para a dead letter, e quando o beat dispara.

Sem RabbitMQ e sem Postgres. A tarefa roda com `apply()`, que faz as novas tentativas na hora,
sem esperar; o serviço que ela chama é trocado por um que falha.
"""

import copy
import logging
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest
from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery.signals import task_failure
from celery.schedules import maybe_schedule
from celery.utils.time import get_exponential_backoff_interval
from sqlalchemy.exc import IntegrityError, OperationalError

from sinkfi import tarefas
from sinkfi.fila import FilaCelery, fila_morta
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
        SoftTimeLimitExceeded(),
    ],
    ids=["cliente desconhecido", "integridade", "bug", "passou do limite de tempo"],
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


INGESTAO = tarefas.app.conf.beat_schedule["ingestao-a-cada-6-horas"]


def test_reiniciar_o_beat_nao_adia_a_ingestao():
    # O beat sem o arquivo de agenda (container recriado) conta a última execução a partir de quando subiu.
    subiu = datetime(2026, 11, 18, 5, 59, tzinfo=UTC)
    agenda = copy.copy(maybe_schedule(INGESTAO["schedule"], app=tarefas.app))
    agenda.nowfun = lambda: subiu

    # A ingestão segue o relógio (0, 6, 12 e 18h UTC), não a hora em que o beat subiu.
    assert agenda.remaining_estimate(subiu) <= timedelta(minutes=1)


def test_ingestao_agendada_com_o_worker_fora_expira_antes_da_proxima():
    # Sem expirar, as ingestões se acumulam na fila e rodam todas juntas quando o worker volta.
    assert 0 < INGESTAO["options"]["expires"] <= 6 * 60 * 60


def test_publicar_espera_o_rabbitmq_confirmar():
    # Sem a confirmação, `send_task` volta antes de o broker aceitar a mensagem, e o relay do outbox
    # marca como publicado um pedido que pode ter se perdido.
    assert tarefas.app.conf.broker_transport_options.get("confirm_publish") is True


TAREFAS = [t for nome, t in sorted(tarefas.app.tasks.items()) if nome.startswith("sinkfi.")]


@pytest.mark.parametrize("tarefa", TAREFAS, ids=lambda t: t.name)
def test_mensagem_que_derruba_o_processo_nao_volta_para_sempre(tarefa):
    # O processo que morre (falta de memória, por exemplo) conta como tentativa; acabadas as tentativas,
    # a mensagem vai para a dead letter, em vez de voltar para a fila e derrubar o próximo.
    assert tarefa.retry_on_worker_lost is True
    assert tarefa.max_retries is not None


def test_tarefa_presa_vai_para_a_dead_letter_antes_do_limite_duro():
    # O limite brando lança `SoftTimeLimitExceeded` dentro da tarefa: é uma falha comum, que vai para a dead letter.
    # O duro mata o processo e a mensagem recebe ack, sem dead letter: é só a rede de segurança.
    brando, duro = tarefas.app.conf.task_soft_time_limit, tarefas.app.conf.task_time_limit
    assert brando is not None and duro is not None
    assert brando < duro


def _fila_de(nome_da_tarefa: str):
    return tarefas.app.amqp.router.route({}, nome_da_tarefa)["queue"]


@pytest.mark.parametrize("tarefa", [t for t in TAREFAS if t.name != "sinkfi.publicar_pedidos"], ids=lambda t: t.name)
def test_trabalho_que_falha_de_vez_cai_na_fila_morta(tarefa):
    argumentos = _fila_de(tarefa.name).queue_arguments

    # O RabbitMQ manda a mensagem rejeitada para a exchange e a chave em que a fila morta está ligada.
    assert argumentos["x-dead-letter-exchange"] == fila_morta.exchange.name
    assert argumentos["x-dead-letter-routing-key"] == fila_morta.routing_key


def test_tick_do_outbox_tem_fila_propria_e_sem_dead_letter():
    # O tick não carrega trabalho: o perdido é coberto pelo próximo, e não deve encher a fila morta.
    fila = _fila_de("sinkfi.publicar_pedidos")

    assert fila.name != _fila_de("sinkfi.fechar_cliente").name
    assert not fila.queue_arguments


@pytest.fixture
def reprocessamento_que_falha(monkeypatch: pytest.MonkeyPatch):
    """Troca o serviço do `reprocessar_cliente` por um que lança cada erro de `erros`, um por chamada."""

    def preparar(*erros: Exception) -> None:
        restantes = list(erros)

        def reprocessar(*_):
            if restantes:
                raise restantes.pop(0)

        monkeypatch.setattr(tarefas, "engine", lambda: None)
        monkeypatch.setattr(tarefas, "Session", SessaoFalsa)
        monkeypatch.setattr(tarefas, "reprocessar", reprocessar)

    return preparar


CORTE_ISO = "2026-11-10T18:00:00-03:00"


def _dead_letters(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.getMessage().startswith("dead letter:")]


def test_falha_definitiva_registra_dead_letter_com_cliente_corte_e_erro(reprocessamento_que_falha, caplog):
    reprocessamento_que_falha(ValueError("dado ruim no ext_14"))

    tarefas.reprocessar_cliente.apply(args=["cli_marina", CORTE_ISO])

    # Uma linha por mensagem na fila morta, com o que o plantão precisa para achar o caso.
    [registro] = _dead_letters(caplog)
    assert registro.levelno == logging.ERROR
    mensagem = registro.getMessage()
    assert "cli_marina" in mensagem
    assert CORTE_ISO in mensagem
    assert "dado ruim no ext_14" in mensagem
    assert "reprocessamento pelo suporte" in mensagem


def test_nova_tentativa_nao_registra_dead_letter(reprocessamento_que_falha, caplog):
    # O banco caiu uma vez e voltou: a nova tentativa resolve, e nada foi para a fila morta.
    reprocessamento_que_falha(OperationalError("SELECT 1", {}, Exception("conexão recusada")))

    resultado = tarefas.reprocessar_cliente.apply(args=["cli_marina", CORTE_ISO])

    assert resultado.successful()
    assert _dead_letters(caplog) == []


def _falhar(tarefa, exception: Exception, *args: str) -> None:
    """Dispara o `task_failure` como o worker: o limite duro não acontece com `apply()`."""
    task_failure.send(sender=tarefa, task_id="t1", exception=exception, args=list(args), kwargs={}, traceback=None, einfo=None)


def test_limite_duro_nao_registra_dead_letter(caplog):
    # O limite duro mata o processo e a mensagem recebe ack: não está na fila morta, e a linha não pode dizer que está.
    _falhar(tarefas.reprocessar_cliente, TimeLimitExceeded(150), "cli_marina", CORTE_ISO)

    assert _dead_letters(caplog) == []
    [registro] = [r for r in caplog.records if r.getMessage().startswith("limite duro:")]
    assert registro.levelno == logging.ERROR
    assert "cli_marina" in registro.getMessage()
    assert CORTE_ISO in registro.getMessage()


def test_dead_letter_sem_corte_nao_registra_corte(caplog):
    # O pedido da ingestão não tem corte: a linha mostra só o que a tarefa recebeu.
    _falhar(tarefas.fechar_cliente, ValueError("dado ruim"), "cli_marina")

    [registro] = _dead_letters(caplog)
    assert "cli_marina" in registro.getMessage()
    assert "corte" not in registro.getMessage()


def test_dead_letter_com_o_rabbitmq_fora_vem_nula():
    # Porta recusada: responde na hora, sem esperar o `connect_timeout`.
    assert FilaCelery("amqp://guest:guest@127.0.0.1:1//").mensagens_na_dead_letter() is None
