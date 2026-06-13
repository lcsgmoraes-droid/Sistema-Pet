from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("si20260613a1_rls_bling_nfe_cache.py")

BLING_NFE_CACHE_RLS_TABLES = ("bling_notas_fiscais_cache",)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        BLING_NFE_CACHE_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_bling_nfe_cache_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="si20260613a1",
        down_revision="sh20260613a1",
        table_constant="BLING_NFE_CACHE_RLS_TABLES",
        table_names=BLING_NFE_CACHE_RLS_TABLES,
    )


def test_bling_nfe_cache_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        BLING_NFE_CACHE_RLS_TABLES,
    )


def test_bling_nfe_cache_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_bling_nfe_cache_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        BLING_NFE_CACHE_RLS_TABLES,
    )


def test_bling_nfe_cache_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []


def test_bling_nfe_cache_is_tracked_by_tenant_safe_sql_guardrail():
    assert "bling_notas_fiscais_cache" in TENANT_SCOPED_TABLES
