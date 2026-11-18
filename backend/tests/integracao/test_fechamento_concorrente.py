"""Dois processos no mesmo cliente ao mesmo tempo (ADR 0004): a fila entrega pedidos repetidos em paralelo.

Aqui o commit é de verdade, entre duas conexões. Por isso cada teste ganha um banco só dele,
no mesmo container, e não usa a sessão desfeita no fim do `conftest`.
"""

import threading
import time as relogio
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from fechamento import VERSAO_DA_REGRA
from sinkfi.banco import migrar, repositorios
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.rodadas import hash_da_rodada, rodar_fechamento
from sinkfi.tipos import Rodada

from tests.integracao.cenarios import MARINA, dados_com_credito_a_mais, preparar_marina

CORTE = datetime(2026, 11, 10, 18, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))


@pytest.fixture
def banco(engine: Engine) -> Iterator[Engine]:
    nome = f"concorrente_{uuid4().hex[:8]}"
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conexao:
        conexao.execute(text(f"CREATE DATABASE {nome}"))
    url = engine.url.set(database=nome)
    migrar(url.render_as_string(hide_password=False))
    proprio = create_engine(url)
    with Session(proprio) as sessao, sessao.begin():
        preparar_marina(sessao)
    yield proprio
    proprio.dispose()
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conexao:
        conexao.execute(text(f"DROP DATABASE {nome} WITH (FORCE)"))


class EmOutraConexao(threading.Thread):
    """Roda `trabalho` numa sessão e numa transação próprias, e guarda o resultado ou o erro."""

    def __init__(self, banco: Engine, trabalho: Callable[[Session], Rodada]):
        super().__init__()
        self.banco, self.trabalho = banco, trabalho
        self.resultado: Rodada | None = None
        self.erro: Exception | None = None

    def run(self) -> None:
        try:
            with Session(self.banco) as sessao, sessao.begin():
                self.resultado = self.trabalho(sessao)
        except Exception as erro:  # noqa: BLE001
            self.erro = erro


def esperar_ate_bloquear(banco: Engine, outra: threading.Thread) -> bool:
    """Devolve True quando alguma conexão do banco está parada esperando uma trava, e False se `outra` terminou antes."""
    with banco.connect() as conexao:
        for _ in range(100):
            esperando = conexao.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'")
            ).scalar_one()
            if esperando:
                return True
            if not outra.is_alive():
                return False
            relogio.sleep(0.05)
    raise AssertionError("a outra conexão não terminou nem ficou esperando")


def test_dois_pedidos_ao_mesmo_tempo_devolvem_a_mesma_rodada(banco: Engine):
    with Session(banco) as primeira, primeira.begin():
        rodada = rodar_fechamento(primeira, MARINA, CORTE)
        segunda = EmOutraConexao(banco, lambda s: rodar_fechamento(s, MARINA, CORTE))
        segunda.start()
        esperar_ate_bloquear(banco, segunda)
    segunda.join()

    # O segundo pedido não é falha: é a mesma rodada, e não vai para a dead letter.
    assert segunda.erro is None
    assert segunda.resultado.id == rodada.id


def test_rodada_espera_a_ingestao_em_andamento(banco: Engine, tmp_path: Path):
    with Session(banco) as ingestao, ingestao.begin():
        ingerir(ingestao, MARINA, dados_com_credito_a_mais(tmp_path))
        rodada = EmOutraConexao(banco, lambda s: rodar_fechamento(s, MARINA, CORTE))
        rodada.start()
        esperar_ate_bloquear(banco, rodada)
    rodada.join()

    # A rodada lê a entrada inteira depois da ingestão, nunca uma parte de antes e outra de depois.
    with Session(banco) as sessao:
        entrada = repositorios.entrada_do_cliente(sessao, MARINA)
    assert rodada.erro is None
    assert rodada.resultado.hash_entrada == hash_da_rodada(entrada, CORTE, VERSAO_DA_REGRA)
