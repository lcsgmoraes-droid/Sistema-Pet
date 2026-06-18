"""add payment link fields to pedidos

Revision ID: pe20260601a1
Revises: pd20260601a1
Create Date: 2026-06-01 13:42:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "pe20260601a1"
down_revision: Union[str, None] = "pd20260601a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pedidos", sa.Column("payment_provider", sa.String(length=50), nullable=True))
    op.add_column("pedidos", sa.Column("payment_preference_id", sa.String(length=255), nullable=True))
    op.add_column("pedidos", sa.Column("payment_url", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("pedidos", "payment_url")
    op.drop_column("pedidos", "payment_preference_id")
    op.drop_column("pedidos", "payment_provider")
