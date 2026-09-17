"""add globally unique phone login for users

Revision ID: zzu20260917a1
Revises: zzt20260916a1
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import AUTH_USERS_ACCESS_GUARD


revision = "zzu20260917a1"
down_revision = "zzt20260916a1"
branch_labels = None
depends_on = None


TABLE_NAME = "users"
LOGIN_PHONE_UNIQUE = "uq_users_login_phone"
LOGIN_CHECK = "ck_users_login_identifier"
AUTH_PHONE_SETTING = "NULLIF(current_setting('app.auth_phone', true), '')"
AUTH_PHONE_GUARD = f"login_phone = {AUTH_PHONE_SETTING}"


def _replace_users_auth_policies(access_guard: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP POLICY IF EXISTS users_auth_select ON users")
    op.execute("DROP POLICY IF EXISTS users_auth_update ON users")
    op.execute(
        f"CREATE POLICY users_auth_select ON users FOR SELECT USING ({access_guard})"
    )
    op.execute(
        "CREATE POLICY users_auth_update ON users "
        f"FOR UPDATE USING ({access_guard}) WITH CHECK ({access_guard})"
    )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(TABLE_NAME):
        return

    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if "login_phone" not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column("login_phone", sa.String(length=16), nullable=True),
        )

    unique_names = {
        constraint.get("name")
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(TABLE_NAME)
    }
    if LOGIN_PHONE_UNIQUE not in unique_names:
        op.create_unique_constraint(
            LOGIN_PHONE_UNIQUE,
            TABLE_NAME,
            ["login_phone"],
        )

    check_names = {
        constraint.get("name")
        for constraint in sa.inspect(op.get_bind()).get_check_constraints(TABLE_NAME)
    }
    if LOGIN_CHECK in check_names:
        op.drop_constraint(LOGIN_CHECK, TABLE_NAME, type_="check")
    op.create_check_constraint(
        LOGIN_CHECK,
        TABLE_NAME,
        "email IS NOT NULL OR username IS NOT NULL OR login_phone IS NOT NULL",
    )

    access_guard = f"({AUTH_USERS_ACCESS_GUARD}) OR ({AUTH_PHONE_GUARD})"
    _replace_users_auth_policies(access_guard)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(TABLE_NAME):
        return

    _replace_users_auth_policies(AUTH_USERS_ACCESS_GUARD)

    op.execute(
        """
        UPDATE users
           SET username = 'tel-' || login_phone
         WHERE email IS NULL
           AND username IS NULL
           AND login_phone IS NOT NULL
        """
    )

    check_names = {
        constraint.get("name")
        for constraint in sa.inspect(op.get_bind()).get_check_constraints(TABLE_NAME)
    }
    if LOGIN_CHECK in check_names:
        op.drop_constraint(LOGIN_CHECK, TABLE_NAME, type_="check")
    op.create_check_constraint(
        LOGIN_CHECK,
        TABLE_NAME,
        "email IS NOT NULL OR username IS NOT NULL",
    )

    unique_names = {
        constraint.get("name")
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(TABLE_NAME)
    }
    if LOGIN_PHONE_UNIQUE in unique_names:
        op.drop_constraint(LOGIN_PHONE_UNIQUE, TABLE_NAME, type_="unique")

    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns(TABLE_NAME)}
    if "login_phone" in columns:
        op.drop_column(TABLE_NAME, "login_phone")
