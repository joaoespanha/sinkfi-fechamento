"""As tarefas do Celery: cascas finas que abrem a sessão, fazem o commit e chamam o serviço (ADR 0004).

Worker: `celery -A sinkfi.tarefas worker -Q fechamento`. Beat: `celery -A sinkfi.tarefas beat`, com exatamente uma cópia.
"""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from celery.signals import worker_ready
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from sinkfi.banco import engine, repositorios
from sinkfi.fila import app, fila_morta
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.pedidos import processar_pedido
from sinkfi.rodadas import reprocessar

log = logging.getLogger(__name__)

# Passageira é o banco fora do ar ou a conexão perdida. Qualquer outra exceção é bug ou dado
# ruim: tentar de novo não resolve, e a mensagem vai direto para a dead letter.
TENTA_DE_NOVO = dict(autoretry_for=(OperationalError,), retry_backoff=True, retry_jitter=True, max_retries=5)

app.conf.beat_schedule = {
    "ingestao-a-cada-6-horas": {"task": "sinkfi.agendar_ingestoes", "schedule": 6 * 60 * 60},
}


@worker_ready.connect
def _declarar_fila_morta(sender, **_) -> None:
    # O worker só declara a fila que consome; sem a fila morta declarada, a mensagem rejeitada se perde.
    with sender.app.connection_for_write() as conexao:
        fila_morta.bind(conexao.default_channel).declare()


@app.task(name="sinkfi.agendar_ingestoes")
def agendar_ingestoes() -> None:
    """Disparada pelo beat: um pedido de ingestão por cliente."""
    with Session(engine()) as sessao:
        ids = repositorios.ids_dos_clientes(sessao)
    for cliente_id in ids:
        ingerir_cliente.delay(cliente_id)


@app.task(name="sinkfi.ingerir_cliente", **TENTA_DE_NOVO)
def ingerir_cliente(cliente_id: str) -> None:
    # Na demonstração a fonte é uma pasta por cliente; em produção seria Open Finance e adquirentes.
    pasta = Path(os.environ.get("PASTA_DADOS", "dados")) / cliente_id
    if not pasta.is_dir():
        log.info("cliente %s sem pasta de dados em %s", cliente_id, pasta)
        return
    with Session(engine()) as sessao, sessao.begin():
        ingerir(sessao, cliente_id, pasta)
    # O #11 troca esta publicação pelo outbox, gravado na mesma transação da ingestão.
    fechar_cliente.delay(cliente_id)


@app.task(name="sinkfi.fechar_cliente", **TENTA_DE_NOVO)
def fechar_cliente(cliente_id: str) -> None:
    with Session(engine()) as sessao, sessao.begin():
        processar_pedido(sessao, cliente_id, datetime.now(UTC), corte_fixo=_corte_fixo())


@app.task(name="sinkfi.reprocessar_cliente", **TENTA_DE_NOVO)
def reprocessar_cliente(cliente_id: str) -> None:
    with Session(engine()) as sessao, sessao.begin():
        reprocessar(sessao, cliente_id)


def _corte_fixo() -> datetime | None:
    """Só na demonstração: os CSVs de `dados/` batem com o corte de 10/11, que não é um dia
    de fechamento da Marina. Fora dela, o corte vem de `fechamento_vigente`."""
    valor = os.environ.get("SINKFI_CORTE_FIXO")
    return datetime.fromisoformat(valor) if valor else None
