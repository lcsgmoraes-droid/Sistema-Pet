from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("to20260614a1_rls_extrato_importacao.py")

EXTRATO_IMPORTACAO_RLS_TABLES = (
    "arquivos_extrato_importados",
    "lancamentos_importados",
    "padroes_categorizacao_ia",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        EXTRATO_IMPORTACAO_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_extrato_importacao_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="to20260614a1",
        down_revision="tn20260614a1",
        table_constant="EXTRATO_IMPORTACAO_RLS_TABLES",
        table_names=EXTRATO_IMPORTACAO_RLS_TABLES,
    )


def test_extrato_importacao_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        EXTRATO_IMPORTACAO_RLS_TABLES,
    )


def test_extrato_importacao_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_extrato_importacao_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        EXTRATO_IMPORTACAO_RLS_TABLES,
    )


def test_extrato_importacao_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
