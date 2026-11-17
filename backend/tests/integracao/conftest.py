"""Postgres descartável para os testes de integração.

O container sobe uma vez por sessão e recebe as migrações. Cada teste roda numa
transação desfeita no fim: um commit do código vira savepoint e não escapa.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

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
