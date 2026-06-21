"""create user push devices

Revision ID: ua20260621a1
Revises: tz20260614a1
Create Date: 2026-06-21 00:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "ua20260621a1"
down_revision: Union[str, None] = "tz20260614a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_push_devices",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expo_push_token", sa.String(length=500), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=True),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("device_brand", sa.String(length=100), nullable=True),
        sa.Column("device_model", sa.String(length=150), nullable=True),
        sa.Column("os_name", sa.String(length=100), nullable=True),
        sa.Column("os_version", sa.String(length=100), nullable=True),
        sa.Column("app_version", sa.String(length=50), nullable=True),
        sa.Column(
            "enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ticket_id", sa.String(length=120), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
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
            "expo_push_token",
            name="uq_user_push_devices_tenant_user_token",
        ),
    )
    op.create_index(
        "ix_user_push_devices_tenant_id",
        "user_push_devices",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_push_devices_user_id",
        "user_push_devices",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_push_devices_expo_push_token",
        "user_push_devices",
        ["expo_push_token"],
        unique=False,
    )
    op.create_index(
        "ix_user_push_devices_tenant_user_enabled",
        "user_push_devices",
        ["tenant_id", "user_id", "enabled"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_push_devices_tenant_user_enabled", table_name="user_push_devices")
    op.drop_index("ix_user_push_devices_expo_push_token", table_name="user_push_devices")
    op.drop_index("ix_user_push_devices_user_id", table_name="user_push_devices")
    op.drop_index("ix_user_push_devices_tenant_id", table_name="user_push_devices")
    op.drop_table("user_push_devices")
