"""add tenant username login and optional user email

Revision ID: zxl20260828a1
Revises: zxk20260828a1
Create Date: 2026-08-28
"""

from alembic import op
import sqlalchemy as sa


revision = "zxl20260828a1"
down_revision = "zxk20260828a1"
branch_labels = None
depends_on = None


TABLE_NAME = "users"
USERNAME_UNIQUE = "uq_users_tenant_username"
LOGIN_CHECK = "ck_users_login_identifier"


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    inspector = _inspector()
    if not inspector.has_table(TABLE_NAME):
        return

    columns = {column["name"]: column for column in inspector.get_columns(TABLE_NAME)}
    if "username" not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column("username", sa.String(length=50), nullable=True),
        )

    if not columns.get("email", {}).get("nullable", True):
        op.alter_column(
            TABLE_NAME,
            "email",
            existing_type=sa.String(length=255),
            nullable=True,
        )

    inspector = _inspector()
    unique_names = {
        constraint.get("name")
        for constraint in inspector.get_unique_constraints(TABLE_NAME)
    }
    if USERNAME_UNIQUE not in unique_names:
        op.create_unique_constraint(
            USERNAME_UNIQUE,
            TABLE_NAME,
            ["tenant_id", "username"],
        )

    check_names = {
        constraint.get("name")
        for constraint in inspector.get_check_constraints(TABLE_NAME)
    }
    if LOGIN_CHECK not in check_names:
        op.create_check_constraint(
            LOGIN_CHECK,
            TABLE_NAME,
            "email IS NOT NULL OR username IS NOT NULL",
        )


def downgrade() -> None:
    inspector = _inspector()
    if not inspector.has_table(TABLE_NAME):
        return

    check_names = {
        constraint.get("name")
        for constraint in inspector.get_check_constraints(TABLE_NAME)
    }
    if LOGIN_CHECK in check_names:
        op.drop_constraint(LOGIN_CHECK, TABLE_NAME, type_="check")

    unique_names = {
        constraint.get("name")
        for constraint in inspector.get_unique_constraints(TABLE_NAME)
    }
    if USERNAME_UNIQUE in unique_names:
        op.drop_constraint(USERNAME_UNIQUE, TABLE_NAME, type_="unique")

    columns = {column["name"]: column for column in inspector.get_columns(TABLE_NAME)}
    if "email" in columns:
        op.execute(
            sa.text(
                """
                UPDATE users
                   SET email = 'conta-' || id || '@username-only.corepet.invalid'
                 WHERE email IS NULL
                """
            )
        )
        op.alter_column(
            TABLE_NAME,
            "email",
            existing_type=sa.String(length=255),
            nullable=False,
        )
    if "username" in columns:
        op.drop_column(TABLE_NAME, "username")
