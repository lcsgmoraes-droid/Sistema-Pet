"""A trilha externa exige RLS e preserva documentos/configurações no downgrade."""

from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from tests.multi_tenant.rls_migration_helpers import (
    load_migration,
    migration_path,
    TENANT_RLS_GUARD,
)

PATH = migration_path("zzzzz20261027a1_ecommerceai_fiscal_orders.py")


def test_three_new_tenant_tables_force_rls_and_permanent_business_identity(monkeypatch):
    migration = load_migration(PATH)
    created = []
    statements = []
    metadata = migration["sa"].MetaData()

    def create_table(name, *columns):
        migration["sa"].Table(name, metadata, *columns)
        created.append((name, columns))

    monkeypatch.setattr(
        migration["op"],
        "get_bind",
        lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
    )
    monkeypatch.setattr(
        migration["op"],
        "create_table",
        create_table,
    )
    monkeypatch.setattr(migration["op"], "create_index", Mock())
    monkeypatch.setattr(
        migration["op"], "execute", lambda sql: statements.append(str(sql))
    )
    monkeypatch.setattr(
        migration["sa"], "inspect", lambda _: SimpleNamespace(has_table=lambda _: True)
    )
    migration["upgrade"]()
    assert migration["down_revision"] == "zzzzy20261026a1"
    assert len(created) == 3
    for name, columns in created:
        assert (
            next(c for c in columns if getattr(c, "name", None) == "tenant_id").nullable
            is False
        )
        assert any(
            name in sql and "FORCE ROW LEVEL SECURITY" in sql for sql in statements
        )
        assert any(
            name in sql
            and "CREATE POLICY" in sql
            and f"USING ({TENANT_RLS_GUARD})" in sql
            and f"WITH CHECK ({TENANT_RLS_GUARD})" in sql
            for sql in statements
        )
    constraints = [
        c
        for c in created[-1][1]
        if getattr(c, "name", None) == "uq_eai_fiscal_order_identity"
    ]
    assert len(constraints) == 1
    assert list(constraints[0].columns.keys()) == [
        "tenant_id",
        "channel",
        "seller_id",
        "external_order_id",
    ]


@pytest.mark.parametrize("history", [True, False])
def test_downgrade_never_discards_any_fiscal_history(monkeypatch, history):
    migration = load_migration(PATH)
    bind = Mock()
    bind.execute.return_value.first.return_value = (1,) if history else None
    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(migration["op"], "execute", Mock())
    drop = Mock()
    monkeypatch.setattr(migration["op"], "drop_table", drop)
    if history:
        with pytest.raises(RuntimeError, match="preserve o histórico"):
            migration["downgrade"]()
        drop.assert_not_called()
    else:
        migration["downgrade"]()
        assert [call.args[0] for call in drop.call_args_list] == list(
            reversed(migration["TABLES"])
        )
