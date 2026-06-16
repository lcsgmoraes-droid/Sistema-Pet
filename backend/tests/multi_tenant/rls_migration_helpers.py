import runpy
from pathlib import Path
from types import SimpleNamespace


TENANT_RLS_GUARD = (
    "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
)


def migration_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[2] / "alembic" / "versions" / filename


def load_migration(migration_file: Path):
    return runpy.run_path(str(migration_file))


def capture_migration_sql(
    monkeypatch,
    migration_file: Path,
    action_name: str,
    table_names: tuple[str, ...],
    *,
    dialect="postgresql",
    existing=None,
) -> list[str]:
    migration = load_migration(migration_file)
    emitted: list[str] = []
    present = set(table_names if existing is None else existing)
    bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect))
    inspector = SimpleNamespace(has_table=lambda table_name: table_name in present)

    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(
        migration["op"], "execute", lambda sql: emitted.append(str(sql))
    )
    monkeypatch.setattr(migration["sa"], "inspect", lambda _bind: inspector)

    migration[action_name]()
    return emitted


def statements_containing(statements: list[str], fragment: str) -> list[str]:
    return [sql for sql in statements if fragment in sql]


def assert_rls_migration_metadata(
    migration_file: Path,
    *,
    revision: str,
    down_revision: str,
    table_constant: str,
    table_names: tuple[str, ...],
) -> None:
    assert migration_file.exists()

    migration = load_migration(migration_file)
    assert migration["revision"] == revision
    assert migration["down_revision"] == down_revision
    assert migration["TENANT_GUARD"] == TENANT_RLS_GUARD
    assert migration[table_constant] == table_names


def assert_upgrade_emits_rls_for_declared_tables(
    emitted: list[str],
    table_names: tuple[str, ...],
) -> None:
    create_policy_sql = statements_containing(emitted, "CREATE POLICY")
    assert len(create_policy_sql) == len(table_names)
    for table_name, statement in zip(table_names, create_policy_sql, strict=True):
        assert table_name in statement

    assert len(statements_containing(emitted, "ENABLE ROW LEVEL SECURITY")) == len(
        table_names
    )
    assert len(statements_containing(emitted, "FORCE ROW LEVEL SECURITY")) == len(
        table_names
    )
    assert len(
        statements_containing(emitted, f"WITH CHECK ({TENANT_RLS_GUARD})")
    ) == len(table_names)


def assert_downgrade_unwinds_in_reverse_order(
    emitted: list[str],
    table_names: tuple[str, ...],
) -> None:
    reversed_tables = tuple(reversed(table_names))
    for fragment in (
        "DROP POLICY IF EXISTS",
        "NO FORCE ROW LEVEL SECURITY",
        "DISABLE ROW LEVEL SECURITY",
    ):
        matching_sql = statements_containing(emitted, fragment)
        assert len(matching_sql) == len(reversed_tables)
        for table_name, statement in zip(reversed_tables, matching_sql, strict=True):
            assert table_name in statement
