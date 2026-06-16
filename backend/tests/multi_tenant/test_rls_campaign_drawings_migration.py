from pathlib import Path
import runpy
from types import SimpleNamespace


MIGRATION_FILE = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / ("pz20260611a1_rls_campaign_drawings_tables.py")
)

DRAWING_TABLES = (
    "drawings",
    "drawing_entries",
)

TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


class _Bind:
    def __init__(self, dialect_name: str):
        self.dialect = SimpleNamespace(name=dialect_name)


def _load_migration():
    return runpy.run_path(str(MIGRATION_FILE))


def _capture(
    monkeypatch, action_name: str, *, dialect="postgresql", tables=DRAWING_TABLES
):
    migration = _load_migration()
    statements: list[str] = []

    class _Inspector:
        def has_table(self, table_name: str) -> bool:
            return table_name in tables

    monkeypatch.setattr(migration["op"], "get_bind", lambda: _Bind(dialect))
    monkeypatch.setattr(
        migration["op"], "execute", lambda sql: statements.append(str(sql))
    )
    monkeypatch.setattr(migration["sa"], "inspect", lambda bind: _Inspector())

    migration[action_name]()
    return statements


def test_campaign_drawings_rls_migration_chains_after_rewards():
    assert MIGRATION_FILE.exists()

    source = MIGRATION_FILE.read_text(encoding="utf-8")
    assert 'revision = "pz20260611a1"' in source
    assert 'down_revision = "py20260611a1"' in source
    assert TENANT_GUARD in source
    assert "campaign_event_queue" not in source
    assert "notification_queue" not in source
    assert "coupons" not in source


def test_campaign_drawings_upgrade_scopes_each_existing_drawing_table(monkeypatch):
    statements = _capture(monkeypatch, "upgrade", tables=("drawings",))
    emitted = "\n".join(statements)

    assert "drawing_entries" not in emitted
    assert emitted.count("ENABLE ROW LEVEL SECURITY") == 1
    assert emitted.count("FORCE ROW LEVEL SECURITY") == 1
    assert emitted.count("CREATE POLICY") == 1
    assert f"USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})" in emitted
    assert "DROP POLICY IF EXISTS drawings_tenant_isolation ON drawings" in emitted


def test_campaign_drawings_downgrade_handles_entries_before_drawings(monkeypatch):
    statements = _capture(monkeypatch, "downgrade")
    policy_drops = [
        sql for sql in statements if sql.startswith("DROP POLICY IF EXISTS")
    ]

    assert policy_drops == [
        "DROP POLICY IF EXISTS drawing_entries_tenant_isolation ON drawing_entries",
        "DROP POLICY IF EXISTS drawings_tenant_isolation ON drawings",
    ]
    for table_name in DRAWING_TABLES:
        assert f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY" in statements
        assert f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY" in statements


def test_campaign_drawings_rls_migration_noops_outside_postgresql(monkeypatch):
    migration = _load_migration()
    monkeypatch.setattr(migration["op"], "get_bind", lambda: _Bind("sqlite"))
    monkeypatch.setattr(
        migration["op"],
        "execute",
        lambda sql: (_ for _ in ()).throw(AssertionError("unexpected SQL")),
    )

    migration["upgrade"]()
    migration["downgrade"]()
