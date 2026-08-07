import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import text

from app.config import settings
from app.ecommerceai_integration_models import (
    EcommerceAIConnection,
    EcommerceAIConnectionRequest,
)
from app.produtos_models import Produto, ProdutoKitComponente
from app.routes.ecommerceai_integration_routes import _serialize_product, _signature


TEST_SECRET = "corepet-ecommerceai-test-secret-with-32-chars"


def _signed_headers(body: bytes, nonce: str = "nonce-for-contract-test") -> dict[str, str]:
    timestamp_value = str(int(time.time()))
    return {
        "X-Integration-Timestamp": timestamp_value,
        "X-Integration-Nonce": nonce,
        "X-Integration-Signature": _signature(
            TEST_SECRET, timestamp_value, nonce, body
        ),
        "Content-Type": "application/json",
    }


def test_connection_request_requires_hmac_and_rejects_replay(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "ECOMMERCEAI_INTEGRATION_BOOTSTRAP_SECRET", TEST_SECRET)
    monkeypatch.setattr(
        settings,
        "ECOMMERCEAI_CALLBACK_ALLOWED_ORIGINS",
        "https://api.ecommerceai.com.br",
    )
    payload = {
        "client_id": "ecommerceai",
        "ecommerceai_user_id": "42",
        "account_name": "Conta teste",
        "account_email": "teste@example.com",
        "callback_url": "https://api.ecommerceai.com.br/api/v1/integrations/corepet/callback",
        "state": "state-with-more-than-thirty-two-random-characters",
        "requested_scopes": ["catalog:read", "events:write"],
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    headers = _signed_headers(body)

    response = client.post(
        "/integracoes/ecommerceai/requests", content=body, headers=headers
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert db_session.execute(
        text("SELECT COUNT(*) FROM ecommerceai_connection_requests")
    ).scalar_one() == 1

    replay = client.post(
        "/integracoes/ecommerceai/requests", content=body, headers=headers
    )
    assert replay.status_code == 409


def test_event_delivery_is_idempotent(client, db_session):
    tenant_id = uuid4()
    raw_token = "cp_eai_" + "x" * 48
    request_id = str(uuid4())
    request = EcommerceAIConnectionRequest(
        request_id=request_id,
        request_nonce="event-test-nonce",
        client_id="ecommerceai",
        ecommerceai_user_id="77",
        callback_url="https://api.ecommerceai.com.br/api/v1/integrations/corepet/callback",
        state="state-for-event-test-with-thirty-two-characters",
        requested_scopes=["events:write"],
        status="approved",
        tenant_id=tenant_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    connection = EcommerceAIConnection(
        public_id=str(uuid4()),
        request_id=request_id,
        tenant_id=tenant_id,
        ecommerceai_user_id="77",
        status="connected",
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        token_prefix=raw_token[:16],
        scopes=["events:write"],
        connected_at=datetime.now(timezone.utc),
    )
    db_session.add_all([request, connection])
    db_session.commit()
    event = {
        "event_id": str(uuid4()),
        "event_type": "integration.test",
        "schema_version": "1.0",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "payload": {"message": "teste"},
    }
    headers = {"Authorization": f"Bearer {raw_token}"}

    first = client.post(
        "/integracoes/ecommerceai/events", json=event, headers=headers
    )
    duplicate = client.post(
        "/integracoes/ecommerceai/events", json=event, headers=headers
    )

    assert first.status_code == 202
    assert first.json()["status"] == "processed"
    assert duplicate.status_code == 202
    assert duplicate.json()["duplicate"] is True
    assert db_session.execute(
        text("SELECT COUNT(*) FROM ecommerceai_inbound_events")
    ).scalar_one() == 1


def test_product_payload_includes_cost_supplier_and_kit_composition():
    tenant_id = uuid4()
    product = Produto(
        id=10,
        tenant_id=tenant_id,
        user_id=5,
        codigo="KIT-001",
        nome="Kit teste",
        tipo_produto="KIT",
        preco_custo=42.5,
        preco_venda=79.9,
    )
    component = ProdutoKitComponente(
        id=20,
        tenant_id=tenant_id,
        kit_id=10,
        produto_componente_id=11,
        quantidade=2,
    )
    product.componentes_kit = [component]

    payload = _serialize_product(product, include_related=True)

    assert payload["preco_custo"] == 42.5
    assert payload["preco_venda"] == 79.9
    assert payload["sku"] == "KIT-001"
    assert payload["fornecedor_nome"] is None
    assert payload["componentes_kit"][0]["produto_componente_id"] == 11
    assert "tenant_id" not in payload
    assert "user_id" not in payload
