"""add drive fields to pedidos

Revision ID: k4l5m6n7o8p9
Revises: j3k4l5m6n7o8
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "k4l5m6n7o8p9"
down_revision = "j3k4l5m6n7o8"
branch_labels = None
depends_on = None


def upgrade():
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


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("pedidos"):
        return

    columns = {column["name"] for column in inspector.get_columns("pedidos")}
    for column_name in ("drive_entregue_at", "drive_chegou_at", "is_drive"):
        if column_name in columns:
            op.drop_column("pedidos", column_name)
