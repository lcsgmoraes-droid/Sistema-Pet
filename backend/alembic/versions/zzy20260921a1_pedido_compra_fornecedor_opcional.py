"""Permite pedido de compra generico sem fornecedor.

Revision ID: zzy20260921a1
Revises: zzx20260919a1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "zzy20260921a1"
down_revision: Union[str, Sequence[str], None] = "zzx20260919a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "pedidos_compra",
        "fornecedor_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    sem_fornecedor = bind.execute(
        sa.text("SELECT COUNT(*) FROM pedidos_compra WHERE fornecedor_id IS NULL")
    ).scalar()
    if sem_fornecedor:
        raise RuntimeError(
            "Nao e possivel reverter: existem pedidos de compra sem fornecedor."
        )
    op.alter_column(
        "pedidos_compra",
        "fornecedor_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
