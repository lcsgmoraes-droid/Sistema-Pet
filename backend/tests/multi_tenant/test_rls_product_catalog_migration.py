from pathlib import Path
import runpy


MIGRATION_PATH = Path(__file__).resolve().parents[2] / Path(
    "alembic/versions/pt20260611a1_rls_product_catalog_tables.py"
)

PRODUCT_CATALOG_TABLES = ("departamentos", "marcas", "categorias")
TENANT_MATCH = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _migration_namespace():
    return runpy.run_path(str(MIGRATION_PATH))


def _capture_sql(
    monkeypatch, action: str, existing_tables=PRODUCT_CATALOG_TABLES
) -> list[str]:
    namespace = _migration_namespace()
    globals_for_action = namespace[action].__globals__
    statements = []

    monkeypatch.setitem(globals_for_action, "_postgres", lambda: object())
    monkeypatch.setitem(
        globals_for_action,
        "_present_tables",
        lambda bind: set(existing_tables),
    )
    monkeypatch.setattr(
        globals_for_action["op"],
        "execute",
        lambda sql: statements.append(str(sql)),
    )

    namespace[action]()

    return statements


def test_rls_product_catalog_migration_is_chained_after_core_onboarding():
    assert MIGRATION_PATH.exists()

    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "pt20260611a1"' in source
    assert 'down_revision = "ps20260611a1"' in source
    for table_name in PRODUCT_CATALOG_TABLES:
        assert f'"{table_name}"' in source


def test_rls_product_catalog_upgrade_emits_policy_for_each_present_table(monkeypatch):
    statements = _capture_sql(
        monkeypatch,
        "upgrade",
        existing_tables=("departamentos", "categorias"),
    )
    joined = "\n".join(statements)

    assert "marcas" not in joined
    assert joined.count("ENABLE ROW LEVEL SECURITY") == 2
    assert joined.count("FORCE ROW LEVEL SECURITY") == 2
    assert joined.count("CREATE POLICY") == 2
    assert joined.count("WITH CHECK") == 2
    assert TENANT_MATCH in joined

    assert "departamentos_tenant_isolation" in joined
    assert "categorias_tenant_isolation" in joined


def test_rls_product_catalog_downgrade_disables_child_tables_first(monkeypatch):
    statements = _capture_sql(monkeypatch, "downgrade")
    joined = "\n".join(statements)

    assert joined.index(
        "DROP POLICY IF EXISTS categorias_tenant_isolation"
    ) < joined.index("DROP POLICY IF EXISTS departamentos_tenant_isolation")

    for table_name in PRODUCT_CATALOG_TABLES:
        assert (
            f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"
            in joined
        )
        assert f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY" in joined
        assert f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY" in joined


def test_rls_product_catalog_is_noop_outside_postgresql(monkeypatch):
    namespace = _migration_namespace()
    globals_for_upgrade = namespace["upgrade"].__globals__

    monkeypatch.setitem(globals_for_upgrade, "_postgres", lambda: None)
    monkeypatch.setattr(
        globals_for_upgrade["op"],
        "execute",
        lambda sql: (_ for _ in ()).throw(AssertionError("unexpected SQL")),
    )

    namespace["upgrade"]()
    namespace["downgrade"]()
