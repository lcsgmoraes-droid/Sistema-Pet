"""add vet calendar token to users

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-04-20 18:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "h9i0j1k2l3m4"
down_revision = "g8h9i0j1k2l3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    indexes = {index["name"] for index in inspector.get_indexes("users")}

    if "vet_calendar_token" not in columns:
        op.add_column(
            "users",
            sa.Column("vet_calendar_token", sa.String(length=255), nullable=True),
        )
    if "ix_users_vet_calendar_token" not in indexes:
        op.create_index(
            "ix_users_vet_calendar_token", "users", ["vet_calendar_token"], unique=True
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    indexes = {index["name"] for index in inspector.get_indexes("users")}

    if "ix_users_vet_calendar_token" in indexes:
        op.drop_index("ix_users_vet_calendar_token", table_name="users")
    if "vet_calendar_token" in columns:
        op.drop_column("users", "vet_calendar_token")
