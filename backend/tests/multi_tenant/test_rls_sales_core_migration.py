from pathlib import Path

from app.db.sql_audit import TENANT_TABLES
from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("th20260614a1_rls_sales_core.py")
ML_RACOES_ROUTES_FILE = (
    Path(__file__).resolve().parents[2] / "app" / "ml_racoes_routes.py"
)

VENDAS_RLS_TABLES = ("vendas",)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        VENDAS_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_sales_core_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="th20260614a1",
        down_revision="tg20260614a1",
        table_constant="VENDAS_RLS_TABLES",
        table_names=VENDAS_RLS_TABLES,
    )


def test_sales_core_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        VENDAS_RLS_TABLES,
    )


def test_sales_core_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_sales_core_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        VENDAS_RLS_TABLES,
    )


def test_sales_core_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []


def test_sales_core_table_is_tracked_by_raw_sql_guardrails():
    assert "vendas" in TENANT_SCOPED_TABLES
    assert "vendas" in TENANT_TABLES


def test_ml_racoes_sales_query_uses_tenant_safe_sql():
    source = ML_RACOES_ROUTES_FILE.read_text(encoding="utf-8")

    assert "from .utils.tenant_safe_sql import execute_tenant_safe" in source
    assert "execute_tenant_safe(" in source
    assert "v.{tenant_filter}" in source
    assert "vi.{tenant_filter}" in source
    assert "db.execute(" not in source
