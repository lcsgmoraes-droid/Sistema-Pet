"""create usuario menu favoritos

Revision ID: uv20260630a1
Revises: zz20260624a1
Create Date: 2026-06-30 13:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision: str = "uv20260630a1"
down_revision: Union[str, Sequence[str], None] = "zz20260624a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USUARIO_MENU_FAVORITOS_RLS_TABLES = ("usuario_menu_favoritos",)


def upgrade() -> None:
    op.create_table(
        "usuario_menu_favoritos",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("icon_key", sa.String(length=80), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            "path",
            name="uq_usuario_menu_favoritos_tenant_user_path",
        ),
    )
    op.create_index(
        "ix_usuario_menu_favoritos_tenant_id",
        "usuario_menu_favoritos",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_usuario_menu_favoritos_user_id",
        "usuario_menu_favoritos",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_usuario_menu_favoritos_tenant_user_position",
        "usuario_menu_favoritos",
        ["tenant_id", "user_id", "position"],
        unique=False,
    )
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=USUARIO_MENU_FAVORITOS_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=USUARIO_MENU_FAVORITOS_RLS_TABLES,
        enable=False,
    )
    op.drop_index("ix_usuario_menu_favoritos_tenant_user_position", table_name="usuario_menu_favoritos")
    op.drop_index("ix_usuario_menu_favoritos_user_id", table_name="usuario_menu_favoritos")
    op.drop_index("ix_usuario_menu_favoritos_tenant_id", table_name="usuario_menu_favoritos")
    op.drop_table("usuario_menu_favoritos")
