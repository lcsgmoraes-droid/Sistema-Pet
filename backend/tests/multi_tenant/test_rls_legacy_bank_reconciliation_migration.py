from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("ql20260612a1_rls_legacy_bank_reconciliation_tables.py")

LEGACY_BANK_RECONCILIATION_RLS_TABLES = (
    "extratos_bancarios",
    "movimentacoes_bancarias",
    "regras_conciliacao",
    "provisoes_automaticas",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        LEGACY_BANK_RECONCILIATION_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_legacy_bank_reconciliation_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="ql20260612a1",
        down_revision="qk20260611a1",
        table_constant="LEGACY_BANK_RECONCILIATION_RLS_TABLES",
        table_names=LEGACY_BANK_RECONCILIATION_RLS_TABLES,
    )


def test_legacy_bank_reconciliation_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        LEGACY_BANK_RECONCILIATION_RLS_TABLES,
    )


def test_legacy_bank_reconciliation_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = "\n".join(
        _capture(
            monkeypatch,
            "upgrade",
            existing=("movimentacoes_bancarias", "regras_conciliacao"),
        )
    )

    assert "movimentacoes_bancarias" in emitted
    assert "regras_conciliacao" in emitted
    assert "extratos_bancarios" not in emitted
    assert "provisoes_automaticas" not in emitted


def test_legacy_bank_reconciliation_rls_downgrade_unwinds_in_reverse_order(
    monkeypatch,
):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        LEGACY_BANK_RECONCILIATION_RLS_TABLES,
    )


def test_legacy_bank_reconciliation_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
