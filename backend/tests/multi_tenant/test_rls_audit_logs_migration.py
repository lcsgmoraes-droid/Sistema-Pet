from tests.multi_tenant.rls_migration_helpers import (
    capture_migration_sql,
    load_migration,
    migration_path,
)


MIGRATION_FILE = migration_path("tv20260614a1_rls_audit_logs.py")
TABLE_NAME = "audit_logs"
TENANT_SETTING_UUID = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
TENANT_CONTEXT_IS_EMPTY = "NULLIF(current_setting('app.tenant_id', true), '') IS NULL"
TENANT_ROW_GUARD = f"tenant_id = {TENANT_SETTING_UUID}"
GLOBAL_ROW_GUARD = f"tenant_id IS NULL AND {TENANT_CONTEXT_IS_EMPTY}"
AUDIT_LOG_SCOPE_GUARD = f"({TENANT_ROW_GUARD}) OR ({GLOBAL_ROW_GUARD})"
POLICY_NAME = "audit_logs_tenant_or_global_isolation"


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        (TABLE_NAME,),
        dialect=dialect,
        existing=existing,
    )


def test_audit_logs_rls_migration_metadata_and_custom_scope():
    assert MIGRATION_FILE.exists()

    migration = load_migration(MIGRATION_FILE)

    assert migration["revision"] == "tv20260614a1"
    assert migration["down_revision"] == "tu20260614a1"
    assert migration["AUDIT_LOGS_RLS_TABLE"] == TABLE_NAME
    assert migration["TENANT_SETTING_UUID"] == TENANT_SETTING_UUID
    assert migration["TENANT_CONTEXT_IS_EMPTY"] == TENANT_CONTEXT_IS_EMPTY
    assert migration["TENANT_ROW_GUARD"] == TENANT_ROW_GUARD
    assert migration["GLOBAL_ROW_GUARD"] == GLOBAL_ROW_GUARD
    assert migration["AUDIT_LOG_SCOPE_GUARD"] == AUDIT_LOG_SCOPE_GUARD
    assert migration["POLICY_NAME"] == POLICY_NAME


def test_audit_logs_rls_upgrade_preserves_tenant_rows_and_global_null_rows(monkeypatch):
    emitted = _capture(monkeypatch, "upgrade")

    assert emitted == [
        "ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY",
        "DROP POLICY IF EXISTS audit_logs_tenant_isolation ON audit_logs",
        "DROP POLICY IF EXISTS audit_logs_tenant_or_global_isolation ON audit_logs",
        (
            "CREATE POLICY audit_logs_tenant_or_global_isolation ON audit_logs "
            f"USING ({AUDIT_LOG_SCOPE_GUARD}) WITH CHECK ({AUDIT_LOG_SCOPE_GUARD})"
        ),
    ]


def test_audit_logs_rls_upgrade_skips_missing_table(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_audit_logs_rls_downgrade_removes_custom_policy(monkeypatch):
    emitted = _capture(monkeypatch, "downgrade")

    assert emitted == [
        "DROP POLICY IF EXISTS audit_logs_tenant_or_global_isolation ON audit_logs",
        "ALTER TABLE audit_logs NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY",
    ]


def test_audit_logs_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
