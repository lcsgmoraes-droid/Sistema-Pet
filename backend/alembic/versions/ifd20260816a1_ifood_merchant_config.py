"""add iFood merchant configuration

Revision ID: ifd20260816a1
Revises: zwp20260816a1
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls

revision = "ifd20260816a1"
down_revision = "zwp20260816a1"
branch_labels = None
depends_on = None


TABLE_NAME = "ifood_merchant_configs"


def upgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("merchant_id", sa.String(length=36), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "catalog_source",
            sa.String(length=20),
            nullable=False,
            server_default="ecommerce",
        ),
        sa.Column(
            "default_markup_percent",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("stock_safety", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="draft"
        ),
        sa.Column(
            "last_connection_check_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("last_catalog_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_ifood_merchant_configs_tenant"),
    )
    op.create_index("ix_ifood_merchant_configs_tenant_id", TABLE_NAME, ["tenant_id"])
    op.create_index(
        "ix_ifood_merchant_configs_status", TABLE_NAME, ["tenant_id", "status"]
    )
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=(TABLE_NAME,),
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=(TABLE_NAME,),
        enable=False,
    )
    op.drop_table(TABLE_NAME)
