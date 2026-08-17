"""add iFood orders and events

Revision ID: ifr20260816a1
Revises: ifd20260816a1
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "ifr20260816a1"
down_revision = "ifd20260816a1"
branch_labels = None
depends_on = None


TABLE_NAMES = ("ifood_orders", "ifood_events")


def _tenant_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    op.add_column(
        "ifood_merchant_configs",
        sa.Column("last_orders_poll_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ifood_merchant_configs",
        sa.Column("last_orders_error", sa.Text(), nullable=True),
    )

    op.create_table(
        "ifood_orders",
        *_tenant_columns(),
        sa.Column("merchant_id", sa.String(length=36), nullable=False),
        sa.Column("ifood_order_id", sa.String(length=64), nullable=False),
        sa.Column("display_id", sa.String(length=64), nullable=True),
        sa.Column(
            "status", sa.String(length=64), nullable=False, server_default="PLACED"
        ),
        sa.Column("order_type", sa.String(length=32), nullable=True),
        sa.Column("order_timing", sa.String(length=32), nullable=True),
        sa.Column("delivered_by", sa.String(length=32), nullable=True),
        sa.Column("total", sa.Float(), nullable=True),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preparation_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_action", sa.String(length=64), nullable=True),
        sa.Column("last_action_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "ifood_order_id", name="uq_ifood_orders_tenant_order"
        ),
    )
    op.create_index("ix_ifood_orders_tenant_id", "ifood_orders", ["tenant_id"])
    op.create_index(
        "ix_ifood_orders_tenant_status", "ifood_orders", ["tenant_id", "status"]
    )
    op.create_index(
        "ix_ifood_orders_merchant_id",
        "ifood_orders",
        ["tenant_id", "merchant_id"],
    )

    op.create_table(
        "ifood_events",
        *_tenant_columns(),
        sa.Column("merchant_id", sa.String(length=36), nullable=False),
        sa.Column("ifood_event_id", sa.String(length=64), nullable=False),
        sa.Column("ifood_order_id", sa.String(length=64), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("full_code", sa.String(length=128), nullable=True),
        sa.Column("provider_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "ifood_event_id", name="uq_ifood_events_tenant_event"
        ),
    )
    op.create_index("ix_ifood_events_tenant_id", "ifood_events", ["tenant_id"])
    op.create_index(
        "ix_ifood_events_tenant_order",
        "ifood_events",
        ["tenant_id", "ifood_order_id"],
    )
    op.create_index(
        "ix_ifood_events_processing",
        "ifood_events",
        ["tenant_id", "processed_at"],
    )
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=TABLE_NAMES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=TABLE_NAMES,
        enable=False,
    )
    op.drop_table("ifood_events")
    op.drop_table("ifood_orders")
    op.drop_column("ifood_merchant_configs", "last_orders_error")
    op.drop_column("ifood_merchant_configs", "last_orders_poll_at")
