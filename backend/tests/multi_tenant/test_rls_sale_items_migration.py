from app.db.sql_audit import TENANT_TABLES
from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("tg20260614a1_rls_sale_items.py")

SALE_ITEM_RLS_TABLES = ("venda_itens",)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        SALE_ITEM_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_sale_item_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="tg20260614a1",
        down_revision="tf20260614a1",
        table_constant="SALE_ITEM_RLS_TABLES",
        table_names=SALE_ITEM_RLS_TABLES,
    )


def test_sale_item_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        SALE_ITEM_RLS_TABLES,
    )


def test_sale_item_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_sale_item_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        SALE_ITEM_RLS_TABLES,
    )


def test_sale_item_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []


def test_sale_item_table_is_tracked_by_raw_sql_guardrails():
    assert "venda_itens" in TENANT_SCOPED_TABLES
    assert "venda_itens" in TENANT_TABLES
