from uuid import uuid4

from app.domain.opportunity_events import OpportunityEventType, OpportunityType
from app.schemas.opportunity_events import OpportunityEventPayload
from app.services import opportunity_event_service, opportunity_metrics_service
from app.opportunity_events_models import OpportunityEventTypeEnum


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows=None):
        self.added = []
        self.closed = False
        self.committed = False
        self.rows = rows or []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True

    def execute(self, _query):
        return _FakeResult(self.rows)


def test_opportunity_event_persistence_sets_and_clears_rls_tenant(monkeypatch):
    tenant_id = uuid4()
    fake_session = _FakeSession()
    calls = []
    payload = OpportunityEventPayload(
        tenant_id=tenant_id,
        oportunidade_id=uuid4(),
        tipo=OpportunityType.CROSS_SELL,
        produto_sugerido_id=123,
        event_type=OpportunityEventType.OPORTUNIDADE_CONVERTIDA,
        user_id=7,
    )

    monkeypatch.setattr(opportunity_event_service, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(opportunity_event_service, "set_current_tenant", lambda value: calls.append(("set", value)))
    monkeypatch.setattr(opportunity_event_service, "clear_current_tenant", lambda: calls.append(("clear", None)))

    assert opportunity_event_service._persist_event(payload, "evt_test") is True

    assert calls == [("set", tenant_id), ("clear", None)]
    assert fake_session.committed is True
    assert fake_session.closed is True
    assert fake_session.added[0].tenant_id == tenant_id
    assert fake_session.added[0].extra_data["produto_sugerido_id"] == 123


def test_opportunity_metrics_sets_and_clears_rls_tenant(monkeypatch):
    tenant_id = uuid4()
    fake_session = _FakeSession(rows=[(OpportunityEventTypeEnum.CONVERTIDA, 2)])
    calls = []

    monkeypatch.setattr(opportunity_metrics_service, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(opportunity_metrics_service, "set_current_tenant", lambda value: calls.append(("set", value)))
    monkeypatch.setattr(opportunity_metrics_service, "clear_current_tenant", lambda: calls.append(("clear", None)))

    assert opportunity_metrics_service.count_events_by_type(tenant_id) == {
        "oportunidade_convertida": 2
    }

    assert calls == [("set", tenant_id), ("clear", None)]
    assert fake_session.closed is True
