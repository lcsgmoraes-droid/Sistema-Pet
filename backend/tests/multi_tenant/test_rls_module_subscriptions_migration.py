from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qs20260612a1_rls_module_subscriptions_table.py")

MODULE_SUBSCRIPTIONS_RLS_TABLES = ("assinaturas_modulos",)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        MODULE_SUBSCRIPTIONS_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_module_subscriptions_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qs20260612a1",
        down_revision="qr20260612a1",
        table_constant="MODULE_SUBSCRIPTIONS_RLS_TABLES",
        table_names=MODULE_SUBSCRIPTIONS_RLS_TABLES,
    )


def test_module_subscriptions_rls_upgrade_targets_declared_table(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        MODULE_SUBSCRIPTIONS_RLS_TABLES,
    )


def test_module_subscriptions_rls_upgrade_skips_missing_table(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_module_subscriptions_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        MODULE_SUBSCRIPTIONS_RLS_TABLES,
    )


def test_module_subscriptions_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
