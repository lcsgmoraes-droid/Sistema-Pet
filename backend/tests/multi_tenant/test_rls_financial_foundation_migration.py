from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qm20260612a1_rls_financial_foundation_tables.py")

FINANCIAL_FOUNDATION_RLS_TABLES = (
    "contas_bancarias",
    "categorias_financeiras",
    "tipo_despesas",
    "formas_pagamento_taxas",
    "configuracao_impostos",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        FINANCIAL_FOUNDATION_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_financial_foundation_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qm20260612a1",
        down_revision="ql20260612a1",
        table_constant="FINANCIAL_FOUNDATION_RLS_TABLES",
        table_names=FINANCIAL_FOUNDATION_RLS_TABLES,
    )


def test_financial_foundation_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        FINANCIAL_FOUNDATION_RLS_TABLES,
    )


def test_financial_foundation_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = "\n".join(
        _capture(
            monkeypatch,
            "upgrade",
            existing=("contas_bancarias", "tipo_despesas"),
        )
    )

    assert "contas_bancarias" in emitted
    assert "tipo_despesas" in emitted
    assert "categorias_financeiras" not in emitted
    assert "formas_pagamento_taxas" not in emitted
    assert "configuracao_impostos" not in emitted


def test_financial_foundation_rls_downgrade_unwinds_in_reverse_order(
    monkeypatch,
):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        FINANCIAL_FOUNDATION_RLS_TABLES,
    )


def test_financial_foundation_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
