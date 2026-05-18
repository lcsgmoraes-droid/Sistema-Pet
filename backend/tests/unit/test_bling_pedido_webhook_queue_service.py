from datetime import datetime, timedelta, timezone

from app.services.bling_pedido_webhook_queue_service import (
    STATUS_DEAD,
    _backoff_seconds,
    _extract_metadata,
    _mark_exhausted_processing_events_dead,
)


class _FakeQuery:
    def __init__(self, updated_rows=0):
        self.updated_rows = updated_rows
        self.filters = []
        self.update_values = None
        self.synchronize_session = None

    def filter(self, *criteria):
        self.filters.extend(criteria)
        return self

    def update(self, values, synchronize_session=False):
        self.update_values = values
        self.synchronize_session = synchronize_session
        return self.updated_rows


class _FakeDb:
    def __init__(self, query):
        self.query_obj = query
        self.queried_model = None
        self.commits = 0

    def query(self, model):
        self.queried_model = model
        return self.query_obj

    def commit(self):
        self.commits += 1


def test_extract_metadata_uses_event_id_as_dedupe_key():
    payload = {"eventId": "evt-123", "event": "order.created", "data": {"id": 987}}

    metadata = _extract_metadata(payload)

    assert metadata["dedupe_key"] == "event:evt-123"
    assert metadata["event_id"] == "evt-123"
    assert metadata["event_type"] == "order.created"
    assert metadata["pedido_bling_id"] == "987"


def test_extract_metadata_without_event_id_is_payload_stable():
    payload_a = {"event": "order.updated", "data": {"id": 987, "situacao": {"id": 9}}}
    payload_b = {"data": {"situacao": {"id": 9}, "id": 987}, "event": "order.updated"}

    metadata_a = _extract_metadata(payload_a)
    metadata_b = _extract_metadata(payload_b)

    assert metadata_a["dedupe_key"].startswith("payload:")
    assert metadata_a["dedupe_key"] == metadata_b["dedupe_key"]


def test_backoff_uses_exponential_cap(monkeypatch):
    monkeypatch.setenv("BLING_PEDIDO_WEBHOOK_RETRY_BASE_SECONDS", "10")
    monkeypatch.setenv("BLING_PEDIDO_WEBHOOK_RETRY_MAX_SECONDS", "25")

    assert _backoff_seconds(1) == 10
    assert _backoff_seconds(2) == 20
    assert _backoff_seconds(3) == 25


def test_mark_exhausted_processing_events_dead_commits_updated_rows():
    now = datetime(2026, 5, 18, 13, 30, tzinfo=timezone.utc)
    fake_query = _FakeQuery(updated_rows=3)
    fake_db = _FakeDb(fake_query)

    updated = _mark_exhausted_processing_events_dead(
        fake_db,
        stale_after=now - timedelta(minutes=10),
        now=now,
    )

    assert updated == 3
    assert fake_db.commits == 1
    assert fake_query.update_values["status"] == STATUS_DEAD
    assert fake_query.update_values["updated_at"] == now
    assert "max_attempts" in fake_query.update_values["last_error"]
    assert fake_query.synchronize_session is False
