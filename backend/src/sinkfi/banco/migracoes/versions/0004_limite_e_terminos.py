"""Registro das mudanças de limite e dos "Terminei" (#12). Só inserção: nada é editado nem apagado.

Revision ID: 0004
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mudancas_limite",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("cliente_id", sa.Text, sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("em", sa.DateTime(timezone=True), nullable=False),
        # NULL = trava desligada (ADR 0003).
        sa.Column("de_centavos", sa.BigInteger),
        sa.Column("para_centavos", sa.BigInteger),
    )
    op.create_index("ix_mudancas_limite_cliente_id", "mudancas_limite", ["cliente_id"])
    op.create_table(
        "terminos",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("cliente_id", sa.Text, sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("usuario_id", sa.BigInteger, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rodada_id", sa.BigInteger, sa.ForeignKey("rodadas.id"), nullable=False),
        sa.Column("limite_trava_centavos", sa.BigInteger),
        # Cópia do resumo que a lojista viu; ninguém consulta por campo.
        sa.Column("resumo", JSONB, nullable=False),
    )
    op.create_index("ix_terminos_cliente_id", "terminos", ["cliente_id"])


def downgrade() -> None:
    op.drop_table("terminos")
    op.drop_table("mudancas_limite")
