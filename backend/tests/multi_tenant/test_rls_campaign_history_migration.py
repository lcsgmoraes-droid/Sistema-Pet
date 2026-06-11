from pathlib import Path
import runpy
from types import SimpleNamespace


MIGRATION_FILE = Path(__file__).resolve().parents[2] / "alembic" / "versions" / (
    "qa20260611a1_rls_campaign_history_tables.py"
)

HISTORY_TABLES = (
    "customer_rank_history",
    "notification_log",
    "customer_merge_logs",
)

TENANT_MATCH = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _load_migration():
    return runpy.run_path(str(MIGRATION_FILE))


def _run_and_capture(monkeypatch, action: str, *, dialect="postgresql", existing=HISTORY_TABLES):
    migration = _load_migration()
    statements: list[str] = []

    class _Inspector:
        def has_table(self, table_name: str) -> bool:
            return table_name in existing

    bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect))
    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(migration["op"], "execute", lambda sql: statements.append(str(sql)))
    monkeypatch.setattr(migration["sa"], "inspect", lambda received_bind: _Inspector())

    migration[action]()
    return statements


def test_campaign_history_rls_migration_chains_after_drawings():
    assert MIGRATION_FILE.exists()

    source = MIGRATION_FILE.read_text(encoding="utf-8")
    assert 'revision = "qa20260611a1"' in source
    assert 'down_revision = "pz20260611a1"' in source
    assert TENANT_MATCH in source
    assert "campaign_event_queue" not in source
    assert "notification_queue" not in source


def test_campaign_history_upgrade_targets_only_existing_history_tables(monkeypatch):
    existing = ("customer_rank_history", "customer_merge_logs")
    statements = _run_and_capture(monkeypatch, "upgrade", existing=existing)
    emitted = "\n".join(statements)

    assert "notification_log" not in emitted
    assert emitted.count("ENABLE ROW LEVEL SECURITY") == len(existing)
    assert emitted.count("FORCE ROW LEVEL SECURITY") == len(existing)
    assert emitted.count("CREATE POLICY") == len(existing)

    for table_name in existing:
        assert f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}" in emitted
        assert f"USING ({TENANT_MATCH}) WITH CHECK ({TENANT_MATCH})" in emitted


def test_campaign_history_downgrade_unwinds_from_last_table_first(monkeypatch):
    statements = _run_and_capture(monkeypatch, "downgrade")

    assert [sql for sql in statements if sql.startswith("DROP POLICY IF EXISTS")] == [
        "DROP POLICY IF EXISTS customer_merge_logs_tenant_isolation ON customer_merge_logs",
        "DROP POLICY IF EXISTS notification_log_tenant_isolation ON notification_log",
        "DROP POLICY IF EXISTS customer_rank_history_tenant_isolation ON customer_rank_history",
    ]

    for table_name in HISTORY_TABLES:
        assert f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY" in statements
        assert f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY" in statements


def test_campaign_history_migration_noops_when_not_postgresql(monkeypatch):
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
