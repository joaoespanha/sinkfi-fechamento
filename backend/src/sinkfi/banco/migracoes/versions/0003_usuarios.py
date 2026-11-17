"""Usuários da tela: a lojista pertence a um cliente, o suporte a nenhum (ADR 0005).

Revision ID: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("senha_hash", sa.Text, nullable=False),
        sa.Column("papel", sa.Text, nullable=False),
        sa.Column("cliente_id", sa.Text, sa.ForeignKey("clientes.id")),
        sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "(papel = 'lojista' AND cliente_id IS NOT NULL)"
            " OR (papel = 'suporte' AND cliente_id IS NULL)",
            name="ck_usuarios_papel_e_cliente",
        ),
    )


def downgrade() -> None:
    op.drop_table("usuarios")
