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


def _statements_containing(statements: list[str], fragment: str) -> list[str]:
    return [sql for sql in statements if fragment in sql]


def test_fiscal_company_rls_migration_metadata_and_scope():
    assert MIGRATION_FILE.exists()

    migration = _load_migration()
    assert migration["revision"] == "qg20260611a1"
    assert migration["down_revision"] == "qf20260611a1"
    assert migration["TENANT_GUARD"] == TENANT_GUARD
    assert migration["FISCAL_COMPANY_RLS_TABLES"] == FISCAL_COMPANY_RLS_TABLES


def test_fiscal_company_rls_upgrade_targets_existing_tables_in_declared_order(monkeypatch):
    emitted = _capture(monkeypatch, "upgrade")

    create_policy_sql = _statements_containing(emitted, "CREATE POLICY")
    assert len(create_policy_sql) == len(FISCAL_COMPANY_RLS_TABLES)
    for table_name, statement in zip(
        FISCAL_COMPANY_RLS_TABLES,
        create_policy_sql,
        strict=True,
    ):
        assert table_name in statement

    assert len(_statements_containing(emitted, "ENABLE ROW LEVEL SECURITY")) == 2
    assert len(_statements_containing(emitted, "FORCE ROW LEVEL SECURITY")) == 2
    assert len(_statements_containing(emitted, f"WITH CHECK ({TENANT_GUARD})")) == 2


def test_fiscal_company_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = _capture(monkeypatch, "upgrade", existing=("empresa_config_fiscal",))
    emitted_sql = "\n".join(emitted)

    assert "empresa_config_fiscal" in emitted_sql
    assert "simples_nacional_mensal" not in emitted_sql


def test_fiscal_company_rls_downgrade_unwinds_existing_tables_in_reverse_order(monkeypatch):
    emitted = _capture(monkeypatch, "downgrade")
    reversed_tables = tuple(reversed(FISCAL_COMPANY_RLS_TABLES))

    for fragment in (
        "DROP POLICY IF EXISTS",
        "NO FORCE ROW LEVEL SECURITY",
        "DISABLE ROW LEVEL SECURITY",
    ):
        matching_sql = _statements_containing(emitted, fragment)
        assert len(matching_sql) == len(reversed_tables)
        for table_name, statement in zip(reversed_tables, matching_sql, strict=True):
            assert table_name in statement


def test_fiscal_company_rls_migration_skips_when_bind_or_tables_are_not_applicable(
    monkeypatch,
):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
