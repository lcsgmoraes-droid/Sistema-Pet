from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qk20260611a1_rls_legacy_acquirer_templates_table.py")

LEGACY_ACQUIRER_TEMPLATE_RLS_TABLES = ("templates_adquirentes",)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        LEGACY_ACQUIRER_TEMPLATE_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_legacy_acquirer_templates_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qk20260611a1",
        down_revision="qj20260611a1",
        table_constant="LEGACY_ACQUIRER_TEMPLATE_RLS_TABLES",
        table_names=LEGACY_ACQUIRER_TEMPLATE_RLS_TABLES,
    )


def test_legacy_acquirer_templates_rls_upgrade_targets_declared_table(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        LEGACY_ACQUIRER_TEMPLATE_RLS_TABLES,
    )


def test_legacy_acquirer_templates_rls_upgrade_skips_missing_table(monkeypatch):
    assert _capture(monkeypatch, "upgrade", existing=()) == []


def test_legacy_acquirer_templates_rls_downgrade_unwinds_declared_table(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        LEGACY_ACQUIRER_TEMPLATE_RLS_TABLES,
    )


def test_legacy_acquirer_templates_rls_skips_when_dialect_is_not_postgresql(
    monkeypatch,
):
    assert _capture(monkeypatch, "upgrade", dialect="sqlite") == []
    assert _capture(monkeypatch, "downgrade", dialect="sqlite") == []
