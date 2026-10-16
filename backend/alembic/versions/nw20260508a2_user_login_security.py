"""add user login security metadata

Revision ID: nw20260508a2
Revises: nv20260508a1
Create Date: 2026-05-08 14:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "nw20260508a2"
down_revision = "nv20260508a1"
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

    if "failed_login_attempts" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
    if "locked_until" not in columns:
        op.add_column(
            "users",
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        )
    if "last_login_at" not in columns:
        op.add_column(
            "users",
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "last_login_ip" not in columns:
        op.add_column(
            "users", sa.Column("last_login_ip", sa.String(length=50), nullable=True)
        )
    if "password_changed_at" not in columns:
        op.add_column(
            "users",
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        )

    op.execute(
        """
        UPDATE users
           SET failed_login_attempts = 0
        WHERE failed_login_attempts IS NULL
        """
    )

    if inspector.has_table("user_sessions"):
        session_columns = _column_names(inspector, "user_sessions")
        if "tenant_id" not in session_columns:
            op.add_column(
                "user_sessions", sa.Column("tenant_id", sa.UUID(), nullable=True)
            )
            op.execute(
                "CREATE INDEX IF NOT EXISTS ix_user_sessions_tenant_id "
                "ON user_sessions (tenant_id)"
            )
        if "updated_at" not in session_columns:
            op.add_column(
                "user_sessions",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return

    columns = _column_names(inspector, "users")
    for column_name in (
        "password_changed_at",
        "last_login_ip",
        "last_login_at",
        "locked_until",
        "failed_login_attempts",
    ):
        if column_name in columns:
            op.drop_column("users", column_name)

    if inspector.has_table("user_sessions"):
        session_columns = _column_names(inspector, "user_sessions")
        if "tenant_id" in session_columns:
            op.execute("DROP INDEX IF EXISTS ix_user_sessions_tenant_id")
            op.drop_column("user_sessions", "tenant_id")
        if "updated_at" in session_columns:
            op.drop_column("user_sessions", "updated_at")
