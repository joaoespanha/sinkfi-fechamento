"""A sessão de cada requisição. Os testes trocam `obter_sessao` por `dependency_overrides`."""

from collections.abc import Iterator

from sqlalchemy.orm import Session

from sinkfi.banco import engine


def obter_sessao() -> Iterator[Session]:
    with Session(engine()) as sessao:
        yield sessao
