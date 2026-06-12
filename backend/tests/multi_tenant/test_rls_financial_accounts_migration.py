from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qo20260612a1_rls_financial_accounts_tables.py")

FINANCIAL_ACCOUNTS_RLS_TABLES = (
    "contas_pagar",
    "contas_receber",
    "pagamentos",
    "recebimentos",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        FINANCIAL_ACCOUNTS_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_financial_accounts_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qo20260612a1",
        down_revision="qn20260612a1",
        table_constant="FINANCIAL_ACCOUNTS_RLS_TABLES",
        table_names=FINANCIAL_ACCOUNTS_RLS_TABLES,
    )


def test_financial_accounts_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        FINANCIAL_ACCOUNTS_RLS_TABLES,
    )


def test_financial_accounts_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = "\n".join(
        _capture(
            monkeypatch,
            "upgrade",
            existing=("contas_pagar", "recebimentos"),
        )
    )

    assert "contas_pagar" in emitted
    assert "recebimentos" in emitted
    assert "contas_receber" not in emitted
    assert "pagamentos" not in emitted


def test_financial_accounts_rls_downgrade_unwinds_in_reverse_order(
    monkeypatch,
):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        FINANCIAL_ACCOUNTS_RLS_TABLES,
    )


def test_financial_accounts_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
