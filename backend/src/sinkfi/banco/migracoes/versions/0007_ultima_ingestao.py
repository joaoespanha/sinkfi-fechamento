"""A hora da última ingestão de cada cliente (ADR 0011).

É o "dados atualizados em" da tela. A hora da rodada não serve: a ingestão sem dado
novo devolve a rodada que já existe (ADR 0006), e a hora dela ficaria parada.

Revision ID: 0007
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clientes", sa.Column("ultima_ingestao_em", sa.DateTime(timezone=True)))
    # O cliente que já teve ingestão começa com a hora do pedido mais recente no outbox, que nasce na mesma transação.
    op.execute(
        "UPDATE clientes c SET ultima_ingestao_em = p.criado_em"
        " FROM (SELECT cliente_id, max(criado_em) AS criado_em FROM pedidos_fechamento GROUP BY cliente_id) p"
        " WHERE p.cliente_id = c.id"
    )


def downgrade() -> None:
    op.drop_column("clientes", "ultima_ingestao_em")
