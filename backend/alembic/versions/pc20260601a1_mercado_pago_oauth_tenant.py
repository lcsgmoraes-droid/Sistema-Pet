"""add mercado pago oauth tenant fields

Revision ID: pc20260601a1
Revises: pb20260531a1
Create Date: 2026-06-01 07:58:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "pc20260601a1"
down_revision: Union[str, Sequence[str], None] = "pb20260531a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ecommerce_payment_gateway_configs",
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "ecommerce_payment_gateway_configs",
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ecommerce_payment_gateway_configs",
        sa.Column("oauth_connected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "ecommerce_payment_gateway_configs",
        sa.Column("oauth_connected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ecommerce_payment_gateway_configs",
        sa.Column("mercado_pago_user_id", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "ecommerce_payment_gateway_configs",
        sa.Column("oauth_scope", sa.Text(), nullable=True),
    )
    op.add_column(
        "ecommerce_payment_gateway_configs",
        sa.Column("oauth_last_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "ecommerce_payment_gateway_configs",
        sa.Column("oauth_refresh_failed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ecommerce_payment_gateway_configs", "oauth_refresh_failed_at")
    op.drop_column("ecommerce_payment_gateway_configs", "oauth_last_error")
    op.drop_column("ecommerce_payment_gateway_configs", "oauth_scope")
    op.drop_column("ecommerce_payment_gateway_configs", "mercado_pago_user_id")
    op.drop_column("ecommerce_payment_gateway_configs", "oauth_connected_at")
    op.drop_column("ecommerce_payment_gateway_configs", "oauth_connected")
    op.drop_column("ecommerce_payment_gateway_configs", "access_token_expires_at")
    op.drop_column("ecommerce_payment_gateway_configs", "refresh_token_encrypted")
