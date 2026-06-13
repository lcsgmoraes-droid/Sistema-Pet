from app.db.sql_audit import TENANT_TABLES
from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("sq20260613a1_rls_product_bling_sync_tables.py")

PRODUCT_BLING_SYNC_RLS_TABLES = ("produto_bling_sync", "produto_bling_sync_queue")


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        PRODUCT_BLING_SYNC_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_product_bling_sync_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="sq20260613a1",
        down_revision="sp20260613a1",
        table_constant="PRODUCT_BLING_SYNC_RLS_TABLES",
        table_names=PRODUCT_BLING_SYNC_RLS_TABLES,
    )


def test_product_bling_sync_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        PRODUCT_BLING_SYNC_RLS_TABLES,
    )


def test_product_bling_sync_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_product_bling_sync_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        PRODUCT_BLING_SYNC_RLS_TABLES,
    )


def test_product_bling_sync_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []


def test_product_bling_sync_tables_are_tracked_by_sql_guardrails():
    for table_name in PRODUCT_BLING_SYNC_RLS_TABLES:
        assert table_name in TENANT_SCOPED_TABLES
        assert table_name in TENANT_TABLES
