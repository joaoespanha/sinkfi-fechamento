"""Chave da entrada por cliente e por fonte (ADR 0009).

Os IDs vêm de fora e só são únicos dentro de quem os gerou: a loja, no cadastro do
cliente; o recebível, na adquirente; o lançamento, no extrato da conta do cliente.

Revision ID: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # O recebível chegava ao cliente pela loja; agora carrega o cliente, como as outras duas tabelas.
    op.add_column("recebiveis", sa.Column("cliente_id", sa.Text))
    op.execute("UPDATE recebiveis r SET cliente_id = l.cliente_id FROM lojas l WHERE l.id = r.loja_id")
    op.alter_column("recebiveis", "cliente_id", nullable=False)
    op.create_foreign_key("recebiveis_cliente_id_fkey", "recebiveis", "clientes", ["cliente_id"], ["id"])

    op.drop_constraint("recebiveis_loja_id_fkey", "recebiveis", type_="foreignkey")
    for tabela in ("lojas", "recebiveis", "lancamentos"):
        op.drop_constraint(f"{tabela}_pkey", tabela, type_="primary")
    op.create_primary_key("lojas_pkey", "lojas", ["cliente_id", "id"])
    op.create_primary_key("recebiveis_pkey", "recebiveis", ["cliente_id", "adquirente", "id"])
    op.create_primary_key("lancamentos_pkey", "lancamentos", ["cliente_id", "id"])
    # A loja do recebível é do mesmo cliente: um recebível não aponta para a loja de outro.
    op.create_foreign_key(
        "recebiveis_loja_fkey", "recebiveis", "lojas", ["cliente_id", "loja_id"], ["cliente_id", "id"]
    )


def downgrade() -> None:
    # Falha se dois clientes (ou duas adquirentes) já tiverem o mesmo id: a volta perderia dado.
    op.drop_constraint("recebiveis_loja_fkey", "recebiveis", type_="foreignkey")
    for tabela in ("lojas", "recebiveis", "lancamentos"):
        op.drop_constraint(f"{tabela}_pkey", tabela, type_="primary")
        op.create_primary_key(f"{tabela}_pkey", tabela, ["id"])
    op.create_foreign_key("recebiveis_loja_id_fkey", "recebiveis", "lojas", ["loja_id"], ["id"])
    op.drop_constraint("recebiveis_cliente_id_fkey", "recebiveis", type_="foreignkey")
    op.drop_column("recebiveis", "cliente_id")
