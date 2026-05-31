from types import SimpleNamespace

from app.services.mercado_pago_checkout import (
    build_preference_payload,
    create_preference,
    fetch_payment,
)
from app.services.ecommerce_payment_config import (
    build_mercado_pago_webhook_url,
    decrypt_secret,
    encrypt_secret,
    serialize_mercado_pago_config,
)


def _pedido():
    return SimpleNamespace(
        pedido_id="PED-TENANT-001",
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        origem="app",
    )


def test_config_mercado_pago_mascara_segredos_e_expoe_webhook_url(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "tenant-secret-for-tests")
    config = SimpleNamespace(
        enabled=True,
        environment="production",
        public_key="APP_USR-public-key",
        access_token_encrypted=encrypt_secret("APP_USR-access-token"),
        webhook_secret_encrypted=encrypt_secret("webhook-secret"),
        webhook_token="mp_abc123",
        updated_at=None,
    )

    serialized = serialize_mercado_pago_config(
        config,
        base_url="https://corepet.com.br/",
    )

    assert serialized == {
        "provider": "mercadopago",
        "enabled": True,
        "environment": "production",
        "public_key": "APP_USR-public-key",
        "access_token_configured": True,
        "webhook_secret_configured": True,
        "webhook_url": "https://corepet.com.br/api/webhooks/mercadopago/mp_abc123",
        "updated_at": None,
    }
    assert "access_token" not in serialized
    assert "webhook_secret" not in serialized
    assert decrypt_secret(config.access_token_encrypted) == "APP_USR-access-token"


def test_preferencia_usa_webhook_especifico_do_tenant():
    webhook_url = build_mercado_pago_webhook_url(
        "tenant-token",
        base_url="https://corepet.com.br",
    )

    payload = build_preference_payload(
        pedido=_pedido(),
        total=99.9,
        forma_pagamento_tipo="pix",
        endereco_entrega="RETIRADA NA LOJA",
        tipo_retirada="app_loja",
        notification_url=webhook_url,
    )

    assert payload["notification_url"] == (
        "https://corepet.com.br/api/webhooks/mercadopago/tenant-token"
    )
    assert payload["metadata"]["tenant_id"] == "180d9cbf-5dcb-4676-bf11-dcbd91ed444b"


def test_create_preference_usa_access_token_do_tenant(monkeypatch):
    monkeypatch.delenv("MERCADO_PAGO_ACCESS_TOKEN", raising=False)
    captured = {}

    class Response:
        status_code = 201

        @staticmethod
        def json():
            return {
                "id": "pref_123",
                "init_point": "https://mercadopago.com.br/checkout",
                "sandbox_init_point": "https://sandbox.mercadopago.com.br/checkout",
            }

    def http_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return Response()

    preference = create_preference(
        pedido=_pedido(),
        total=10,
        forma_pagamento_tipo="cartao_credito",
        endereco_entrega="Rua Teste, 1",
        tipo_retirada=None,
        access_token="APP_USR-tenant-token",
        notification_url="https://corepet.com.br/api/webhooks/mercadopago/tenant-token",
        use_sandbox=False,
        http_post=http_post,
    )

    assert captured["headers"]["Authorization"] == "Bearer APP_USR-tenant-token"
    assert captured["json"]["notification_url"].endswith("/tenant-token")
    assert preference["preference_id"] == "pref_123"
    assert preference["payment_url"] == "https://mercadopago.com.br/checkout"


def test_fetch_payment_usa_access_token_do_tenant(monkeypatch):
    monkeypatch.delenv("MERCADO_PAGO_ACCESS_TOKEN", raising=False)
    captured = {}

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "pay_123", "status": "approved"}

    def http_get(url, headers, timeout):
        captured.update({"url": url, "headers": headers, "timeout": timeout})
        return Response()

    payment = fetch_payment(
        "pay_123",
        access_token="APP_USR-tenant-token",
        http_get=http_get,
    )

    assert captured["headers"]["Authorization"] == "Bearer APP_USR-tenant-token"
    assert payment == {"id": "pay_123", "status": "approved"}
