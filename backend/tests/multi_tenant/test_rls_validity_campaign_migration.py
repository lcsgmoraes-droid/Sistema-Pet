from pathlib import Path
import runpy
from types import SimpleNamespace


MIGRATION_FILE = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / ("qb20260611a1_rls_validity_campaign_tables.py")
)

VALIDITY_CAMPAIGN_TABLES = (
    "campanha_validade_automatica",
    "campanha_validade_exclusoes",
)

TENANT_POLICY = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _load_migration():
    return runpy.run_path(str(MIGRATION_FILE))


def _capture_statements(
    monkeypatch, action: str, *, dialect="postgresql", existing=VALIDITY_CAMPAIGN_TABLES
):
    migration = _load_migration()
    statements: list[str] = []

    class _Inspector:
        def has_table(self, table_name: str) -> bool:
            return table_name in existing

    bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect))
    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(
        migration["op"], "execute", lambda sql: statements.append(str(sql))
    )
    monkeypatch.setattr(migration["sa"], "inspect", lambda bind: _Inspector())

    migration[action]()
    return statements


def test_validity_campaign_rls_migration_is_next_head():
    assert MIGRATION_FILE.exists()

    source = MIGRATION_FILE.read_text(encoding="utf-8")
    assert 'revision = "qb20260611a1"' in source
    assert 'down_revision = "qa20260611a1"' in source
    assert TENANT_POLICY in source
    assert "produto_lotes" not in source
    assert "produtos" not in source


def test_validity_campaign_upgrade_skips_tables_missing_from_older_databases(
    monkeypatch,
):
    statements = _capture_statements(
        monkeypatch,
        "upgrade",
        existing=("campanha_validade_exclusoes",),
    )
    emitted = "\n".join(statements)

    assert "campanha_validade_automatica" not in emitted
    assert emitted.count("ENABLE ROW LEVEL SECURITY") == 1
    assert emitted.count("FORCE ROW LEVEL SECURITY") == 1
    assert emitted.count("CREATE POLICY") == 1
    assert (
        "DROP POLICY IF EXISTS campanha_validade_exclusoes_tenant_isolation" in emitted
    )
    assert f"USING ({TENANT_POLICY}) WITH CHECK ({TENANT_POLICY})" in emitted


def test_validity_campaign_downgrade_unwinds_exclusions_before_config(monkeypatch):
    statements = _capture_statements(monkeypatch, "downgrade")
    policy_drops = [
        sql for sql in statements if sql.startswith("DROP POLICY IF EXISTS")
    ]

    assert policy_drops == [
        (
            "DROP POLICY IF EXISTS campanha_validade_exclusoes_tenant_isolation "
            "ON campanha_validade_exclusoes"
        ),
        (
            "DROP POLICY IF EXISTS campanha_validade_automatica_tenant_isolation "
            "ON campanha_validade_automatica"
        ),
    ]
    for table_name in VALIDITY_CAMPAIGN_TABLES:
        assert f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY" in statements
        assert f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY" in statements


def test_validity_campaign_rls_migration_is_noop_outside_postgresql(monkeypatch):
    migration = _load_migration()
    bind = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(
        migration["op"],
        "execute",
        lambda sql: (_ for _ in ()).throw(AssertionError("unexpected SQL")),
    )

    migration["upgrade"]()
    migration["downgrade"]()
