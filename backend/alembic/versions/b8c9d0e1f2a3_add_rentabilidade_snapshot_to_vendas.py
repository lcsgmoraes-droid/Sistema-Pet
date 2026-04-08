"""add rentabilidade snapshot to vendas

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-04-07 18:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "r3s4t5u6v7w8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vendas", sa.Column("rentabilidade_snapshot", sa.JSON(), nullable=True))
    op.add_column("vendas", sa.Column("rentabilidade_snapshot_em", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("vendas", "rentabilidade_snapshot_em")
    op.drop_column("vendas", "rentabilidade_snapshot")
