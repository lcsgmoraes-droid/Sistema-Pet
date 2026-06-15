from types import SimpleNamespace
from pathlib import Path

import pytest


def test_no_rls_allowlist_matches_intentionally_global_tables():
    from app.tenancy.filters import TENANT_WHITELIST_TABLES
    from app.tenancy.rls_no_debt import INTENTIONALLY_GLOBAL_NO_RLS_TABLES
    from tests.multi_tenant.test_tenant_model_registry import INTENTIONALLY_GLOBAL_TENANT_TABLES

    assert INTENTIONALLY_GLOBAL_NO_RLS_TABLES == INTENTIONALLY_GLOBAL_TENANT_TABLES
    assert INTENTIONALLY_GLOBAL_NO_RLS_TABLES.issubset(TENANT_WHITELIST_TABLES)


def test_no_rls_query_targets_only_public_tenant_id_tables_without_rls():
    from app.tenancy.rls_no_debt import TENANT_ID_TABLES_WITHOUT_RLS_SQL

    sql = str(TENANT_ID_TABLES_WITHOUT_RLS_SQL)

    assert "information_schema.columns" in sql
    assert "col.column_name = 'tenant_id'" in sql
    assert "c.relrowsecurity" in sql
    assert "n.nspname = 'public'" in sql


def test_assert_no_unexpected_no_rls_tables_accepts_intentional_globals():
    from app.tenancy.rls_no_debt import assert_no_unexpected_no_rls_tables

    db = _FakeDb(
        [
            ("bling_pedido_webhook_events",),
            ("campaign_event_queue",),
            ("notification_queue",),
            ("ops_alerts",),
            ("ops_error_events",),
            ("user_sessions",),
        ]
    )

    assert assert_no_unexpected_no_rls_tables(db) == []
    assert db.executed_sql


def test_assert_no_unexpected_no_rls_tables_fails_for_new_tenant_scoped_table():
    from app.tenancy.rls_no_debt import assert_no_unexpected_no_rls_tables

    db = _FakeDb([("clientes",), ("user_sessions",)])

    with pytest.raises(RuntimeError, match="clientes"):
        assert_no_unexpected_no_rls_tables(db)


def test_cli_script_uses_same_no_debt_guard():
    script = Path(__file__).resolve().parents[2] / "scripts" / "check_rls_no_debt.py"

    assert script.exists()
    source = script.read_text(encoding="utf-8")
    assert "assert_no_unexpected_no_rls_tables" in source
    assert "SessionLocal" in source


class _FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.executed_sql = None

    def execute(self, statement):
        self.executed_sql = str(statement)
        return SimpleNamespace(all=lambda: self.rows)
