from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from app.routers.whatsapp_handoff import _serialize_handoff


def test_serialize_handoff_returns_frontend_expected_fields():
    handoff = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        session_id=uuid4(),
        phone_number="5511999999999",
        customer_name=None,
        reason="manual_request",
        reason_details="Pedido explicito por humano",
        priority="high",
        status="pending",
        assigned_to=None,
        assigned_at=None,
        resolved_at=None,
        resolution_notes=None,
        rating=None,
        rating_feedback=None,
        created_at=datetime(2026, 3, 17, 4, 14, 20),
        updated_at=datetime(2026, 3, 17, 4, 14, 21),
    )

    result = _serialize_handoff(handoff)

    assert result["phone_number"] == "5511999999999"
    assert result["reason"] == "manual_request"
    assert "assigned_agent_id" in result
    assert result["assigned_agent_id"] is None
    assert "assigned_to" not in result