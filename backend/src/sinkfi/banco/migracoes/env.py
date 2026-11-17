"""Ambiente do Alembic: a URL vem de `migrar(url)` ou da variável DATABASE_URL."""

import os

from alembic import context
from sqlalchemy import create_engine, pool

from sinkfi.banco.modelos import Base

url = context.config.get_main_option("sqlalchemy.url") or os.environ["DATABASE_URL"]
engine = create_engine(url, poolclass=pool.NullPool)

with engine.connect() as conexao:
    context.configure(connection=conexao, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
