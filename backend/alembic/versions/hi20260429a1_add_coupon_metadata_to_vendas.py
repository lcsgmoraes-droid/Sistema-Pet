"""add coupon metadata to vendas

Revision ID: hi20260429a1
Revises: gh20260428a1
Create Date: 2026-04-29 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "hi20260429a1"
down_revision: Union[str, Sequence[str], None] = "gh20260428a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vendas", sa.Column("cupom_code", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "vendas", sa.Column("cupom_discount_applied", sa.Numeric(10, 2), nullable=True)
    )
    op.create_index("ix_vendas_cupom_code", "vendas", ["cupom_code"])


def downgrade() -> None:
    op.drop_index("ix_vendas_cupom_code", table_name="vendas")
    op.drop_column("vendas", "cupom_discount_applied")
    op.drop_column("vendas", "cupom_code")
