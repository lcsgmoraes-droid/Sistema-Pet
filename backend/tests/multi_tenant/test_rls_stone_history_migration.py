from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    capture_migration_sql,
    migration_path,
)


MIGRATION_FILE = migration_path("qx20260612a1_rls_stone_history_tables.py")

STONE_HISTORY_RLS_TABLES = (
    "stone_transactions",
    "stone_transaction_logs",
    "stone_configs",
)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    return capture_migration_sql(
        monkeypatch,
        MIGRATION_FILE,
        action_name,
        STONE_HISTORY_RLS_TABLES,
        dialect=dialect,
        existing=existing,
    )


def test_stone_history_rls_migration_metadata_and_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="qx20260612a1",
        down_revision="qw20260612a1",
        table_constant="STONE_HISTORY_RLS_TABLES",
        table_names=STONE_HISTORY_RLS_TABLES,
    )


def test_stone_history_rls_upgrade_targets_declared_tables(monkeypatch):
    assert_upgrade_emits_rls_for_declared_tables(
        _capture(monkeypatch, "upgrade"),
        STONE_HISTORY_RLS_TABLES,
    )


def test_stone_history_rls_upgrade_skips_missing_tables(monkeypatch):
    emitted = "\n".join(
        _capture(
            monkeypatch,
            "upgrade",
            existing=("stone_transactions", "stone_configs"),
        )
    )

    assert "stone_transactions" in emitted
    assert "stone_configs" in emitted
    assert "stone_transaction_logs" not in emitted


def test_stone_history_rls_downgrade_unwinds_in_reverse_order(monkeypatch):
    assert_downgrade_unwinds_in_reverse_order(
        _capture(monkeypatch, "downgrade"),
        STONE_HISTORY_RLS_TABLES,
    )


def test_stone_history_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == []
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
