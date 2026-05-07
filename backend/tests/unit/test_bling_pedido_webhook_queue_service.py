from app.services.bling_pedido_webhook_queue_service import _backoff_seconds, _extract_metadata


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
