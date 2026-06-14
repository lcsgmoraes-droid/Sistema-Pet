from app.db.sql_audit import TENANT_TABLES
from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("tc20260614a1_rls_dre_legacy_analysis.py")

DRE_LEGACY_RLS_TABLES = (
    "dre_produtos",
    "dre_categorias_analise",
    "dre_comparacoes",
    "dre_insights",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        DRE_LEGACY_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_dre_legacy_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="tc20260614a1",
        down_revision="tb20260614a1",
        table_constant="DRE_LEGACY_RLS_TABLES",
        table_names=DRE_LEGACY_RLS_TABLES,
    )


def test_dre_legacy_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        DRE_LEGACY_RLS_TABLES,
    )


def test_dre_legacy_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_dre_legacy_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        DRE_LEGACY_RLS_TABLES,
    )


def test_dre_legacy_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []


def test_dre_legacy_tables_are_tracked_by_raw_sql_guardrails():
    for table_name in DRE_LEGACY_RLS_TABLES:
        assert table_name in TENANT_SCOPED_TABLES
        assert table_name in TENANT_TABLES
