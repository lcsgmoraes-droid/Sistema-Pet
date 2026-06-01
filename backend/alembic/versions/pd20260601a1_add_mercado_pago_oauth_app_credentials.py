"""add mercado pago oauth app credentials

Revision ID: pd20260601a1
Revises: pc20260601a1
Create Date: 2026-06-01 08:39:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "pd20260601a1"
down_revision: Union[str, None] = "pc20260601a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ecommerce_payment_gateway_configs",
        sa.Column("oauth_client_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "ecommerce_payment_gateway_configs",
        sa.Column("oauth_client_secret_encrypted", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ecommerce_payment_gateway_configs", "oauth_client_secret_encrypted")
    op.drop_column("ecommerce_payment_gateway_configs", "oauth_client_id")
