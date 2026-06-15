from types import SimpleNamespace


class FakeConnection:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), dict(params or {})))


class FakeSession:
    def __init__(self, dialect_name):
        self.bind = SimpleNamespace(
            dialect=SimpleNamespace(name=dialect_name),
        )
        self.connection_obj = FakeConnection()

    def get_bind(self):
        return self.bind

    def connection(self):
        return self.connection_obj


def test_rls_auth_user_sync_sets_transaction_local_user_id_on_postgresql():
    from app.tenancy.rls import RLS_AUTH_USER_SETTING, sync_rls_auth_user

    session = FakeSession("postgresql")

    assert sync_rls_auth_user(session, 123) is True

    assert session.connection_obj.calls == [
        (
            "SELECT set_config(:setting_name, :setting_value, true)",
            {
                "setting_name": RLS_AUTH_USER_SETTING,
                "setting_value": "123",
            },
        )
    ]


def test_rls_auth_email_sync_sets_normalized_email_on_postgresql():
    from app.tenancy.rls import RLS_AUTH_EMAIL_SETTING, sync_rls_auth_email

    session = FakeSession("postgresql")

    assert sync_rls_auth_email(session, " USER@Example.COM ") is True

    assert session.connection_obj.calls == [
        (
            "SELECT set_config(:setting_name, :setting_value, true)",
            {
                "setting_name": RLS_AUTH_EMAIL_SETTING,
                "setting_value": "user@example.com",
            },
        )
    ]


def test_rls_auth_sync_clears_empty_values():
    from app.tenancy.rls import RLS_AUTH_EMAIL_SETTING, RLS_AUTH_USER_SETTING
    from app.tenancy.rls import sync_rls_auth_email, sync_rls_auth_user

    session = FakeSession("postgresql")

    assert sync_rls_auth_user(session, None) is True
    assert sync_rls_auth_email(session, "") is True

    assert session.connection_obj.calls == [
        (
            "SELECT set_config(:setting_name, :setting_value, true)",
            {
                "setting_name": RLS_AUTH_USER_SETTING,
                "setting_value": "",
            },
        ),
        (
            "SELECT set_config(:setting_name, :setting_value, true)",
            {
                "setting_name": RLS_AUTH_EMAIL_SETTING,
                "setting_value": "",
            },
        ),
    ]


def test_rls_auth_sync_is_noop_outside_postgresql():
    from app.tenancy.rls import sync_rls_auth_email, sync_rls_auth_user

    session = FakeSession("sqlite")

    assert sync_rls_auth_user(session, 123) is False
    assert sync_rls_auth_email(session, "user@example.com") is False
    assert session.connection_obj.calls == []
