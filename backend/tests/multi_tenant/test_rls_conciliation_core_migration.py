from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qi20260611a1_rls_conciliation_core_tables.py")

CONCILIATION_CORE_RLS_TABLES = (
    "empresa_parametros",
    "arquivos_evidencia",
    "conciliacao_importacoes",
    "conciliacao_lotes",
    "conciliacao_recebimentos",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        CONCILIATION_CORE_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_conciliation_core_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qi20260611a1",
        down_revision="qh20260611a1",
        table_constant="CONCILIATION_CORE_RLS_TABLES",
        table_names=CONCILIATION_CORE_RLS_TABLES,
    )


def test_conciliation_core_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        CONCILIATION_CORE_RLS_TABLES,
    )


def test_conciliation_core_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = "\n".join(
        _capture(
            monkeypatch,
            "upgrade",
            existing=("empresa_parametros", "conciliacao_recebimentos"),
        )
    )

    assert "empresa_parametros" in emitted
    assert "conciliacao_recebimentos" in emitted
    assert "arquivos_evidencia" not in emitted
    assert "conciliacao_importacoes" not in emitted
    assert "conciliacao_lotes" not in emitted


def test_conciliation_core_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        CONCILIATION_CORE_RLS_TABLES,
    )


def test_conciliation_core_rls_skips_when_bind_or_tables_are_not_applicable(
    monkeypatch,
):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
