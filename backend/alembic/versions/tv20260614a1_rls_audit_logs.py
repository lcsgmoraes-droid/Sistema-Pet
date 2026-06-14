"""enable custom RLS on audit logs

Revision ID: tv20260614a1
Revises: tu20260614a1
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "tv20260614a1"
down_revision = "tu20260614a1"
branch_labels = None
depends_on = None


AUDIT_LOGS_RLS_TABLE = "audit_logs"
TENANT_SETTING_UUID = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
TENANT_CONTEXT_IS_EMPTY = "NULLIF(current_setting('app.tenant_id', true), '') IS NULL"
TENANT_ROW_GUARD = f"tenant_id = {TENANT_SETTING_UUID}"
GLOBAL_ROW_GUARD = f"tenant_id IS NULL AND {TENANT_CONTEXT_IS_EMPTY}"
AUDIT_LOG_SCOPE_GUARD = f"({TENANT_ROW_GUARD}) OR ({GLOBAL_ROW_GUARD})"
POLICY_NAME = "audit_logs_tenant_or_global_isolation"


def _postgres_table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    if not _postgres_table_exists(AUDIT_LOGS_RLS_TABLE):
        return

    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation ON audit_logs")
    op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON audit_logs")
    op.execute(
        f"CREATE POLICY {POLICY_NAME} ON audit_logs "
        f"USING ({AUDIT_LOG_SCOPE_GUARD}) WITH CHECK ({AUDIT_LOG_SCOPE_GUARD})"
    )


def downgrade() -> None:
    if not _postgres_table_exists(AUDIT_LOGS_RLS_TABLE):
        return

    op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON audit_logs")
    op.execute("ALTER TABLE audit_logs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY")
