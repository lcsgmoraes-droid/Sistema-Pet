"""pedido compra unidade compra

Revision ID: zwb20260702a1
Revises: zwa20260630a1
Create Date: 2026-07-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "zwb20260702a1"
down_revision: Union[str, Sequence[str], None] = "zwa20260630a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pedidos_compra_itens",
        sa.Column(
            "unidade_compra",
            sa.String(length=10),
            nullable=False,
            server_default="UN",
        ),
    )
    op.add_column(
        "pedidos_compra_itens",
        sa.Column(
            "quantidade_por_embalagem",
            sa.Float(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "pedidos_compra_itens",
        sa.Column(
            "quantidade_total_unidades",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )
    op.execute(
        """
        UPDATE pedidos_compra_itens
        SET quantidade_total_unidades = quantidade_pedida
        WHERE quantidade_total_unidades = 0
        """
    )


def downgrade() -> None:
    op.drop_column("pedidos_compra_itens", "quantidade_total_unidades")
    op.drop_column("pedidos_compra_itens", "quantidade_por_embalagem")
    op.drop_column("pedidos_compra_itens", "unidade_compra")
