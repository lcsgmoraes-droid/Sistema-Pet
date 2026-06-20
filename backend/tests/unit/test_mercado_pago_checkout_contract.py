import hashlib
import hmac
import inspect
import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.routes import ecommerce_checkout, ecommerce_webhooks
from app.services.mercado_pago_checkout import (
    build_preference_payload,
    extract_gateway_financials,
    normalize_payment_payload,
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
    assert (
        payload["notification_url"] == "https://corepet.com.br/api/webhooks/mercadopago"
    )
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
    assert payload["payment_methods"]["excluded_payment_methods"] == [
        {"id": "account_money"}
    ]


@pytest.mark.parametrize(
    "forma_pagamento_tipo",
    ["pix", "cartao_debito", "cartao_credito"],
)
def test_build_preference_payload_bloqueia_saldo_mercado_pago(
    monkeypatch, forma_pagamento_tipo
):
    monkeypatch.setenv("ECOMMERCE_BASE_URL", "https://corepet.com.br/")

    payload = build_preference_payload(
        pedido=_pedido(),
        total=123.45,
        forma_pagamento_tipo=forma_pagamento_tipo,
        endereco_entrega="RETIRADA NA LOJA",
        tipo_retirada="app_loja",
    )

    assert payload["payment_methods"]["excluded_payment_methods"] == [
        {"id": "account_money"}
    ]


def test_build_preference_payload_normaliza_web_como_ecommerce(monkeypatch):
    monkeypatch.setenv("ECOMMERCE_BASE_URL", "https://corepet.com.br/")
    pedido = SimpleNamespace(
        pedido_id="PED-WEB-123",
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        origem="web",
    )

    payload = build_preference_payload(
        pedido=pedido,
        total=12.34,
        forma_pagamento_tipo="pix",
        endereco_entrega="RETIRADA NA LOJA",
        tipo_retirada="proprio",
    )

    assert payload["metadata"]["canal"] == "ecommerce"


def test_build_preference_payload_retorna_para_pedidos_da_loja(monkeypatch):
    monkeypatch.setenv("ECOMMERCE_BASE_URL", "https://corepet.com.br/")

    payload = build_preference_payload(
        pedido=_pedido(),
        total=123.45,
        forma_pagamento_tipo="pix",
        endereco_entrega="RETIRADA NA LOJA",
        tipo_retirada="app_loja",
        return_url_base="https://corepet.com.br/atacadao",
    )

    assert payload["back_urls"] == {
        "success": "https://corepet.com.br/atacadao?view=pedidos&payment_status=success&pedido_id=PED-COREPET-123",
        "pending": "https://corepet.com.br/atacadao?view=pedidos&payment_status=pending&pedido_id=PED-COREPET-123",
        "failure": "https://corepet.com.br/atacadao?view=pedidos&payment_status=failure&pedido_id=PED-COREPET-123",
    }


def test_build_preference_payload_retorno_app_preserva_loja_e_canal(monkeypatch):
    monkeypatch.setenv("ECOMMERCE_BASE_URL", "https://corepet.com.br/")

    payload = build_preference_payload(
        pedido=_pedido(),
        total=123.45,
        forma_pagamento_tipo="pix",
        endereco_entrega="RETIRADA NA LOJA",
        tipo_retirada="app_loja",
        return_url_base="https://corepet.com.br/app/retorno-pagamento",
        return_url_params={"loja": "atacadao", "tenant": "atacadao", "canal": "app"},
    )

    assert payload["back_urls"] == {
        "success": "https://corepet.com.br/app/retorno-pagamento?view=pedidos&payment_status=success&pedido_id=PED-COREPET-123&loja=atacadao&tenant=atacadao&canal=app",
        "pending": "https://corepet.com.br/app/retorno-pagamento?view=pedidos&payment_status=pending&pedido_id=PED-COREPET-123&loja=atacadao&tenant=atacadao&canal=app",
        "failure": "https://corepet.com.br/app/retorno-pagamento?view=pedidos&payment_status=failure&pedido_id=PED-COREPET-123&loja=atacadao&tenant=atacadao&canal=app",
    }


def test_finalizar_checkout_define_origem_antes_de_criar_preferencia_mp():
    source = inspect.getsource(ecommerce_checkout.finalizar_checkout)

    assert "origem_checkout = _resolver_origem_checkout(payload, request)" in source
    assert source.index(
        "origem_checkout = _resolver_origem_checkout(payload, request)"
    ) < source.index("request_data = _checkout_idempotency_payload(")
    assert source.index("carrinho.origem = origem_checkout") < source.index(
        "preference = create_preference("
    )


def test_checkout_resolve_origem_app_por_payload_ou_headers():
    payload = ecommerce_checkout.CheckoutFinalizarRequest(
        cidade_destino="Presidente Prudente",
        forma_pagamento_nome="PIX",
        origem=None,
    )

    assert (
        ecommerce_checkout._resolver_origem_checkout(
            ecommerce_checkout.CheckoutFinalizarRequest(
                cidade_destino="Presidente Prudente",
                forma_pagamento_nome="PIX",
                origem="app",
            ),
            SimpleNamespace(headers={}),
        )
        == "app"
    )
    assert (
        ecommerce_checkout._resolver_origem_checkout(
            payload,
            SimpleNamespace(headers={"X-Canal-Venda": "app"}),
        )
        == "app"
    )
    assert (
        ecommerce_checkout._resolver_origem_checkout(
            payload,
            SimpleNamespace(headers={"X-Client-Channel": "mobile"}),
        )
        == "app"
    )
    assert (
        ecommerce_checkout._resolver_origem_checkout(
            payload,
            SimpleNamespace(headers={}),
        )
        == "ecommerce"
    )


def test_webhook_integracao_usa_origem_do_pedido_como_fallback():
    source = inspect.getsource(ecommerce_webhooks._integrar_venda_ao_motor)

    assert 'getattr(pedido, "origem", None)' in source
    assert source.index('getattr(pedido, "origem", None)') < source.index(
        'or "ecommerce"'
    )


def test_webhook_integracao_retirada_online_fica_pendente_de_separacao():
    source = inspect.getsource(ecommerce_webhooks._integrar_venda_ao_motor)

    assert "online_retirada" in source
    assert 'venda_row.status_entrega = "pendente"' in source


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


def test_normalize_payment_payload_expõe_taxa_real_e_liquido_do_mercado_pago():
    payment = {
        "id": 1387729134,
        "status": "approved",
        "payment_method_id": "pix",
        "payment_type_id": "bank_transfer",
        "transaction_amount": 3.98,
        "fee_details": [
            {"type": "mercadopago_fee", "amount": 0.23},
            {"type": "financing_fee", "amount": 0},
        ],
        "transaction_details": {
            "net_received_amount": 3.75,
            "total_paid_amount": 3.98,
        },
    }

    financials = extract_gateway_financials(payment)
    normalized = normalize_payment_payload(payment)

    assert financials == {
        "gateway_provider": "mercadopago",
        "gateway_payment_id": "1387729134",
        "gateway_fee_amount": 0.23,
        "gateway_net_amount": 3.75,
        "gateway_gross_amount": 3.98,
    }
    assert normalized["gateway_provider"] == "mercadopago"
    assert normalized["gateway_fee_amount"] == 0.23
    assert normalized["gateway_net_amount"] == 3.75
    assert normalized["data"]["gateway_fee_amount"] == 0.23


def test_extract_gateway_financials_preserva_taxa_zero_configurada():
    payment = {
        "provider": "mercadopago",
        "mercadopago": {
            "payment": {
                "id": "mp-zero-fee",
                "gateway_fee_amount": 0,
                "gateway_net_amount": 10,
                "gateway_gross_amount": 10,
            }
        },
    }

    assert extract_gateway_financials(payment) == {
        "gateway_provider": "mercadopago",
        "gateway_payment_id": "mp-zero-fee",
        "gateway_fee_amount": 0.0,
        "gateway_net_amount": 10.0,
        "gateway_gross_amount": 10.0,
    }
