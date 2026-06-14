from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("tk20260614a1_rls_read_models.py")

READ_MODEL_RLS_TABLES = (
    "read_vendas_resumo_diario",
    "read_performance_parceiro",
    "read_receita_mensal",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        READ_MODEL_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_read_models_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="tk20260614a1",
        down_revision="tj20260614a1",
        table_constant="READ_MODEL_RLS_TABLES",
        table_names=READ_MODEL_RLS_TABLES,
    )


def test_read_models_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        READ_MODEL_RLS_TABLES,
    )


def test_read_models_rls_upgrade_skips_missing_tables(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_read_models_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        READ_MODEL_RLS_TABLES,
    )


def test_read_models_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
