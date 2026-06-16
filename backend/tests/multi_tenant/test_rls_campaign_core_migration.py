from pathlib import Path
import runpy


MIGRATION_FILE = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / ("px20260611a1_rls_campaign_core_tables.py")
)

CAMPAIGN_CORE_TABLES = (
    "campaigns",
    "campaign_executions",
    "campaign_run_log",
    "campaign_locks",
)

TENANT_POLICY = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


class _Bind:
    def __init__(self, dialect_name: str):
        self.dialect = type("Dialect", (), {"name": dialect_name})()


class _Inspector:
    def __init__(self, available_tables: tuple[str, ...]):
        self.available_tables = set(available_tables)
        self.seen: list[str] = []

    def has_table(self, table_name: str) -> bool:
        self.seen.append(table_name)
        return table_name in self.available_tables


def _load_migration():
    return runpy.run_path(str(MIGRATION_FILE))


def _emit_sql(monkeypatch, action_name: str, available_tables=CAMPAIGN_CORE_TABLES):
    migration = _load_migration()
    bind = _Bind("postgresql")
    inspector = _Inspector(tuple(available_tables))
    statements: list[str] = []

    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(
        migration["op"], "execute", lambda sql: statements.append(str(sql))
    )
    monkeypatch.setattr(migration["sa"], "inspect", lambda received_bind: inspector)

    migration[action_name]()

    return statements, inspector.seen


def test_campaign_core_rls_migration_is_next_linear_revision():
    assert MIGRATION_FILE.exists()

    source = MIGRATION_FILE.read_text(encoding="utf-8")
    assert 'revision = "px20260611a1"' in source
    assert 'down_revision = "pw20260611a1"' in source
    assert TENANT_POLICY in source
    assert "campaign_event_queue" not in source
    assert "notification_queue" not in source


def test_campaign_core_upgrade_enables_rls_only_for_existing_targets(monkeypatch):
    existing = ("campaigns", "campaign_run_log", "campaign_locks")
    statements, inspected = _emit_sql(monkeypatch, "upgrade", available_tables=existing)
    emitted = "\n".join(statements)

    assert tuple(inspected) == CAMPAIGN_CORE_TABLES
    assert "campaign_executions" not in emitted
    assert emitted.count("ENABLE ROW LEVEL SECURITY") == len(existing)
    assert emitted.count("FORCE ROW LEVEL SECURITY") == len(existing)
    assert emitted.count("CREATE POLICY") == len(existing)
    assert emitted.count("WITH CHECK") == len(existing)

    for table_name in existing:
        assert (
            f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"
            in emitted
        )
        assert f"CREATE POLICY {table_name}_tenant_isolation ON {table_name}" in emitted


def test_campaign_core_downgrade_removes_policies_in_reverse_order(monkeypatch):
    statements, _ = _emit_sql(monkeypatch, "downgrade")
    policy_drops = [
        sql for sql in statements if sql.startswith("DROP POLICY IF EXISTS")
    ]

    assert policy_drops == [
        f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"
        for table_name in reversed(CAMPAIGN_CORE_TABLES)
    ]

    emitted = "\n".join(statements)
    for table_name in CAMPAIGN_CORE_TABLES:
        assert f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY" in emitted
        assert f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY" in emitted


def test_campaign_core_rls_migration_skips_non_postgresql_binds(monkeypatch):
    migration = _load_migration()

    monkeypatch.setattr(migration["op"], "get_bind", lambda: _Bind("sqlite"))
    monkeypatch.setattr(
        migration["op"],
        "execute",
        lambda sql: (_ for _ in ()).throw(AssertionError("unexpected SQL")),
    )

    migration["upgrade"]()
    migration["downgrade"]()
