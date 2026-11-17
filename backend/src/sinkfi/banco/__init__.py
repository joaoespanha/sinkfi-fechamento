"""Acesso ao Postgres. As classes do SQLAlchemy ficam aqui dentro (ADR 0004)."""

from alembic import command
from alembic.config import Config


def migrar(url: str) -> None:
    """Leva o banco em `url` até a última migração."""
    config = Config()
    config.set_main_option("script_location", "sinkfi.banco:migracoes")
    # O ConfigParser do Alembic interpreta %, que aparece em senhas codificadas.
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")
