from tests.multi_tenant.rls_migration_helpers import (
    TENANT_RLS_GUARD,
    load_migration,
    migration_path,
    statements_containing,
)


MIGRATION_FILE = migration_path("ua20260621a1_create_user_push_devices.py")
USER_PUSH_DEVICES_RLS_TABLES = ("user_push_devices",)


def _capture(monkeypatch, action_name: str, *, dialect="postgresql", existing=None):
    migration = load_migration(MIGRATION_FILE)
    emitted: list[str] = []
    present = set(USER_PUSH_DEVICES_RLS_TABLES if existing is None else existing)

    class _Dialect:
        name = dialect

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


def test_user_push_devices_migration_metadata_and_rls_scope():
    migration = load_migration(MIGRATION_FILE)

    assert migration["revision"] == "ua20260621a1"
    assert migration["down_revision"] == "tz20260614a1"
    assert migration["USER_PUSH_DEVICES_RLS_TABLES"] == USER_PUSH_DEVICES_RLS_TABLES
    assert migration["TENANT_GUARD"] == TENANT_RLS_GUARD


def test_user_push_devices_upgrade_enables_tenant_rls(monkeypatch):
    emitted = _capture(monkeypatch, "upgrade")

    assert statements_containing(emitted, "INSERT INTO user_push_devices")
    assert statements_containing(emitted, "ENABLE ROW LEVEL SECURITY") == [
        "ALTER TABLE user_push_devices ENABLE ROW LEVEL SECURITY"
    ]
    assert statements_containing(emitted, "FORCE ROW LEVEL SECURITY") == [
        "ALTER TABLE user_push_devices FORCE ROW LEVEL SECURITY"
    ]
    assert len(statements_containing(emitted, f"WITH CHECK ({TENANT_RLS_GUARD})")) == 1


def test_user_push_devices_downgrade_disables_rls_before_drop(monkeypatch):
    emitted = _capture(monkeypatch, "downgrade")

    assert (
        emitted[0]
        == "DROP POLICY IF EXISTS user_push_devices_tenant_isolation ON user_push_devices"
    )
    assert emitted[1] == "ALTER TABLE user_push_devices NO FORCE ROW LEVEL SECURITY"
    assert emitted[2] == "ALTER TABLE user_push_devices DISABLE ROW LEVEL SECURITY"


def test_user_push_devices_rls_skips_when_not_applicable(monkeypatch):
    for kwargs in ({"dialect": "sqlite"}, {"existing": ()}):
        assert _capture(monkeypatch, "upgrade", **kwargs) == [
            """
        INSERT INTO user_push_devices (
            user_id,
            expo_push_token,
            platform,
            device_name,
            enabled,
            last_seen_at,
            tenant_id,
            created_at,
            updated_at
        )
        SELECT
            id,
            push_token,
            'legacy',
            'Dispositivo registrado anteriormente',
            true,
            COALESCE(updated_at, created_at, now()),
            tenant_id,
            now(),
            now()
        FROM users
        WHERE push_token IS NOT NULL
          AND btrim(push_token) <> ''
        ON CONFLICT ON CONSTRAINT uq_user_push_devices_tenant_user_token DO NOTHING
        """
        ]
        assert _capture(monkeypatch, "downgrade", **kwargs) == []
