from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("sb20260612a1_rls_rotas_entrega.py")

ROTAS_ENTREGA_RLS_TABLES = (
    "rotas_entrega",
    "rotas_entrega_paradas",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        ROTAS_ENTREGA_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_rotas_entrega_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="sb20260612a1",
        down_revision="sa20260612a1",
        table_constant="ROTAS_ENTREGA_RLS_TABLES",
        table_names=ROTAS_ENTREGA_RLS_TABLES,
    )


def test_rotas_entrega_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        ROTAS_ENTREGA_RLS_TABLES,
    )


def test_rotas_entrega_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_rotas_entrega_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        ROTAS_ENTREGA_RLS_TABLES,
    )


def test_rotas_entrega_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
