"""ensure LGPD consent audit columns

Revision ID: nz20260508a5
Revises: ny20260508a4
Create Date: 2026-05-08 18:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "nz20260508a5"
down_revision = "ny20260508a4"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _columns("data_privacy_consents")
    if not columns:
        return

    if "updated_at" not in columns:
        op.add_column(
            "data_privacy_consents",
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
    if "revoked_at" not in columns:
        op.add_column(
            "data_privacy_consents",
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
        )
    if "revoke_reason" not in columns:
        op.add_column(
            "data_privacy_consents",
            sa.Column("revoke_reason", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    columns = _columns("data_privacy_consents")
    if "revoke_reason" in columns:
        op.drop_column("data_privacy_consents", "revoke_reason")
    if "revoked_at" in columns:
        op.drop_column("data_privacy_consents", "revoked_at")
    if "updated_at" in columns:
        op.drop_column("data_privacy_consents", "updated_at")
