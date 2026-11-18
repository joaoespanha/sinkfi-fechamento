"""O "Terminei" passa a se chamar conferência (ADR 0012). Só nome: os registros continuam como estão.

Renomeia a tabela, o índice, as restrições e a sequência para os nomes que o Postgres daria a uma
tabela `conferencias` criada do zero.

Revision ID: 0008
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_RESTRICOES = ("pkey", "cliente_id_fkey", "usuario_id_fkey", "rodada_id_fkey")


def _renomear(de: str, para: str) -> None:
    op.rename_table(de, para)
    op.execute(f"ALTER INDEX ix_{de}_cliente_id RENAME TO ix_{para}_cliente_id")
    for restricao in _RESTRICOES:
        op.execute(f"ALTER TABLE {para} RENAME CONSTRAINT {de}_{restricao} TO {para}_{restricao}")
    op.execute(f"ALTER SEQUENCE {de}_id_seq RENAME TO {para}_id_seq")


def upgrade() -> None:
    _renomear("terminos", "conferencias")


def downgrade() -> None:
    _renomear("conferencias", "terminos")
