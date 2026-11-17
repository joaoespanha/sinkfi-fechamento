"""Tabelas de entrada (clientes, lojas, recebíveis, lançamentos) e rodadas.

Revision ID: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("nome", sa.Text, nullable=False),
        sa.Column("dia_fechamento", sa.SmallInteger, nullable=False),
        sa.Column("hora_corte", sa.Time, nullable=False),
        sa.Column("fuso", sa.Text, nullable=False),
        sa.Column("limite_trava_centavos", sa.BigInteger),
    )
    op.create_table(
        "lojas",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("cliente_id", sa.Text, sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("nome", sa.Text, nullable=False),
        sa.Column("documento", sa.Text, nullable=False),
        sa.Column("adquirente", sa.Text, nullable=False),
    )
    op.create_table(
        "recebiveis",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("loja_id", sa.Text, sa.ForeignKey("lojas.id"), nullable=False),
        sa.Column("adquirente", sa.Text, nullable=False),
        sa.Column("trilho", sa.Text, nullable=False),
        sa.Column("vendido_em", sa.Date, nullable=False),
        sa.Column("liquidacao_prevista", sa.Date, nullable=False),
        sa.Column("bruto_centavos", sa.BigInteger, nullable=False),
        sa.Column("mdr_centavos", sa.BigInteger, nullable=False),
        sa.Column("antecipacao_centavos", sa.BigInteger, nullable=False),
        sa.Column("liquido_centavos", sa.BigInteger, nullable=False),
        sa.Column("nsu", sa.Text, nullable=False),
        sa.Column("parcela", sa.SmallInteger, nullable=False),
        sa.Column("parcelas", sa.SmallInteger, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
    )
    op.create_table(
        "lancamentos",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("cliente_id", sa.Text, sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("transacao_id", sa.Text, nullable=False),
        sa.Column("transacao_original_id", sa.Text),
        sa.Column("lancado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valor_centavos", sa.BigInteger, nullable=False),
        sa.Column("nome_contraparte", sa.Text, nullable=False),
        sa.Column("documento_contraparte", sa.Text, nullable=False),
        sa.Column("descricao", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("tipo", sa.Text, nullable=False),
    )
    op.create_table(
        "rodadas",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("cliente_id", sa.Text, sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("data_fechamento", sa.Date, nullable=False),
        sa.Column("corte", sa.DateTime(timezone=True), nullable=False),
        sa.Column("versao_regra", sa.Text, nullable=False),
        sa.Column("hash_entrada", sa.Text, nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("cliente_id", "data_fechamento", "hash_entrada"),
    )


def downgrade() -> None:
    for tabela in ("rodadas", "lancamentos", "recebiveis", "lojas", "clientes"):
        op.drop_table(tabela)
