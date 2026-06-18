"""add user email verification and lgpd consent metadata

Revision ID: nv20260508a1
Revises: nu20260507a1
Create Date: 2026-05-08 10:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "nv20260508a1"
down_revision = "nu20260507a1"
branch_labels = None
depends_on = None


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    columns = _column_names(inspector, "users")

    if "consent_version" not in columns:
        op.add_column(
            "users", sa.Column("consent_version", sa.String(length=50), nullable=True)
        )
    if "privacy_version" not in columns:
        op.add_column(
            "users", sa.Column("privacy_version", sa.String(length=50), nullable=True)
        )
    if "consent_ip" not in columns:
        op.add_column(
            "users", sa.Column("consent_ip", sa.String(length=50), nullable=True)
        )
    if "consent_user_agent" not in columns:
        op.add_column(
            "users", sa.Column("consent_user_agent", sa.Text(), nullable=True)
        )
    if "email_verified" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "email_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
    if "email_verified_at" not in columns:
        op.add_column(
            "users",
            sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "email_verification_token_hash" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "email_verification_token_hash", sa.String(length=128), nullable=True
            ),
        )
    if "email_verification_token_expires" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "email_verification_token_expires",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
    if "email_verification_sent_at" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "email_verification_sent_at", sa.DateTime(timezone=True), nullable=True
            ),
        )

    op.execute(
        """
        UPDATE users
           SET email_verified = true,
               email_verified_at = COALESCE(email_verified_at, created_at, now())
         WHERE COALESCE(email_verified, false) = false
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_users_email_verification_token_hash "
        "ON users (email_verification_token_hash)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    op.execute("DROP INDEX IF EXISTS ix_users_email_verification_token_hash")
    columns = _column_names(inspector, "users")
    for column_name in (
        "email_verification_sent_at",
        "email_verification_token_expires",
        "email_verification_token_hash",
        "email_verified_at",
        "email_verified",
        "consent_user_agent",
        "consent_ip",
        "privacy_version",
        "consent_version",
    ):
        if column_name in columns:
            op.drop_column("users", column_name)
