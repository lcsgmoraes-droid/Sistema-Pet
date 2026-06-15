from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import (
    capture_migration_sql,
    load_migration,
    migration_path,
    statements_containing,
)


MIGRATION_FILE = migration_path("tz20260614a1_rls_auth_users.py")
AUTH_RLS_TABLES = ("users", "user_tenants")


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        AUTH_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_auth_users_rls_migration_metadata_and_scope():
    assert MIGRATION_FILE.exists()

    migration = load_migration(MIGRATION_FILE)

    assert migration["revision"] == "tz20260614a1"
    assert migration["down_revision"] == "ty20260614a1"
    assert migration["AUTH_RLS_TABLES"] == AUTH_RLS_TABLES


def test_auth_users_rls_upgrade_allows_pre_tenant_auth_and_tenant_membership(monkeypatch):
    emitted = _capture(monkeypatch, "upgrade")

    assert len(statements_containing(emitted, "ENABLE ROW LEVEL SECURITY")) == 2
    assert len(statements_containing(emitted, "FORCE ROW LEVEL SECURITY")) == 2

    users_select = statements_containing(emitted, "CREATE POLICY users_auth_select ON users")
    assert len(users_select) == 1
    assert "current_setting('app.tenant_id', true)" in users_select[0]
    assert "current_setting('app.auth_user_id', true)" in users_select[0]
    assert "current_setting('app.auth_email', true)" in users_select[0]
    assert "EXISTS (SELECT 1 FROM user_tenants aut" in users_select[0]

    user_tenants_select = statements_containing(
        emitted,
        "CREATE POLICY user_tenants_auth_select ON user_tenants",
    )
    assert len(user_tenants_select) == 1
    assert "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid" in user_tenants_select[0]
    assert "user_id = NULLIF(current_setting('app.auth_user_id', true), '')::integer" in user_tenants_select[0]


def test_auth_users_rls_writes_stay_tenant_scoped_except_user_self_updates(monkeypatch):
    emitted = _capture(monkeypatch, "upgrade")

    users_insert = statements_containing(emitted, "CREATE POLICY users_auth_insert ON users")
    assert len(users_insert) == 1
    assert "FOR INSERT WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)" in users_insert[0]

    users_update = statements_containing(emitted, "CREATE POLICY users_auth_update ON users")
    assert len(users_update) == 1
    assert "FOR UPDATE USING" in users_update[0]
    assert "current_setting('app.auth_email', true)" in users_update[0]

    user_tenants_writes = [
        sql
        for sql in emitted
        if sql.startswith("CREATE POLICY user_tenants_auth_")
        and any(fragment in sql for fragment in ("FOR INSERT", "FOR UPDATE", "FOR DELETE"))
    ]
    assert len(user_tenants_writes) == 3
    assert all("current_setting('app.auth_email', true)" not in sql for sql in user_tenants_writes)
    assert all("tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid" in sql for sql in user_tenants_writes)


def test_auth_users_rls_downgrade_removes_custom_policies(monkeypatch):
    emitted = _capture(monkeypatch, "downgrade")

    assert emitted[0].startswith("DROP POLICY IF EXISTS user_tenants_auth_delete")
    assert emitted[-1] == "ALTER TABLE users DISABLE ROW LEVEL SECURITY"


def test_auth_users_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []


def test_auth_tables_are_tracked_by_tenant_safe_sql_guardrail():
    assert set(AUTH_RLS_TABLES).issubset(TENANT_SCOPED_TABLES)
