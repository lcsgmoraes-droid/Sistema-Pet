"""Helpers for Alembic migrations that enable tenant-scoped RLS."""

from __future__ import annotations

from collections.abc import Iterator, Sequence


TENANT_RLS_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def _postgres_bind(op_module):
    bind = op_module.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    return bind


def _existing_tables(sa_module, bind, table_names: Sequence[str]) -> list[str]:
    inspector = sa_module.inspect(bind)
    return [table_name for table_name in table_names if inspector.has_table(table_name)]


def _policy_name(table_name: str) -> str:
    return f"{table_name}_tenant_isolation"


def iter_tenant_rls_statements(table_name: str, *, enable: bool) -> Iterator[str]:
    policy = _policy_name(table_name)
    if enable:
        yield f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"
        yield f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"

    yield f"DROP POLICY IF EXISTS {policy} ON {table_name}"

    if enable:
        yield (
            f"CREATE POLICY {policy} ON {table_name} "
            f"USING ({TENANT_RLS_GUARD}) WITH CHECK ({TENANT_RLS_GUARD})"
        )
    else:
        yield f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY"
        yield f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"


def apply_tenant_rls(
    *,
    op_module,
    sa_module,
    table_names: Sequence[str],
    enable: bool,
) -> None:
    bind = _postgres_bind(op_module)
    if bind is None:
        return

    present_tables = _existing_tables(sa_module, bind, table_names)
    if not enable:
        present_tables.reverse()

    for table_name in present_tables:
        for statement in iter_tenant_rls_statements(table_name, enable=enable):
            op_module.execute(statement)
