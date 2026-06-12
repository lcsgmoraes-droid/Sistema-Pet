from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qh20260611a1_rls_conciliation_audit_tables.py")

CONCILIATION_AUDIT_RLS_TABLES = (
    "conciliacao_validacoes",
    "conciliacao_logs",
    "conciliacao_metricas",
    "historico_conciliacao",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        CONCILIATION_AUDIT_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_conciliation_audit_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qh20260611a1",
        down_revision="qg20260611a1",
        table_constant="CONCILIATION_AUDIT_RLS_TABLES",
        table_names=CONCILIATION_AUDIT_RLS_TABLES,
    )


def test_conciliation_audit_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        CONCILIATION_AUDIT_RLS_TABLES,
    )


def test_conciliation_audit_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = "\n".join(
        _capture(
            monkeypatch,
            "upgrade",
            existing=("conciliacao_logs", "historico_conciliacao"),
        )
    )

    assert "conciliacao_logs" in emitted
    assert "historico_conciliacao" in emitted
    assert "conciliacao_validacoes" not in emitted
    assert "conciliacao_metricas" not in emitted


def test_conciliation_audit_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        CONCILIATION_AUDIT_RLS_TABLES,
    )


def test_conciliation_audit_rls_skips_when_bind_or_tables_are_not_applicable(
    monkeypatch,
):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
