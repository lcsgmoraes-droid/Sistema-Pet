import hmac
import hashlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes.ecommerce_webhooks import (
    _get_signature_config,
    _validate_optional_signature,
)


def _request(headers=None):
    return SimpleNamespace(headers=headers or {})


def test_webhook_pagarme_mantem_assinatura_opcional_em_dev(monkeypatch):
    monkeypatch.delenv("PAGARME_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("PAGARME_WEBHOOK_VALIDATE_SIGNATURE", raising=False)
    monkeypatch.delenv("ECOMMERCE_PAYMENT_GATEWAY_ENABLED", raising=False)
    monkeypatch.delenv("ECOMMERCE_PAYMENT_PROVIDER", raising=False)

    secret, validate = _get_signature_config()

    assert secret == ""
    assert validate is False
    assert _validate_optional_signature(b"{}", _request()) == "skipped_by_config"


def test_webhook_pagarme_exige_segredo_quando_gateway_pagarme_ativo(monkeypatch):
    monkeypatch.delenv("PAGARME_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("PAGARME_WEBHOOK_VALIDATE_SIGNATURE", raising=False)
    monkeypatch.setenv("ECOMMERCE_PAYMENT_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("ECOMMERCE_PAYMENT_PROVIDER", "pagarme")

    with pytest.raises(HTTPException) as exc:
        _validate_optional_signature(b"{}", _request())

    assert exc.value.status_code == 503


def test_webhook_pagarme_valida_assinatura_sha256(monkeypatch):
    raw_body = b'{"id":"evt_123"}'
    secret = "segredo-teste"
    signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    monkeypatch.setenv("PAGARME_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("PAGARME_WEBHOOK_VALIDATE_SIGNATURE", "true")
    monkeypatch.delenv("ECOMMERCE_PAYMENT_GATEWAY_ENABLED", raising=False)

    status = _validate_optional_signature(
        raw_body,
        _request({"X-PagarMe-Hmac-SHA256": f"sha256={signature}"}),
    )

    assert status == "validated"


def test_webhook_pagarme_rejeita_assinatura_invalida(monkeypatch):
    monkeypatch.setenv("PAGARME_WEBHOOK_SECRET", "segredo-teste")
    monkeypatch.setenv("PAGARME_WEBHOOK_VALIDATE_SIGNATURE", "true")
    monkeypatch.delenv("ECOMMERCE_PAYMENT_GATEWAY_ENABLED", raising=False)

    with pytest.raises(HTTPException) as exc:
        _validate_optional_signature(
            b'{"id":"evt_123"}',
            _request({"X-PagarMe-Signature": "sha256=assinatura-errada"}),
        )

    assert exc.value.status_code == 401
