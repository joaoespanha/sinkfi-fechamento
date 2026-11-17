"""A sessão de cada requisição. Os testes trocam `obter_sessao` por `dependency_overrides`."""

import os
from collections.abc import Iterator
from functools import cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


@cache
def _engine() -> Engine:
    # Criado na primeira requisição: importar o app não exige DATABASE_URL.
    return create_engine(os.environ["DATABASE_URL"])


def obter_sessao() -> Iterator[Session]:
    with Session(_engine()) as sessao:
        yield sessao
