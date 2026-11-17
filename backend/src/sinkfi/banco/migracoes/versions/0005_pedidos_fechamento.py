"""Outbox da ingestão (#11): o pedido de fechamento gravado na transação do dado.

Revision ID: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pedidos_fechamento",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("cliente_id", sa.Text, sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # NULL = pendente.
        sa.Column("publicado_em", sa.DateTime(timezone=True)),
    )
    # O relay só lê os pendentes, e a tabela só cresce.
    op.create_index(
        "ix_pedidos_fechamento_pendentes",
        "pedidos_fechamento",
        ["id"],
        postgresql_where=sa.text("publicado_em IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("pedidos_fechamento")
