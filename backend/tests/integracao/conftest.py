"""Postgres descartável para os testes de integração.

O container sobe uma vez por sessão e recebe as migrações. Cada teste roda numa
transação desfeita no fim: um commit do código vira savepoint e não escapa.
"""

from collections.abc import Iterator
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from sinkfi.api import app, obter_agora, obter_sessao
from sinkfi.banco import migrar


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        migrar(url)
        engine = create_engine(url)
        yield engine
        engine.dispose()


@pytest.fixture
def sessao(engine: Engine) -> Iterator[Session]:
    with engine.connect() as conexao:
        transacao = conexao.begin()
        sessao = Session(bind=conexao, join_transaction_mode="create_savepoint")
        yield sessao
        sessao.close()
        transacao.rollback()


@pytest.fixture
def http(sessao: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Cliente HTTP sem login. https por causa do cookie `Secure` (ADR 0005).

    A api vê a demonstração (ADR 0007): cortes a partir de terça, 10/11 às 18:00, e a hora
    fixa em 17/11 às 21:00. Com os CSVs, o fechamento atual é 10/11.
    """
    monkeypatch.setenv("JWT_SECRET", "segredo-so-dos-testes-com-32-bytes-ou-mais")
    monkeypatch.setenv("SINKFI_ANCORA_DOS_CORTES", "2026-11-10T18:00:00-03:00")
    app.dependency_overrides[obter_sessao] = lambda: sessao
    app.dependency_overrides[obter_agora] = lambda: datetime(2026, 11, 17, 21, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    yield TestClient(app, base_url="https://testserver")
    app.dependency_overrides.clear()
