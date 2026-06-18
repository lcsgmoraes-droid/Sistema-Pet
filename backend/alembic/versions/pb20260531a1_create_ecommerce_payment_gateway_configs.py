"""create ecommerce payment gateway configs

Revision ID: pb20260531a1
Revises: 0f8a8df9259d
Create Date: 2026-05-31 17:42:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "pb20260531a1"
down_revision: Union[str, Sequence[str], None] = "0f8a8df9259d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ecommerce_payment_gateway_configs",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="mercadopago"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("environment", sa.String(length=20), nullable=False, server_default="production"),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("webhook_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("webhook_token", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            name="uq_ecommerce_payment_gateway_tenant_provider",
        ),
        sa.UniqueConstraint("webhook_token"),
    )
    op.create_index(
        "ix_ecommerce_payment_gateway_configs_tenant_id",
        "ecommerce_payment_gateway_configs",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_ecommerce_payment_gateway_configs_webhook_token",
        "ecommerce_payment_gateway_configs",
        ["webhook_token"],
        unique=False,
    )
    op.create_index(
        "ix_ecommerce_payment_gateway_tenant_enabled",
        "ecommerce_payment_gateway_configs",
        ["tenant_id", "enabled"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ecommerce_payment_gateway_tenant_enabled",
        table_name="ecommerce_payment_gateway_configs",
    )
    op.drop_index(
        "ix_ecommerce_payment_gateway_configs_webhook_token",
        table_name="ecommerce_payment_gateway_configs",
    )
    op.drop_index(
        "ix_ecommerce_payment_gateway_configs_tenant_id",
        table_name="ecommerce_payment_gateway_configs",
    )
    op.drop_table("ecommerce_payment_gateway_configs")
