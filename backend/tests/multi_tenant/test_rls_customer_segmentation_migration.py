from pathlib import Path
import runpy


MIGRATION_FILE = Path(__file__).resolve().parents[2] / (
    "alembic/versions/pv20260611a1_rls_customer_segmentation_tables.py"
)

SEGMENTATION_TABLE = "cliente_segmentos"
TENANT_PREDICATE_SQL = (
    "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
)


def _migration():
    return runpy.run_path(str(MIGRATION_FILE))


def _run_migration(monkeypatch, action_name: str, *, table_exists: bool = True) -> list[str]:
    migration = _migration()
    action = migration[action_name]
    action_globals = action.__globals__
    emitted: list[str] = []

    monkeypatch.setitem(action_globals, "postgresql_connection", lambda: object())
    monkeypatch.setitem(
        action_globals,
        "table_exists",
        lambda bind, table_name: table_exists and table_name == SEGMENTATION_TABLE,
    )
    monkeypatch.setattr(action_globals["op"], "execute", emitted.append)

    action()

    return [str(statement) for statement in emitted]


def test_customer_segmentation_rls_migration_is_after_ration_options():
    assert MIGRATION_FILE.exists()

    source = MIGRATION_FILE.read_text(encoding="utf-8")

    assert 'revision = "pv20260611a1"' in source
    assert 'down_revision = "pu20260611a1"' in source
    assert SEGMENTATION_TABLE in source
    assert TENANT_PREDICATE_SQL in source


def test_customer_segmentation_upgrade_emits_single_table_policy(monkeypatch):
    statements = _run_migration(monkeypatch, "upgrade")

    assert statements == [
        f"ALTER TABLE {SEGMENTATION_TABLE} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {SEGMENTATION_TABLE} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS {SEGMENTATION_TABLE}_tenant_isolation ON {SEGMENTATION_TABLE}",
        (
            f"CREATE POLICY {SEGMENTATION_TABLE}_tenant_isolation ON {SEGMENTATION_TABLE} "
            f"USING ({TENANT_PREDICATE_SQL}) WITH CHECK ({TENANT_PREDICATE_SQL})"
        ),
    ]


def test_customer_segmentation_migration_skips_missing_table(monkeypatch):
    assert _run_migration(monkeypatch, "upgrade", table_exists=False) == []


def test_customer_segmentation_downgrade_removes_policy_and_rls(monkeypatch):
    statements = _run_migration(monkeypatch, "downgrade")

    assert statements == [
        f"DROP POLICY IF EXISTS {SEGMENTATION_TABLE}_tenant_isolation ON {SEGMENTATION_TABLE}",
        f"ALTER TABLE {SEGMENTATION_TABLE} NO FORCE ROW LEVEL SECURITY",
        f"ALTER TABLE {SEGMENTATION_TABLE} DISABLE ROW LEVEL SECURITY",
    ]


def test_customer_segmentation_migration_is_noop_without_postgresql(monkeypatch):
    migration = _migration()
    migration_globals = migration["upgrade"].__globals__

    monkeypatch.setitem(migration_globals, "postgresql_connection", lambda: None)
    monkeypatch.setattr(
        migration_globals["op"],
        "execute",
        lambda statement: (_ for _ in ()).throw(AssertionError("unexpected SQL")),
    )

    migration["upgrade"]()
    migration["downgrade"]()
