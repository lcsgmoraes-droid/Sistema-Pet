"""add Asaas billing foundation

Revision ID: zwi20260718a1
Revises: zwh20260717a1
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "zwi20260718a1"
down_revision = "zwh20260717a1"
branch_labels = None
depends_on = None


TENANT_COLUMNS = (
    ("billing_provider_environment", sa.String(length=20)),
    ("billing_provider_customer_id", sa.String(length=80)),
    ("billing_provider_subscription_id", sa.String(length=80)),
    ("billing_provider_payment_id", sa.String(length=80)),
    ("billing_payment_status", sa.String(length=40)),
    ("billing_type", sa.String(length=30)),
    ("billing_next_due_date", sa.Date()),
    ("billing_checkout_url", sa.String(length=500)),
)


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    tenant_columns = _columns("tenants")
    for column_name, column_type in TENANT_COLUMNS:
        if column_name not in tenant_columns:
            op.add_column(
                "tenants", sa.Column(column_name, column_type, nullable=True)
            )

    tenant_indexes = _indexes("tenants")
    for column_name in (
        "billing_provider_customer_id",
        "billing_provider_subscription_id",
        "billing_provider_payment_id",
    ):
        index_name = f"ix_tenants_{column_name}"
        if index_name not in tenant_indexes:
            op.create_index(index_name, "tenants", [column_name], unique=False)

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("billing_webhook_events"):
        op.create_table(
            "billing_webhook_events",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("provider", sa.String(length=30), nullable=False),
            sa.Column("event_id", sa.String(length=120), nullable=False),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("tenant_reference", sa.String(length=36), nullable=True),
            sa.Column("provider_payment_id", sa.String(length=80), nullable=True),
            sa.Column("payload_sha256", sa.String(length=64), nullable=False),
            sa.Column(
                "processing_status",
                sa.String(length=20),
                nullable=False,
                server_default="processing",
            ),
            sa.Column("error_message", sa.String(length=500), nullable=True),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "provider", "event_id", name="uq_billing_webhook_provider_event"
            ),
        )

    event_indexes = _indexes("billing_webhook_events")
    for column_name in ("tenant_reference", "provider_payment_id"):
        index_name = f"ix_billing_webhook_events_{column_name}"
        if index_name not in event_indexes:
            op.create_index(
                index_name,
                "billing_webhook_events",
                [column_name],
                unique=False,
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("billing_webhook_events"):
        op.drop_table("billing_webhook_events")

    tenant_columns = _columns("tenants")
    tenant_indexes = _indexes("tenants")
    for column_name, _column_type in reversed(TENANT_COLUMNS):
        index_name = f"ix_tenants_{column_name}"
        if index_name in tenant_indexes:
            op.drop_index(index_name, table_name="tenants")
        if column_name in tenant_columns:
            op.drop_column("tenants", column_name)
