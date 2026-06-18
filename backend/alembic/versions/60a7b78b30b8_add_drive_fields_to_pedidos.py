"""add drive fields to pedidos

Revision ID: 60a7b78b30b8
Revises: j3k4l5m6n7o8
Create Date: 2026-03-09 00:02:18.673678

This revision originally contained an oversized autogenerate dump unrelated to
its purpose and attempted to recreate tables that already belong to earlier
migrations. Keep the revision ID for graph compatibility, but limit the upgrade
to the intended pedidos drive columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "60a7b78b30b8"
down_revision: Union[str, Sequence[str], None] = "j3k4l5m6n7o8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("pedidos"):
        return

    columns = {column["name"] for column in inspector.get_columns("pedidos")}
    if "is_drive" not in columns:
        op.add_column(
            "pedidos",
            sa.Column("is_drive", sa.Boolean(), nullable=False, server_default="false"),
        )
    if "drive_chegou_at" not in columns:
        op.add_column(
            "pedidos",
            sa.Column("drive_chegou_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "drive_entregue_at" not in columns:
        op.add_column(
            "pedidos",
            sa.Column("drive_entregue_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("pedidos"):
        return

    columns = {column["name"] for column in inspector.get_columns("pedidos")}
    for column_name in ("drive_entregue_at", "drive_chegou_at", "is_drive"):
        if column_name in columns:
            op.drop_column("pedidos", column_name)
