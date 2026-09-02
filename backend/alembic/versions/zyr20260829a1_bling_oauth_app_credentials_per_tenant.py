"""store Bling OAuth app credentials per tenant

Revision ID: zyr20260829a1
Revises: zxq20260829a1
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa


revision = "zyr20260829a1"
down_revision = "zxq20260829a1"
branch_labels = None
depends_on = None


CONNECTIONS = "bling_connections"


def _column_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(CONNECTIONS)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(CONNECTIONS):
        return

    columns = _column_names()
    if "oauth_client_id" not in columns:
        op.add_column(
            CONNECTIONS,
            sa.Column("oauth_client_id", sa.String(length=255), nullable=True),
        )
    if "oauth_client_secret_encrypted" not in columns:
        op.add_column(
            CONNECTIONS,
            sa.Column("oauth_client_secret_encrypted", sa.Text(), nullable=True),
        )

    op.alter_column(
        CONNECTIONS,
        "access_token_encrypted",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.alter_column(
        CONNECTIONS,
        "refresh_token_encrypted",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(CONNECTIONS):
        return

    op.execute(
        sa.text(
            f"DELETE FROM {CONNECTIONS} "
            "WHERE access_token_encrypted IS NULL OR refresh_token_encrypted IS NULL"
        )
    )
    op.alter_column(
        CONNECTIONS,
        "refresh_token_encrypted",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.alter_column(
        CONNECTIONS,
        "access_token_encrypted",
        existing_type=sa.Text(),
        nullable=False,
    )

    columns = _column_names()
    if "oauth_client_secret_encrypted" in columns:
        op.drop_column(CONNECTIONS, "oauth_client_secret_encrypted")
    if "oauth_client_id" in columns:
        op.drop_column(CONNECTIONS, "oauth_client_id")
