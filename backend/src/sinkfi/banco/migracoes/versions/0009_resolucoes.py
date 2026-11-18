"""Resolução da pendência para conferir (ADR 0014). Só inserção: desfazer é um registro novo.

Revision ID: 0009
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resolucoes",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("cliente_id", sa.Text, sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("lancamento_id", sa.Text, nullable=False),
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("desfeita", sa.Boolean, nullable=False),
        # O valor da pendência resolvida e a nota. NULL só no registro de desfeita.
        sa.Column("valor_centavos", sa.BigInteger),
        sa.Column("nota", sa.Text),
        sa.ForeignKeyConstraint(
            ["cliente_id", "lancamento_id"],
            ["lancamentos.cliente_id", "lancamentos.id"],
            name="resolucoes_lancamento_fkey",
        ),
        sa.CheckConstraint(
            "desfeita OR (valor_centavos IS NOT NULL AND nota IS NOT NULL)",
            name="ck_resolucoes_valor_e_nota",
        ),
    )
    op.create_index("ix_resolucoes_cliente_id_lancamento_id", "resolucoes", ["cliente_id", "lancamento_id"])


def downgrade() -> None:
    op.drop_table("resolucoes")
