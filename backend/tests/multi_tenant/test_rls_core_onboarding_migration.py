from pathlib import Path
import runpy


MIGRATION_PATH = Path(__file__).resolve().parents[2] / Path(
    "alembic/versions/ps20260611a1_rls_core_onboarding_tables.py"
)

RLS_TABLES = ("formas_pagamento", "especies", "racas")
TENANT_PREDICATE = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _load_migration():
    return runpy.run_path(str(MIGRATION_PATH))


def _run_and_collect(monkeypatch, action: str, tables=RLS_TABLES) -> str:
    migration = _load_migration()
    fake_bind = object()
    commands = []
    migration_globals = migration[action].__globals__

    monkeypatch.setitem(migration_globals, "_postgresql_bind", lambda: fake_bind)
    monkeypatch.setitem(migration_globals, "_existing_targets", lambda bind: list(tables))
    monkeypatch.setattr(migration_globals["op"], "execute", commands.append)

    migration[action]()

    return "\n".join(str(command) for command in commands)


def test_rls_core_onboarding_migration_is_linear_successor_of_template_canary():
    assert MIGRATION_PATH.exists()

    source = MIGRATION_PATH.read_text(encoding="utf-8")
    expected_metadata = {
        'revision = "ps20260611a1"',
        'down_revision = "pr20260611a1"',
        '"formas_pagamento"',
        '"especies"',
        '"racas"',
        "postgresql",
    }

    for snippet in expected_metadata:
        assert snippet in source


def test_rls_core_onboarding_upgrade_emits_tenant_policy_for_existing_targets(monkeypatch):
    emitted_sql = _run_and_collect(monkeypatch, "upgrade")

    assert emitted_sql.count("ENABLE ROW LEVEL SECURITY") == len(RLS_TABLES)
    assert emitted_sql.count("FORCE ROW LEVEL SECURITY") == len(RLS_TABLES)
    assert emitted_sql.count("CREATE POLICY") == len(RLS_TABLES)
    assert emitted_sql.count("WITH CHECK") == len(RLS_TABLES)
    assert TENANT_PREDICATE in emitted_sql

    for table_name in RLS_TABLES:
        assert f"{table_name}_tenant_isolation" in emitted_sql
        assert f"ON {table_name}" in emitted_sql


def test_rls_core_onboarding_downgrade_removes_child_policy_first(monkeypatch):
    emitted_sql = _run_and_collect(monkeypatch, "downgrade")

    assert emitted_sql.index("DROP POLICY IF EXISTS racas_tenant_isolation") < emitted_sql.index(
        "DROP POLICY IF EXISTS especies_tenant_isolation"
    )

    for table_name in RLS_TABLES:
        assert f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}" in emitted_sql
        assert f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY" in emitted_sql
        assert f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY" in emitted_sql


def test_rls_core_onboarding_skips_tables_missing_from_older_databases(monkeypatch):
    emitted_sql = _run_and_collect(monkeypatch, "upgrade", tables=("especies",))

    assert "ON especies" in emitted_sql
    assert "formas_pagamento" not in emitted_sql
    assert "ON racas" not in emitted_sql


def test_rls_core_onboarding_is_noop_when_alembic_is_not_using_postgresql(monkeypatch):
    migration = _load_migration()
    migration_globals = migration["upgrade"].__globals__

    monkeypatch.setitem(migration_globals, "_postgresql_bind", lambda: None)
    monkeypatch.setattr(
        migration_globals["op"],
        "execute",
        lambda sql: (_ for _ in ()).throw(AssertionError("unexpected SQL")),
    )

    migration["upgrade"]()
    migration["downgrade"]()
