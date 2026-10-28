"""A clonagem cria armazenamento fiscal isolado e não apaga histórico."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tests.multi_tenant.rls_migration_helpers import (
    TENANT_RLS_GUARD,
    load_migration,
    migration_path,
)

MIGRATION_FILE = migration_path("zzzzx20261026a1_notas_fiscais_clones.py")


def test_nova_tabela_exige_tenant_e_forca_rls_para_leitura_e_escrita(monkeypatch):
    migration = load_migration(MIGRATION_FILE)
    statements = []
    created = []
    bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(
        migration["op"],
        "create_table",
        lambda name, *columns: created.append((name, columns)),
    )
    monkeypatch.setattr(migration["op"], "create_index", Mock())
    monkeypatch.setattr(
        migration["op"], "execute", lambda sql: statements.append(str(sql))
    )
    monkeypatch.setattr(
        migration["sa"],
        "inspect",
        lambda _bind: SimpleNamespace(has_table=lambda _name: True),
    )

    migration["upgrade"]()

    assert migration["revision"] == "zzzzx20261026a1"
    assert migration["down_revision"] == "zzzzw20261025a1"
    assert [name for name, _columns in created] == ["notas_fiscais_clones"]
    tenant = next(
        column
        for column in created[0][1]
        if getattr(column, "name", None) == "tenant_id"
    )
    assert tenant.nullable is False
    assert any("ENABLE ROW LEVEL SECURITY" in sql for sql in statements)
    assert any("FORCE ROW LEVEL SECURITY" in sql for sql in statements)
    assert any(
        "CREATE POLICY" in sql
        and f"USING ({TENANT_RLS_GUARD})" in sql
        and f"WITH CHECK ({TENANT_RLS_GUARD})" in sql
        for sql in statements
    )


@pytest.mark.parametrize("has_history", [True, False])
def test_reversao_preserva_qualquer_rascunho_ou_documento_existente(
    monkeypatch, has_history
):
    migration = load_migration(MIGRATION_FILE)
    bind = Mock()
    bind.execute.return_value.first.return_value = (1,) if has_history else None
    drop = Mock()
    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(migration["op"], "execute", Mock())
    monkeypatch.setattr(migration["op"], "drop_table", drop)

    if has_history:
        with pytest.raises(RuntimeError, match="preserve o histórico"):
            migration["downgrade"]()
        drop.assert_not_called()
    else:
        migration["downgrade"]()
        drop.assert_called_once_with("notas_fiscais_clones")
