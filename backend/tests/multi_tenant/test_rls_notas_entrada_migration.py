from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("so20260613a1_rls_notas_entrada_tables.py")

NOTAS_ENTRADA_RLS_TABLES = ("notas_entrada", "notas_entrada_itens")


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        NOTAS_ENTRADA_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_notas_entrada_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="so20260613a1",
        down_revision="sn20260613a1",
        table_constant="NOTAS_ENTRADA_RLS_TABLES",
        table_names=NOTAS_ENTRADA_RLS_TABLES,
    )


def test_notas_entrada_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        NOTAS_ENTRADA_RLS_TABLES,
    )


def test_notas_entrada_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_notas_entrada_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        NOTAS_ENTRADA_RLS_TABLES,
    )


def test_notas_entrada_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []


def test_notas_entrada_are_tracked_by_tenant_safe_sql_guardrail():
    for table_name in NOTAS_ENTRADA_RLS_TABLES:
        assert table_name in TENANT_SCOPED_TABLES
