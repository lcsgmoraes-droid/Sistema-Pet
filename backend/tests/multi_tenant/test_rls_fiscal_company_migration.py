from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qg20260611a1_rls_fiscal_company_tables.py")

FISCAL_COMPANY_RLS_TABLES = (
    "empresa_config_fiscal",
    "simples_nacional_mensal",
)

def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        FISCAL_COMPANY_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_fiscal_company_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qg20260611a1",
        down_revision="qf20260611a1",
        table_constant="FISCAL_COMPANY_RLS_TABLES",
        table_names=FISCAL_COMPANY_RLS_TABLES,
    )


def test_fiscal_company_rls_upgrade_targets_existing_tables_in_declared_order(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        FISCAL_COMPANY_RLS_TABLES,
    )


def test_fiscal_company_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = _capture(monkeypatch, "upgrade", existing=("empresa_config_fiscal",))
    emitted_sql = "\n".join(emitted)

    assert "empresa_config_fiscal" in emitted_sql
    assert "simples_nacional_mensal" not in emitted_sql


def test_fiscal_company_rls_downgrade_unwinds_existing_tables_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        FISCAL_COMPANY_RLS_TABLES,
    )


def test_fiscal_company_rls_migration_skips_when_bind_or_tables_are_not_applicable(
    monkeypatch,
):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
