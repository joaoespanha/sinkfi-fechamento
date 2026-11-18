"""As tarefas do Celery: cascas finas que abrem a sessão, fazem o commit e chamam o serviço (ADR 0004).

Worker: `celery -A sinkfi.tarefas worker -Q fechamento,outbox`. Beat: `celery -A sinkfi.tarefas beat`, com exatamente uma cópia.
"""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from celery.signals import worker_ready
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from sinkfi.banco import engine, repositorios
from sinkfi.fechamentos import ancora_dos_cortes
from sinkfi.fila import FilaCelery, app, fila_morta
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.outbox import publicar_pendentes
from sinkfi.pedidos import processar_pedido
from sinkfi.rodadas import reprocessar, rodar_fechamento

log = logging.getLogger(__name__)

# Passageira é o banco fora do ar ou a conexão perdida. Qualquer outra exceção é bug ou dado
# ruim: tentar de novo não resolve, e a mensagem vai direto para a dead letter.
# Esperas de 1, 2, 4… até 300s: a queda de até ~13 min (~7 min na média, pelo sorteio) não vira dead letter.
# A tentativa agendada fica no worker sem ack até a hora: a espera máxima tem que ficar abaixo do
# `consumer_timeout` do RabbitMQ (30 min).
TENTA_DE_NOVO = dict(
    autoretry_for=(OperationalError,), retry_backoff=True, retry_backoff_max=300, retry_jitter=True, max_retries=10
)

app.conf.beat_schedule = {
    "ingestao-a-cada-6-horas": {"task": "sinkfi.agendar_ingestoes", "schedule": 6 * 60 * 60},
    # O relay do outbox, na fila `outbox`. Segundos para a demonstração. O tick que expira sem rodar
    # some (a fila não tem dead letter), para não acumular enquanto o worker estiver fora.
    "outbox-a-cada-10-segundos": {"task": "sinkfi.publicar_pedidos", "schedule": 10, "options": {"expires": 10}},
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
    # O pedido de fechamento é gravado junto com o dado; quem publica é o `publicar_pedidos`.
    with Session(engine()) as sessao, sessao.begin():
        ingerir(sessao, cliente_id, pasta)


@app.task(name="sinkfi.publicar_pedidos")
def publicar_pedidos() -> None:
    """Disparada pelo beat. Sem retry: o próximo tick tenta de novo o que ficou pendente."""
    with Session(engine()) as sessao, sessao.begin():
        publicar_pendentes(sessao, FilaCelery())


@app.task(name="sinkfi.fechar_cliente", **TENTA_DE_NOVO)
def fechar_cliente(cliente_id: str) -> None:
    """O pedido da ingestão, sem corte (#11): roda o fechamento atual."""
    with Session(engine()) as sessao, sessao.begin():
        processar_pedido(sessao, cliente_id, datetime.now(UTC), ancora=ancora_dos_cortes())


@app.task(name="sinkfi.fechar_semana", **TENTA_DE_NOVO)
def fechar_semana(cliente_id: str, corte: str) -> None:
    """O pedido de quem escolheu um fechamento sem rodada (ADR 0007). A api já conferiu o corte."""
    with Session(engine()) as sessao, sessao.begin():
        rodar_fechamento(sessao, cliente_id, datetime.fromisoformat(corte))


@app.task(name="sinkfi.reprocessar_cliente", **TENTA_DE_NOVO)
def reprocessar_cliente(cliente_id: str, corte: str) -> None:
    with Session(engine()) as sessao, sessao.begin():
        reprocessar(sessao, cliente_id, datetime.fromisoformat(corte))
