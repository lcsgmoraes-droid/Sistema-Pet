from types import SimpleNamespace

import httpx

from app.whatsapp import (
    customer_context_service,
    remote_corepet_client,
    tool_product_search,
)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_remote_catalog_uses_internal_token_without_exposing_it(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return _FakeResponse(
            {
                "success": True,
                "produtos": [{"nome": "Racao Royal Canin"}],
                "total": 1,
            }
        )

    monkeypatch.setenv(
        "COREPET_WHATSAPP_DATA_BASE_URL",
        "https://corepet.com.br/api/internal/whatsapp-orchestrator",
    )
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-test")
    monkeypatch.setattr(remote_corepet_client.httpx, "get", fake_get)

    result = remote_corepet_client.fetch_remote_catalog(
        "tenant-test", "Royal", limite=5
    )

    assert result["total"] == 1
    assert captured["url"].endswith("/tenant-test/catalog-data")
    assert captured["params"] == {"query": "Royal", "limit": 5}
    assert captured["headers"] == {"X-Internal-Token": "token-test"}


def test_remote_order_creation_sends_idempotency_key(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return _FakeResponse({"success": True, "sale_id": 99, "number": "VEN-0099"})

    monkeypatch.setenv(
        "COREPET_WHATSAPP_DATA_BASE_URL",
        "https://corepet.com.br/api/internal/whatsapp-orchestrator",
    )
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-test")
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_WRITE_TOKEN", "write-token-test")
    monkeypatch.setattr(remote_corepet_client.httpx, "post", fake_post)

    result = remote_corepet_client.create_remote_order(
        "tenant-test",
        phone="5518997401641",
        items=[{"product_id": 10, "quantity": 1}],
        fulfillment="pickup",
        payment_method={"key": "pix", "name": "PIX"},
        delivery_address=None,
        cash_change_for=None,
        idempotency_key="checkout-test-1234567890",
    )

    assert result["sale_id"] == 99
    assert captured["url"].endswith("/tenant-test/order-create-data")
    assert captured["headers"] == {
        "X-Internal-Token": "token-test",
        "X-Internal-Write-Token": "write-token-test",
        "Idempotency-Key": "checkout-test-1234567890",
    }
    assert captured["json"]["cash_change_for"] is None


def test_remote_order_preview_preserves_safe_conflict_detail(monkeypatch):
    def fake_post(url, **_kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(
            409,
            request=request,
            json={"detail": "Estoque insuficiente para Racao Special Dog 15kg."},
        )

    monkeypatch.setenv(
        "COREPET_WHATSAPP_DATA_BASE_URL",
        "https://corepet.com.br/api/internal/whatsapp-orchestrator",
    )
    monkeypatch.setenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN", "token-test")
    monkeypatch.setattr(remote_corepet_client.httpx, "post", fake_post)

    result = remote_corepet_client.fetch_remote_order_preview(
        "tenant-test",
        phone="5518997401641",
        items=[{"product_id": 5866, "quantity": 3}],
    )

    assert result == {
        "success": False,
        "status_code": 409,
        "detail": "Estoque insuficiente para Racao Special Dog 15kg.",
    }


def test_remote_customer_is_resolved_without_local_foreign_key(monkeypatch):
    monkeypatch.setattr(
        customer_context_service,
        "remote_data_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        customer_context_service,
        "fetch_remote_customer_context",
        lambda *_args, **_kwargs: {
            "customer": {
                "id": 10563,
                "name": "Lucas Guerra",
                "phone": "18997401641",
                "store_credit": 0,
            },
            "latest_purchase": {
                "number": "202608160001",
                "items": [{"name": "Racao Special Dog 15kg"}],
            },
        },
    )
    session = SimpleNamespace(
        cliente_id=None,
        phone_number="5518997401641",
    )

    customer = customer_context_service.resolve_session_customer(
        None,
        tenant_id="tenant-test",
        session=session,
    )
    purchase = customer_context_service.load_latest_purchase(
        None,
        tenant_id="tenant-test",
        customer_id=customer.id,
    )

    assert customer.id == 10563
    assert customer.nome == "Lucas Guerra"
    assert customer._remote_source is True
    assert purchase["number"] == "202608160001"


def test_remote_catalog_does_not_mix_explicit_product_brands():
    result = tool_product_search._filter_remote_catalog_explicit_brand(
        {
            "success": True,
            "produtos": [
                {
                    "nome": "Racao Bob Dog Gold Premium 15kg",
                    "descricao": "Premium Special",
                },
                {"nome": "Racao Special Dog Gold Adultos 15kg"},
            ],
            "total": 2,
        },
        "Special Dog Gold",
    )

    assert result["total"] == 1
    assert result["produtos"][0]["nome"] == "Racao Special Dog Gold Adultos 15kg"
