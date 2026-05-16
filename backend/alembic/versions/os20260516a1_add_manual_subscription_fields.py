"""add manual subscription fields to tenants

Revision ID: os20260516a1
Revises: or20260515a9
Create Date: 2026-05-16 09:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "os20260516a1"
down_revision = "or20260515a9"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _columns("tenants")

    if "billing_status" not in columns:
        op.add_column(
            "tenants",
            sa.Column("billing_status", sa.String(length=20), nullable=False, server_default="active"),
        )

    if "trial_started_at" not in columns:
        op.add_column("tenants", sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True))

    if "trial_ends_at" not in columns:
        op.add_column("tenants", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True))

    if "subscription_activated_at" not in columns:
        op.add_column(
            "tenants",
            sa.Column("subscription_activated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "subscription_source" not in columns:
        op.add_column(
            "tenants",
            sa.Column("subscription_source", sa.String(length=50), nullable=False, server_default="manual"),
        )


def downgrade() -> None:
    columns = _columns("tenants")
    for column_name in [
        "subscription_source",
        "subscription_activated_at",
        "trial_ends_at",
        "trial_started_at",
        "billing_status",
    ]:
        if column_name in columns:
            op.drop_column("tenants", column_name)
