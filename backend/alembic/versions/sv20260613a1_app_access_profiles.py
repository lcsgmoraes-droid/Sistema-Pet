"""create app access profiles

Revision ID: sv20260613a1
Revises: su20260613a1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "sv20260613a1"
down_revision = "su20260613a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_access_profiles",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("profile_type", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("granted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "cliente_id",
            "profile_type",
            name="uq_app_access_profiles_tenant_cliente_profile",
        ),
    )
    op.create_index(
        "ix_app_access_profiles_tenant_id",
        "app_access_profiles",
        ["tenant_id"],
    )
    op.create_index(
        "ix_app_access_profiles_user_id",
        "app_access_profiles",
        ["user_id"],
    )
    op.create_index(
        "ix_app_access_profiles_cliente_id",
        "app_access_profiles",
        ["cliente_id"],
    )
    op.create_index(
        "ix_app_access_profiles_profile_type",
        "app_access_profiles",
        ["profile_type"],
    )
    op.create_index(
        "ix_app_access_profiles_tenant_user_profile",
        "app_access_profiles",
        ["tenant_id", "user_id", "profile_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_app_access_profiles_tenant_user_profile", table_name="app_access_profiles"
    )
    op.drop_index(
        "ix_app_access_profiles_profile_type", table_name="app_access_profiles"
    )
    op.drop_index("ix_app_access_profiles_cliente_id", table_name="app_access_profiles")
    op.drop_index("ix_app_access_profiles_user_id", table_name="app_access_profiles")
    op.drop_index("ix_app_access_profiles_tenant_id", table_name="app_access_profiles")
    op.drop_table("app_access_profiles")
