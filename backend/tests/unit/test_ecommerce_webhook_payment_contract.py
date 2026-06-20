import pytest
from fastapi import HTTPException

from app.routes.ecommerce_webhooks import (
    _extrair_pagamento_do_webhook,
    _find_payment_preference_id,
    _find_pedido_for_payment,
    _find_pedido_id,
    _normalizar_canal_venda_online,
    _normalizar_payment_method_online,
)


class _FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def first(self):
        return self.result


class _FakeDb:
    def __init__(self, *results):
        self.results = list(results)
        self.queries = 0

    def query(self, model):
        self.queries += 1
        result = self.results.pop(0) if self.results else None
        return _FakeQuery(result)


@pytest.mark.parametrize(
    ("payment_method", "esperado"),
    [
        ("pix", "pix"),
        ("credit_card", "credit_card"),
        ("debit_card", "debit_card"),
    ],
)
def test_webhook_aceita_somente_pix_credito_debito(payment_method, esperado):
    assert _normalizar_payment_method_online(payment_method) == esperado


@pytest.mark.parametrize(
    "payment_method", ["boleto", "bank_slip", "transfer", "voucher", "", None]
)
def test_webhook_recusa_pagamentos_fora_do_contrato_online(payment_method):
    with pytest.raises(HTTPException) as exc:
        _normalizar_payment_method_online(payment_method)

    assert exc.value.status_code == 400


def test_webhook_nao_assume_pix_quando_metodo_pagamento_esta_ausente():
    payment_method, installments = _extrair_pagamento_do_webhook(
        {"metadata": {"parcelas": 3}}
    )

    assert payment_method == ""
    assert installments == 3


def test_webhook_identifica_pedido_por_external_reference():
    assert _find_pedido_id({"external_reference": "PED-APP-123"}) == "PED-APP-123"
    assert (
        _find_pedido_id({"mercadopago": {"payment": {"external_reference": "PED-MP"}}})
        == "PED-MP"
    )


def test_webhook_resolve_pedido_por_payment_preference_id_quando_pedido_id_ausente():
    pedido = object()
    payload = {
        "status": "approved",
        "mercadopago": {"payment": {"order": {"id": "pref-123"}}},
    }
    db = _FakeDb(pedido)

    assert _find_payment_preference_id(payload) == "pref-123"
    assert _find_pedido_for_payment(db, tenant_id="tenant-1", payload=payload) is pedido
    assert db.queries == 1


def test_webhook_tenta_preference_id_quando_pedido_id_nao_encontra_registro():
    pedido = object()
    payload = {
        "pedido_id": "PED-INEXISTENTE",
        "metadata": {"payment_preference_id": "pref-456"},
    }
    db = _FakeDb(None, pedido)

    assert _find_pedido_for_payment(db, tenant_id="tenant-1", payload=payload) is pedido
    assert db.queries == 2


@pytest.mark.parametrize(
    "canal", ["web", "site", "loja_virtual", "e-commerce", "ecommerce"]
)
def test_webhook_normaliza_canais_web_como_ecommerce(canal):
    assert _normalizar_canal_venda_online(canal) == "ecommerce"


@pytest.mark.parametrize("canal", ["app", "aplicativo"])
def test_webhook_normaliza_canais_app(canal):
    assert _normalizar_canal_venda_online(canal) == "app"
