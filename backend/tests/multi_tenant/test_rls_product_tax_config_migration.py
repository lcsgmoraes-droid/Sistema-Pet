from pathlib import Path
import runpy


MIGRATION_FILE = Path(__file__).resolve().parents[2].joinpath(
    "alembic",
    "versions",
    "pw20260611a1_rls_product_tax_config_tables.py",
)

TAX_CONFIG_TABLES = (
    "produto_config_fiscal",
    "kit_config_fiscal",
    "variacao_config_fiscal",
)

TENANT_POLICY_SQL = (
    "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
)


def _load_migration():
    return runpy.run_path(str(MIGRATION_FILE))


def _capture(monkeypatch, action: str, existing_tables=TAX_CONFIG_TABLES) -> list[str]:
    migration = _load_migration()
    action_fn = migration[action]
    globals_ = action_fn.__globals__
    captured: list[str] = []

    monkeypatch.setitem(globals_, "get_postgresql_bind", lambda: object())
    monkeypatch.setitem(globals_, "existing_tax_config_tables", lambda bind: set(existing_tables))
    monkeypatch.setattr(globals_["op"], "execute", lambda statement: captured.append(str(statement)))

    action_fn()

    return captured


def test_product_tax_config_rls_migration_is_linear_successor():
    assert MIGRATION_FILE.exists()

    source = MIGRATION_FILE.read_text(encoding="utf-8")
    for expected in (
        'revision = "pw20260611a1"',
        'down_revision = "pv20260611a1"',
        "postgresql",
        TENANT_POLICY_SQL,
    ):
        assert expected in source


def test_product_tax_config_upgrade_emits_policy_for_available_tables(monkeypatch):
    statements = _capture(
        monkeypatch,
        "upgrade",
        existing_tables=("produto_config_fiscal", "variacao_config_fiscal"),
    )
    emitted_sql = "\n".join(statements)

    assert "kit_config_fiscal" not in emitted_sql
    assert emitted_sql.count("ENABLE ROW LEVEL SECURITY") == 2
    assert emitted_sql.count("FORCE ROW LEVEL SECURITY") == 2
    assert emitted_sql.count("CREATE POLICY") == 2
    assert emitted_sql.count("WITH CHECK") == 2

    for table_name in ("produto_config_fiscal", "variacao_config_fiscal"):
        assert f"{table_name}_tenant_isolation" in emitted_sql
        assert f"ON {table_name}" in emitted_sql


def test_product_tax_config_downgrade_starts_with_variation_table(monkeypatch):
    emitted_sql = "\n".join(_capture(monkeypatch, "downgrade"))

    assert emitted_sql.index("DROP POLICY IF EXISTS variacao_config_fiscal_tenant_isolation") < emitted_sql.index(
        "DROP POLICY IF EXISTS produto_config_fiscal_tenant_isolation"
    )

    for table_name in TAX_CONFIG_TABLES:
        assert f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}" in emitted_sql
        assert f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY" in emitted_sql
        assert f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY" in emitted_sql


def test_product_tax_config_migration_is_noop_outside_postgresql(monkeypatch):
    migration = _load_migration()
    globals_ = migration["upgrade"].__globals__

    monkeypatch.setitem(globals_, "get_postgresql_bind", lambda: None)
    monkeypatch.setattr(
        globals_["op"],
        "execute",
        lambda statement: (_ for _ in ()).throw(AssertionError("unexpected SQL")),
    )

    migration["upgrade"]()
    migration["downgrade"]()
