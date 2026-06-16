from pathlib import Path
import importlib.util


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "pr20260611a1_rls_template_canary.py"
)

CANARY_TABLES = (
    "tenant_template_installs",
    "tenant_template_item_installs",
)


def test_rls_template_canary_migration_exists_and_chains_from_current_head():
    assert MIGRATION_PATH.exists()

    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "pr20260611a1"' in source
    assert 'down_revision = "pq20260611a1"' in source
    assert 'bind.dialect.name == "postgresql"' in source


def _load_migration():
    spec = importlib.util.spec_from_file_location("rls_template_canary", MIGRATION_PATH)
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)
    return migration


def test_rls_template_canary_enables_force_and_policy_for_each_table(monkeypatch):
    migration = _load_migration()
    executed = []

    monkeypatch.setattr(migration, "_is_postgresql", lambda: True)
    monkeypatch.setattr(migration, "_table_exists", lambda table_name: True)
    monkeypatch.setattr(migration.op, "execute", lambda sql: executed.append(str(sql)))

    migration.upgrade()

    source = "\n".join(executed)

    for table in CANARY_TABLES:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in source
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in source
        assert f"CREATE POLICY {table}_tenant_isolation" in source
        assert f"ON {table}" in source

    assert "current_setting('app.tenant_id', true)" in source
    assert "WITH CHECK" in source
    assert (
        "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid" in source
    )


def test_rls_template_canary_downgrade_removes_policies_before_disabling_rls(
    monkeypatch,
):
    migration = _load_migration()
    executed = []

    monkeypatch.setattr(migration, "_is_postgresql", lambda: True)
    monkeypatch.setattr(migration, "_table_exists", lambda table_name: True)
    monkeypatch.setattr(migration.op, "execute", lambda sql: executed.append(str(sql)))

    migration.downgrade()

    source = "\n".join(executed)

    for table in CANARY_TABLES:
        assert f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}" in source
        assert f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY" in source
        assert f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY" in source


def test_rls_template_canary_is_noop_outside_postgresql(monkeypatch):
    migration = _load_migration()

    monkeypatch.setattr(migration, "_is_postgresql", lambda: False)
    monkeypatch.setattr(
        migration.op,
        "execute",
        lambda sql: (_ for _ in ()).throw(AssertionError("unexpected SQL")),
    )

    migration.upgrade()
    migration.downgrade()
