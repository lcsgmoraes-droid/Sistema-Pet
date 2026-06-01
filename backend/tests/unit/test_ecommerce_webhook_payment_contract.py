import pytest
from fastapi import HTTPException

from app.routes.ecommerce_webhooks import (
    _extrair_pagamento_do_webhook,
    _normalizar_canal_venda_online,
    _normalizar_payment_method_online,
)


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


@pytest.mark.parametrize("payment_method", ["boleto", "bank_slip", "transfer", "voucher", "", None])
def test_webhook_recusa_pagamentos_fora_do_contrato_online(payment_method):
    with pytest.raises(HTTPException) as exc:
        _normalizar_payment_method_online(payment_method)

    assert exc.value.status_code == 400


def test_webhook_nao_assume_pix_quando_metodo_pagamento_esta_ausente():
    payment_method, installments = _extrair_pagamento_do_webhook({"metadata": {"parcelas": 3}})

    assert payment_method == ""
    assert installments == 3


@pytest.mark.parametrize("canal", ["web", "site", "loja_virtual", "e-commerce", "ecommerce"])
def test_webhook_normaliza_canais_web_como_ecommerce(canal):
    assert _normalizar_canal_venda_online(canal) == "ecommerce"


@pytest.mark.parametrize("canal", ["app", "aplicativo"])
def test_webhook_normaliza_canais_app(canal):
    assert _normalizar_canal_venda_online(canal) == "app"

