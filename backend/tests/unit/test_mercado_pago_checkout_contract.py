import hashlib
import hmac
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.mercado_pago_checkout import (
    build_preference_payload,
    select_checkout_url,
    validate_webhook_signature,
)
from app.routes.ecommerce_webhooks import (
    _extrair_pagamento_do_webhook,
    _map_payment_status,
)


def _pedido():
    return SimpleNamespace(
        pedido_id="PED-COREPET-123",
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        origem="app",
    )


def test_build_preference_payload_inclui_metadados_urls_e_total(monkeypatch):
    monkeypatch.setenv("ECOMMERCE_BASE_URL", "https://corepet.com.br/")

    payload = build_preference_payload(
        pedido=_pedido(),
        total=123.45,
        forma_pagamento_tipo="pix",
        endereco_entrega="RETIRADA NA LOJA",
        tipo_retirada="app_loja",
    )

    assert payload["external_reference"] == "PED-COREPET-123"
    assert payload["notification_url"] == "https://corepet.com.br/api/webhooks/mercadopago"
    assert payload["items"] == [
        {
            "id": "PED-COREPET-123",
            "title": "Pedido CorePet PED-COREPET-123",
            "quantity": 1,
            "currency_id": "BRL",
            "unit_price": 123.45,
        }
    ]
    assert payload["metadata"] == {
        "pedido_id": "PED-COREPET-123",
        "tenant_id": "180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        "canal": "app",
        "payment_method": "pix",
        "delivery_mode": "retirada",
        "tipo_retirada": "app_loja",
        "endereco_entrega": "RETIRADA NA LOJA",
        "tem_entrega": False,
    }


def test_select_checkout_url_respeita_sandbox(monkeypatch):
    preference = {
        "init_point": "https://www.mercadopago.com.br/checkout/v1/redirect",
        "sandbox_init_point": "https://sandbox.mercadopago.com.br/checkout/v1/redirect",
    }

    monkeypatch.setenv("MERCADO_PAGO_USE_SANDBOX", "true")
    assert select_checkout_url(preference) == preference["sandbox_init_point"]

    monkeypatch.setenv("MERCADO_PAGO_USE_SANDBOX", "false")
    assert select_checkout_url(preference) == preference["init_point"]


def test_validate_webhook_signature_usa_manifesto_oficial():
    secret = "mp-secret"
    data_id = "123456"
    request_id = "bb56a2f1-6aae-46ac-982e-9dcd3581d08e"
    ts = "1742505638683"
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    signature = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    request = SimpleNamespace(
        headers={
            "x-request-id": request_id,
            "x-signature": f"ts={ts},v1={signature}",
        },
        query_params={"data.id": data_id},
    )

    assert validate_webhook_signature(request, secret) == "validated"


def test_validate_webhook_signature_rejeita_assinatura_invalida():
    request = SimpleNamespace(
        headers={"x-request-id": "req", "x-signature": "ts=1,v1=errada"},
        query_params={"data.id": "123"},
    )

    with pytest.raises(HTTPException) as exc:
        validate_webhook_signature(request, "mp-secret")

    assert exc.value.status_code == 401


def test_webhook_mercado_pago_mapeia_pix_e_status_aprovado():
    payload = {
        "provider": "mercadopago",
        "status": "approved",
        "payment_method_id": "pix",
        "payment_type_id": "bank_transfer",
        "installments": 1,
    }

    assert _map_payment_status(payload) == "aprovado"
    assert _extrair_pagamento_do_webhook(payload) == ("pix", 1)


def test_webhook_mercado_pago_mapeia_credito_parcelado_e_recusado():
    payload = {
        "provider": "mercadopago",
        "status": "rejected",
        "payment_method_id": "master",
        "payment_type_id": "credit_card",
        "installments": 3,
    }

    assert _map_payment_status(payload) == "recusado"
    assert _extrair_pagamento_do_webhook(payload) == ("credit_card", 3)
