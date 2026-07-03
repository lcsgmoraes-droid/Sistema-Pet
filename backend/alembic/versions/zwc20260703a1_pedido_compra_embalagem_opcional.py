"""pedido compra embalagem opcional

Revision ID: zwc20260703a1
Revises: zwb20260702a1
Create Date: 2026-07-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "zwc20260703a1"
down_revision: Union[str, Sequence[str], None] = "zwb20260702a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "pedidos_compra_itens",
        "quantidade_por_embalagem",
        existing_type=sa.Float(),
        nullable=True,
        server_default=None,
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE pedidos_compra_itens
        SET quantidade_por_embalagem = 1
        WHERE quantidade_por_embalagem IS NULL
        """
    )
    op.alter_column(
        "pedidos_compra_itens",
        "quantidade_por_embalagem",
        existing_type=sa.Float(),
        nullable=False,
        server_default="1",
    )
