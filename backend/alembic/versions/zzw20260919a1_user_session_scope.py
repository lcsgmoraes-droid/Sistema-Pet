"""Distingue sessoes do ERP das sessoes do app e ecommerce.

Revision ID: zzw20260919a1
Revises: zzv20260917a1
Create Date: 2026-09-19
"""

import sqlalchemy as sa
from alembic import op


revision = "zzw20260919a1"
down_revision = "zzv20260917a1"
branch_labels = None
depends_on = None


TABLE_NAME = "user_sessions"
COLUMN_NAME = "session_scope"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(TABLE_NAME):
        return

    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if COLUMN_NAME not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column(
                COLUMN_NAME,
                sa.String(length=32),
                nullable=False,
                server_default="erp",
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(TABLE_NAME):
        return

    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if COLUMN_NAME in columns:
        op.drop_column(TABLE_NAME, COLUMN_NAME)
