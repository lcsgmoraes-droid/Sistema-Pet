from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.audit_event_report_service import (
    audit_row_matches_request_id,
    extract_request_id_from_audit_payload,
    row_to_audit_event,
)


def test_extract_request_id_from_audit_payload_finds_nested_metadata():
    payload = {
        "event": "sale_coupon_redeemed",
        "metadata": {
            "request": {
                "request_id": "req-sale-123",
            },
        },
    }

    assert extract_request_id_from_audit_payload(payload) == "req-sale-123"


def test_row_to_audit_event_prefers_details_request_id_and_parses_json_fields():
    tenant_id = uuid4()
    row = SimpleNamespace(
        id=42,
        tenant_id=tenant_id,
        user_id=7,
        action="sale_reopened",
        entity_type="sale",
        entity_id=123,
        old_value='{"manual_discount": 10}',
        new_value='{"request_id": "req-new-ignored"}',
        details='{"request_id": "req-detail-456", "path": "/vendas/123/reabrir"}',
        ip_address="127.0.0.1",
        user_agent="pytest",
        timestamp=datetime(2026, 5, 16, 20, 5, tzinfo=timezone.utc),
    )

    item = row_to_audit_event(row)

    assert item["request_id"] == "req-detail-456"
    assert item["tenant_id"] == str(tenant_id)
    assert item["old_value"] == {"manual_discount": 10}
    assert item["new_value"] == {"request_id": "req-new-ignored"}
    assert item["details"]["path"] == "/vendas/123/reabrir"


def test_audit_row_matches_request_id_requires_exact_payload_match():
    row = SimpleNamespace(
        old_value=None,
        new_value='{"request_id": "req-exact"}',
        details='{"message": "related req-exact-suffix text"}',
    )

    assert audit_row_matches_request_id(row, "req-exact") is True
    assert audit_row_matches_request_id(row, "req-exact-suffix") is False
