import runpy
from pathlib import Path
from types import SimpleNamespace


MIGRATION_FILE = Path(__file__).resolve().parents[2] / "alembic" / "versions" / (
    "qg20260611a1_rls_fiscal_company_tables.py"
)

FISCAL_COMPANY_RLS_TABLES = (
    "empresa_config_fiscal",
    "simples_nacional_mensal",
)

TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _load_migration():
    return runpy.run_path(str(MIGRATION_FILE))


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    migration = _load_migration()
    emitted: list[str] = []
    present = set(FISCAL_COMPANY_RLS_TABLES if existing is None else existing)
    bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect))
    inspector = SimpleNamespace(has_table=lambda table_name: table_name in present)

    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(migration["op"], "execute", lambda sql: emitted.append(str(sql)))
    monkeypatch.setattr(migration["sa"], "inspect", lambda _bind: inspector)

    migration[action_name]()
    return emitted


def _enable_statements(table_name: str) -> list[str]:
    policy = f"{table_name}_tenant_isolation"
    return [
        f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {policy} ON {table_name}",
        (
            f"CREATE POLICY {policy} ON {table_name} "
            f"USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
        ),
    ]


def test_fiscal_company_rls_migration_metadata_and_scope():
    assert MIGRATION_FILE.exists()

    source = MIGRATION_FILE.read_text(encoding="utf-8")
    assert 'revision = "qg20260611a1"' in source
    assert 'down_revision = "qf20260611a1"' in source
    assert TENANT_GUARD in source
    for table_name in FISCAL_COMPANY_RLS_TABLES:
        assert f'"{table_name}"' in source


def test_fiscal_company_rls_upgrade_targets_existing_tables_in_declared_order(monkeypatch):
    existing = ("empresa_config_fiscal",)

    emitted = _capture(monkeypatch, "upgrade", existing=existing)

    assert emitted == [
        statement
        for table_name in existing
        for statement in _enable_statements(table_name)
    ]


def test_fiscal_company_rls_downgrade_unwinds_existing_tables_in_reverse_order(monkeypatch):
    emitted = _capture(monkeypatch, "downgrade")
    reversed_tables = tuple(reversed(FISCAL_COMPANY_RLS_TABLES))

    assert [sql for sql in emitted if sql.startswith("DROP POLICY IF EXISTS")] == [
        f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"
        for table_name in reversed_tables
    ]
    assert [sql for sql in emitted if "NO FORCE ROW LEVEL SECURITY" in sql] == [
        f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY"
        for table_name in reversed_tables
    ]
    assert [sql for sql in emitted if "DISABLE ROW LEVEL SECURITY" in sql] == [
        f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"
        for table_name in reversed_tables
    ]


def test_fiscal_company_rls_migration_skips_when_bind_or_tables_are_not_applicable(
    monkeypatch,
):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
