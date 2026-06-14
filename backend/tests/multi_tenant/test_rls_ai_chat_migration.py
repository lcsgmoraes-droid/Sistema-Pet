from app.utils.tenant_safe_sql import TENANT_SCOPED_TABLES
from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("ta20260614a1_rls_ai_chat_tables.py")

AI_CHAT_RLS_TABLES = (
    "conversas_ia",
    "mensagens_chat",
    "contexto_financeiro_chat",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        AI_CHAT_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_ai_chat_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="ta20260614a1",
        down_revision="sz20260614a1",
        table_constant="AI_CHAT_RLS_TABLES",
        table_names=AI_CHAT_RLS_TABLES,
    )


def test_ai_chat_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        AI_CHAT_RLS_TABLES,
    )


def test_ai_chat_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_ai_chat_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        AI_CHAT_RLS_TABLES,
    )


def test_ai_chat_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []


def test_ai_chat_tables_are_tracked_by_tenant_safe_sql_guardrail():
    assert set(AI_CHAT_RLS_TABLES).issubset(TENANT_SCOPED_TABLES)
