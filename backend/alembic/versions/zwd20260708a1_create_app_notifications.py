"""create app notifications

Revision ID: zwd20260708a1
Revises: zwc20260703a1
Create Date: 2026-07-08 22:14:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


# revision identifiers, used by Alembic.
revision: str = "zwd20260708a1"
down_revision: Union[str, None] = "zwc20260703a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APP_NOTIFICATIONS_RLS_TABLES = ("app_notifications",)

TENANT_GUARD = TENANT_RLS_GUARD


def upgrade() -> None:
    op.create_table(
        "app_notifications",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=300), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("push_ticket_id", sa.String(length=120), nullable=True),
        sa.Column("push_error", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            "idempotency_key",
            name="uq_app_notifications_tenant_user_idem",
        ),
    )
    op.create_index(
        "ix_app_notifications_tenant_id",
        "app_notifications",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_app_notifications_user_id",
        "app_notifications",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_app_notifications_customer_id",
        "app_notifications",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_app_notifications_source",
        "app_notifications",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_app_notifications_kind",
        "app_notifications",
        ["kind"],
        unique=False,
    )
    op.create_index(
        "ix_app_notifications_tenant_user_visible",
        "app_notifications",
        ["tenant_id", "user_id", "cleared_at", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_app_notifications_tenant_customer",
        "app_notifications",
        ["tenant_id", "customer_id", "created_at"],
        unique=False,
    )
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=APP_NOTIFICATIONS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=APP_NOTIFICATIONS_RLS_TABLES,
        enable=False,
    )
    op.drop_index(
        "ix_app_notifications_tenant_customer", table_name="app_notifications"
    )
    op.drop_index(
        "ix_app_notifications_tenant_user_visible", table_name="app_notifications"
    )
    op.drop_index("ix_app_notifications_kind", table_name="app_notifications")
    op.drop_index("ix_app_notifications_source", table_name="app_notifications")
    op.drop_index("ix_app_notifications_customer_id", table_name="app_notifications")
    op.drop_index("ix_app_notifications_user_id", table_name="app_notifications")
    op.drop_index("ix_app_notifications_tenant_id", table_name="app_notifications")
    op.drop_table("app_notifications")
