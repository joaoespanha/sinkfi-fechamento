"""Itens da rodada: valores em colunas, recebíveis e créditos em JSONB (ADR 0006).

Revision ID: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "itens_rodada",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("rodada_id", sa.BigInteger, sa.ForeignKey("rodadas.id"), nullable=False),
        sa.Column("esperado_centavos", sa.BigInteger),
        sa.Column("caiu_centavos", sa.BigInteger),
        sa.Column("nao_caiu_centavos", sa.BigInteger),
        sa.Column("proximo_fechamento_centavos", sa.BigInteger),
        sa.Column("severidade", sa.Text),
        sa.Column("motivo", sa.Text),
        sa.Column("pendencia_centavos", sa.BigInteger),
        sa.Column("recebiveis", JSONB, nullable=False),
        sa.Column("creditos", JSONB, nullable=False),
    )
    op.create_index("ix_itens_rodada_rodada_id", "itens_rodada", ["rodada_id"])
    # "Em quais rodadas o rec_7001 apareceu": recebiveis @> '[{"id": "rec_7001"}]'.
    op.create_index(
        "ix_itens_rodada_recebiveis",
        "itens_rodada",
        ["recebiveis"],
        postgresql_using="gin",
        postgresql_ops={"recebiveis": "jsonb_path_ops"},
    )


def downgrade() -> None:
    op.drop_table("itens_rodada")
