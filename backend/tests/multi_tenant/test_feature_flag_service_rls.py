from types import SimpleNamespace
from uuid import UUID

from app.services import feature_flag_service


TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")


class _FakeQuery:
    def __init__(self, events, first_result=None, all_result=None):
        self._events = events
        self._first_result = first_result
        self._all_result = all_result if all_result is not None else []

    def filter(self, *conditions):
        self._conditions = conditions
        return self

    def first(self):
        return self._first_result

    def all(self):
        return self._all_result


class _FakeDB:
    def __init__(self, events, first_result=None, all_result=None):
        self.events = events
        self.first_result = first_result
        self.all_result = all_result
        self.added = None
        self.committed = False
        self.refreshed = None

    def query(self, _model):
        self.events.append("query")
        return _FakeQuery(self.events, self.first_result, self.all_result)

    def add(self, obj):
        self.added = obj

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed = obj


def _capture_rls_sync(monkeypatch, events):
    def fake_sync_rls_tenant(db, tenant_id):
        events.append(("sync", db, tenant_id))
        return True

    monkeypatch.setattr(
        feature_flag_service, "sync_rls_tenant", fake_sync_rls_tenant, raising=False
    )


def test_is_feature_enabled_syncs_explicit_tenant_before_query(monkeypatch):
    events = []
    db = _FakeDB(events, first_result=SimpleNamespace(enabled=True))
    feature_flag_service.clear_cache()
    _capture_rls_sync(monkeypatch, events)

    assert (
        feature_flag_service.is_feature_enabled(
            db, TENANT_ID, "PDV_IA_OPORTUNIDADES", use_cache=False
        )
        is True
    )

    assert events[:2] == [("sync", db, TENANT_ID), "query"]


def test_set_feature_flag_syncs_explicit_tenant_before_upsert(monkeypatch):
    events = []
    db = _FakeDB(events, first_result=None)
    _capture_rls_sync(monkeypatch, events)

    feature_flag = feature_flag_service.set_feature_flag(
        db, TENANT_ID, "PDV_IA_OPORTUNIDADES", True
    )

    assert events[:2] == [("sync", db, TENANT_ID), "query"]
    assert db.added is feature_flag
    assert db.committed is True
    assert db.refreshed is feature_flag
    assert feature_flag.tenant_id == TENANT_ID
    assert feature_flag.enabled is True


def test_get_all_feature_flags_syncs_explicit_tenant_before_query(monkeypatch):
    events = []
    db = _FakeDB(
        events,
        all_result=[
            SimpleNamespace(feature_key="PDV_IA_OPORTUNIDADES", enabled=True),
            SimpleNamespace(feature_key="OUTRA_FLAG", enabled=False),
        ],
    )
    _capture_rls_sync(monkeypatch, events)

    flags = feature_flag_service.get_all_feature_flags(db, TENANT_ID)

    assert events[:2] == [("sync", db, TENANT_ID), "query"]
    assert flags == {"PDV_IA_OPORTUNIDADES": True, "OUTRA_FLAG": False}
