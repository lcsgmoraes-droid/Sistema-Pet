from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qr20260612a1_rls_lgpd_ecommerce_notify_tables.py")

LGPD_ECOMMERCE_NOTIFY_RLS_TABLES = (
    "data_subject_requests",
    "ecommerce_notify_requests",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        LGPD_ECOMMERCE_NOTIFY_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_lgpd_ecommerce_notify_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qr20260612a1",
        down_revision="qq20260612a1",
        table_constant="LGPD_ECOMMERCE_NOTIFY_RLS_TABLES",
        table_names=LGPD_ECOMMERCE_NOTIFY_RLS_TABLES,
    )


def test_lgpd_ecommerce_notify_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        LGPD_ECOMMERCE_NOTIFY_RLS_TABLES,
    )


def test_lgpd_ecommerce_notify_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = "\n".join(
        _capture(
            monkeypatch,
            "upgrade",
            existing=("ecommerce_notify_requests",),
        )
    )

    assert "ecommerce_notify_requests" in emitted
    assert "data_subject_requests" not in emitted


def test_lgpd_ecommerce_notify_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        LGPD_ECOMMERCE_NOTIFY_RLS_TABLES,
    )


def test_lgpd_ecommerce_notify_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
