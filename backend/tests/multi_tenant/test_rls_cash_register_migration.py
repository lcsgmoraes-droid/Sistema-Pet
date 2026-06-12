from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qp20260612a1_rls_cash_register_tables.py")

CASH_REGISTER_RLS_TABLES = (
    "caixas",
    "movimentacoes_caixa",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        CASH_REGISTER_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_cash_register_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qp20260612a1",
        down_revision="qo20260612a1",
        table_constant="CASH_REGISTER_RLS_TABLES",
        table_names=CASH_REGISTER_RLS_TABLES,
    )


def test_cash_register_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        CASH_REGISTER_RLS_TABLES,
    )


def test_cash_register_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = "\n".join(
        _capture(
            monkeypatch,
            "upgrade",
            existing=("caixas",),
        )
    )

    assert "caixas" in emitted
    assert "movimentacoes_caixa" not in emitted


def test_cash_register_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        CASH_REGISTER_RLS_TABLES,
    )


def test_cash_register_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
