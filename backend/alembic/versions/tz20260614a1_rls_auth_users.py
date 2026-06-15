"""enable custom RLS on auth users tables

Revision ID: tz20260614a1
Revises: ty20260614a1
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa

from app.tenant_rls_migration import (
    AUTH_EMAIL_SETTING_TEXT,
    AUTH_USER_ID_SETTING_INT,
    AUTH_USER_TENANTS_ACCESS_GUARD,
    AUTH_USERS_ACCESS_GUARD,
    AUTH_USERS_TENANT_MEMBERSHIP_GUARD,
    apply_auth_users_rls,
)


revision = "tz20260614a1"
down_revision = "ty20260614a1"
branch_labels = None
depends_on = None


AUTH_RLS_TABLES = ("users", "user_tenants")
AUTH_USER_ID_SETTING = AUTH_USER_ID_SETTING_INT
AUTH_EMAIL_SETTING = AUTH_EMAIL_SETTING_TEXT
USERS_ACCESS_GUARD = AUTH_USERS_ACCESS_GUARD
USERS_TENANT_MEMBERSHIP_GUARD = AUTH_USERS_TENANT_MEMBERSHIP_GUARD
USER_TENANTS_ACCESS_GUARD = AUTH_USER_TENANTS_ACCESS_GUARD


def upgrade() -> None:
    apply_auth_users_rls(
        op_module=op,
        sa_module=sa,
        table_names=AUTH_RLS_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_auth_users_rls(
        op_module=op,
        sa_module=sa,
        table_names=AUTH_RLS_TABLES,
        enable=False,
    )
