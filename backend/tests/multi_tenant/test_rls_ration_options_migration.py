from pathlib import Path
import runpy


MIGRATION_FILE = Path(__file__).resolve().parents[2].joinpath(
    "alembic",
    "versions",
    "pu20260611a1_rls_ration_options_tables.py",
)

RATION_OPTION_TABLES = (
    "linhas_racao",
    "portes_animal",
    "fases_publico",
    "tipos_tratamento",
    "sabores_proteina",
    "apresentacoes_peso",
)

TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _load_target_migration():
    return runpy.run_path(str(MIGRATION_FILE))


def _collect_statements(monkeypatch, action_name: str, available_tables=None) -> str:
    migration = _load_target_migration()
    statements: list[str] = []
    action = migration[action_name]
    action_globals = action.__globals__

    monkeypatch.setitem(action_globals, "_postgres_bind", lambda: object())
    monkeypatch.setitem(
        action_globals,
        "_existing_option_tables",
        lambda bind: frozenset(available_tables or RATION_OPTION_TABLES),
    )
    monkeypatch.setattr(action_globals["op"], "execute", lambda sql: statements.append(str(sql)))

    action()

    return "\n".join(statements)


def test_rls_ration_options_migration_continues_from_product_catalog_head():
    assert MIGRATION_FILE.exists()

    source = MIGRATION_FILE.read_text(encoding="utf-8")
    required_fragments = [
        'revision = "pu20260611a1"',
        'down_revision = "pt20260611a1"',
        "postgresql",
        TENANT_GUARD,
    ]

    for fragment in required_fragments:
        assert fragment in source


def test_rls_ration_options_upgrade_targets_only_existing_tables(monkeypatch):
    present = ("linhas_racao", "tipos_tratamento", "apresentacoes_peso")
    emitted = _collect_statements(monkeypatch, "upgrade", available_tables=present)

    assert emitted.count("ENABLE ROW LEVEL SECURITY") == len(present)
    assert emitted.count("FORCE ROW LEVEL SECURITY") == len(present)
    assert emitted.count("CREATE POLICY") == len(present)
    assert emitted.count("WITH CHECK") == len(present)
    assert TENANT_GUARD in emitted

    for table_name in present:
        assert f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}" in emitted
        assert f"CREATE POLICY {table_name}_tenant_isolation ON {table_name}" in emitted

    for skipped_table in set(RATION_OPTION_TABLES) - set(present):
        assert skipped_table not in emitted


def test_rls_ration_options_downgrade_unwinds_in_reverse_table_order(monkeypatch):
    emitted = _collect_statements(monkeypatch, "downgrade")
    drop_positions = [
        emitted.index(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation")
        for table_name in reversed(RATION_OPTION_TABLES)
    ]

    assert drop_positions == sorted(drop_positions)

    for table_name in RATION_OPTION_TABLES:
        assert f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY" in emitted
        assert f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY" in emitted


def test_rls_ration_options_migration_does_nothing_without_postgresql(monkeypatch):
    migration = _load_target_migration()
    migration_globals = migration["upgrade"].__globals__

    monkeypatch.setitem(migration_globals, "_postgres_bind", lambda: None)
    monkeypatch.setattr(
        migration_globals["op"],
        "execute",
        lambda sql: (_ for _ in ()).throw(AssertionError("unexpected SQL")),
    )

    migration["upgrade"]()
    migration["downgrade"]()
