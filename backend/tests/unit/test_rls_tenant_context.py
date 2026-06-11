from types import SimpleNamespace
from uuid import UUID

import pytest

from app.tenancy.context import clear_current_tenant, set_current_tenant


TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")


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


@pytest.fixture(autouse=True)
def _clear_tenant_context():
    clear_current_tenant()
    yield
    clear_current_tenant()


def test_rls_sync_sets_transaction_local_tenant_on_postgresql():
    from app.tenancy.rls import RLS_TENANT_SETTING, sync_rls_tenant

    session = FakeSession("postgresql")
    set_current_tenant(TENANT_ID)

    assert sync_rls_tenant(session) is True

    assert session.connection_obj.calls == [
        (
            "SELECT set_config(:setting_name, :setting_value, true)",
            {
                "setting_name": RLS_TENANT_SETTING,
                "setting_value": str(TENANT_ID),
            },
        )
    ]


def test_rls_sync_clears_transaction_local_tenant_without_context():
    from app.tenancy.rls import RLS_TENANT_SETTING, sync_rls_tenant

    session = FakeSession("postgresql")

    assert sync_rls_tenant(session) is True

    assert session.connection_obj.calls == [
        (
            "SELECT set_config(:setting_name, :setting_value, true)",
            {
                "setting_name": RLS_TENANT_SETTING,
                "setting_value": "",
            },
        )
    ]


def test_rls_sync_explicit_none_clears_even_with_python_context():
    from app.tenancy.rls import RLS_TENANT_SETTING, sync_rls_tenant

    session = FakeSession("postgresql")
    set_current_tenant(TENANT_ID)

    assert sync_rls_tenant(session, tenant_id=None) is True

    assert session.connection_obj.calls == [
        (
            "SELECT set_config(:setting_name, :setting_value, true)",
            {
                "setting_name": RLS_TENANT_SETTING,
                "setting_value": "",
            },
        )
    ]


def test_rls_sync_is_noop_outside_postgresql():
    from app.tenancy.rls import sync_rls_tenant

    session = FakeSession("sqlite")
    set_current_tenant(TENANT_ID)

    assert sync_rls_tenant(session) is False
    assert session.connection_obj.calls == []


def test_tenant_filter_syncs_rls_before_applying_orm_filter(monkeypatch):
    import app.tenancy.filters as filters

    calls = []
    fake_session = object()

    def fake_sync(session, tenant_id=None):
        calls.append((session, tenant_id))

    monkeypatch.setattr(filters, "sync_rls_tenant", fake_sync)

    class FakeStatement:
        def options(self, *args, **kwargs):
            return self

    execute_state = SimpleNamespace(
        is_select=True,
        session=fake_session,
        statement=FakeStatement(),
    )
    set_current_tenant(TENANT_ID)

    filters._add_tenant_filter(execute_state)

    assert calls == [(fake_session, TENANT_ID)]


def test_tenant_filter_syncs_rls_for_orm_dml(monkeypatch):
    import app.tenancy.filters as filters

    calls = []
    fake_session = object()

    def fake_sync(session, tenant_id=None):
        calls.append((session, tenant_id))

    monkeypatch.setattr(filters, "sync_rls_tenant", fake_sync)

    execute_state = SimpleNamespace(
        is_select=False,
        session=fake_session,
        statement=object(),
    )
    set_current_tenant(TENANT_ID)

    filters._add_tenant_filter(execute_state)

    assert calls == [(fake_session, TENANT_ID)]


def test_rls_before_flush_hook_syncs_current_tenant(monkeypatch):
    import app.tenancy.rls as rls

    calls = []
    fake_session = object()

    def fake_sync(session, tenant_id=None):
        calls.append((session, tenant_id))

    monkeypatch.setattr(rls, "sync_rls_tenant", fake_sync)
    set_current_tenant(TENANT_ID)

    rls._sync_rls_before_flush(fake_session, flush_context=object(), instances=None)

    assert calls == [(fake_session, TENANT_ID)]
