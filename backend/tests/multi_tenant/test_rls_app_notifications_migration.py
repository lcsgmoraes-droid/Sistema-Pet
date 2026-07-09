from tests.multi_tenant.rls_migration_helpers import (
    assert_downgrade_unwinds_in_reverse_order,
    assert_rls_migration_metadata,
    assert_upgrade_emits_rls_for_declared_tables,
    migration_path,
)


MIGRATION_FILE = migration_path("zwd20260708a1_create_app_notifications.py")
APP_NOTIFICATIONS_RLS_TABLES = ("app_notifications",)


def _capture(monkeypatch, action_name: str):
    migration = __import__("runpy").run_path(str(MIGRATION_FILE))
    emitted: list[str] = []
    present = set(APP_NOTIFICATIONS_RLS_TABLES)

    class _Dialect:
        name = "postgresql"

    class _Bind:
        dialect = _Dialect()

    class _Inspector:
        def has_table(self, table_name: str) -> bool:
            return table_name in present

    monkeypatch.setattr(migration["op"], "create_table", lambda *_, **__: None)
    monkeypatch.setattr(migration["op"], "create_index", lambda *_, **__: None)
    monkeypatch.setattr(migration["op"], "drop_index", lambda *_, **__: None)
    monkeypatch.setattr(migration["op"], "drop_table", lambda *_, **__: None)
    monkeypatch.setattr(
        migration["op"], "execute", lambda sql: emitted.append(str(sql))
    )
    monkeypatch.setattr(migration["op"], "get_bind", lambda: _Bind())
    monkeypatch.setattr(migration["sa"], "inspect", lambda _bind: _Inspector())

    migration[action_name]()
    return emitted


def test_app_notifications_migration_metadata_and_rls_scope():
    assert_rls_migration_metadata(
        MIGRATION_FILE,
        revision="zwd20260708a1",
        down_revision="zwc20260703a1",
        table_constant="APP_NOTIFICATIONS_RLS_TABLES",
        table_names=APP_NOTIFICATIONS_RLS_TABLES,
    )


def test_app_notifications_upgrade_enables_tenant_rls(monkeypatch):
    emitted = _capture(monkeypatch, "upgrade")

    assert_upgrade_emits_rls_for_declared_tables(
        emitted,
        APP_NOTIFICATIONS_RLS_TABLES,
    )


def test_app_notifications_downgrade_disables_rls_before_drop(monkeypatch):
    emitted = _capture(monkeypatch, "downgrade")

    assert_downgrade_unwinds_in_reverse_order(
        emitted,
        APP_NOTIFICATIONS_RLS_TABLES,
    )
