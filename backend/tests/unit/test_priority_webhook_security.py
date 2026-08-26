import hashlib
import hmac
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.services import bling_webhook_security
from app.services.bling_webhook_security import validate_bling_webhook_signature
from app.whatsapp.webhook import (
    receive_webhook,
    validate_webhook_authentication,
    validate_webhook_signature,
)


ROOT = Path(__file__).resolve().parents[3]


class _Request:
    def __init__(self, raw_body: bytes, headers: dict[str, str] | None = None):
        self._raw_body = raw_body
        self.headers = headers or {}
        self.state = SimpleNamespace()

    async def body(self) -> bytes:
        return self._raw_body


class _ConfigQuery:
    def __init__(self, config):
        self.config = config

    def filter(self, *_criteria):
        return self

    def first(self):
        return self.config


class _ConfigDb:
    def __init__(self, config):
        self.config = config

    def query(self, _model):
        return _ConfigQuery(self.config)


def _hmac_header(secret: str, raw_body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_bling_accepts_the_official_signature_over_the_exact_raw_body():
    secret = "bling-client-secret"
    raw_body = b'{"eventId":"evt-1","data":{"id":123}}'

    assert validate_bling_webhook_signature(
        raw_body,
        _hmac_header(secret, raw_body),
        secret,
    )
    assert not validate_bling_webhook_signature(
        raw_body + b" ",
        _hmac_header(secret, raw_body),
        secret,
    )


@pytest.mark.asyncio
async def test_bling_rejects_missing_or_invalid_signature_before_processing(
    monkeypatch,
):
    secret = "bling-client-secret"
    raw_body = b'{"eventId":"evt-1"}'
    monkeypatch.setattr(
        bling_webhook_security,
        "_configured_bling_client_secret",
        lambda: secret,
    )

    for header in (None, "sha256=invalid"):
        request = _Request(
            raw_body,
            ({"X-Bling-Signature-256": header} if header else {}),
        )
        with pytest.raises(HTTPException) as exc:
            await bling_webhook_security.require_bling_webhook_signature(request)

        assert exc.value.status_code == 403
        assert not hasattr(request.state, "bling_webhook_signature_verified")


@pytest.mark.asyncio
async def test_bling_fails_closed_when_client_secret_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        bling_webhook_security,
        "_configured_bling_client_secret",
        lambda: "",
    )

    with pytest.raises(HTTPException) as exc:
        await bling_webhook_security.require_bling_webhook_signature(_Request(b"{}"))

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_bling_marks_only_a_validated_request_as_verified(monkeypatch):
    secret = "bling-client-secret"
    raw_body = b'{"eventId":"evt-2"}'
    request = _Request(
        raw_body,
        {"X-Bling-Signature-256": _hmac_header(secret, raw_body)},
    )
    monkeypatch.setattr(
        bling_webhook_security,
        "_configured_bling_client_secret",
        lambda: secret,
    )

    await bling_webhook_security.require_bling_webhook_signature(request)

    assert request.state.bling_webhook_signature_verified is True


def test_bling_order_and_invoice_routes_share_the_security_dependency():
    for relative_path in (
        "backend/app/integracao_bling_pedido_routes.py",
        "backend/app/integracao_bling_nf_routes.py",
    ):
        source = (ROOT / relative_path).read_text(encoding="utf-8")

        assert "Depends(require_bling_webhook_signature)" in source


def test_whatsapp_signature_validation_is_fail_closed():
    raw_body = b'{"entry":[]}'
    secret = "whatsapp-webhook-secret"
    signature = _hmac_header(secret, raw_body)

    assert validate_webhook_signature(raw_body, signature, secret)
    assert not validate_webhook_signature(raw_body, "", secret)
    assert not validate_webhook_signature(raw_body, signature, "")
    assert not validate_webhook_signature(raw_body, "sha256=invalid", secret)


def test_whatsapp_accepts_the_static_header_supported_by_360dialog():
    assert validate_webhook_authentication(
        b'{"entry":[]}',
        signature=None,
        static_token="whatsapp-webhook-secret",
        secret="whatsapp-webhook-secret",
    )
    assert not validate_webhook_authentication(
        b'{"entry":[]}',
        signature=None,
        static_token="wrong-secret",
        secret="whatsapp-webhook-secret",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("configured_secret", "signature", "expected_status"),
    (
        ("", "", 503),
        ("whatsapp-webhook-secret", "", 403),
        ("whatsapp-webhook-secret", "sha256=invalid", 403),
    ),
)
async def test_whatsapp_rejects_insecure_request_before_parsing_payload(
    configured_secret,
    signature,
    expected_status,
):
    request = _Request(
        b"not-json",
        ({"X-Hub-Signature-256": signature} if signature else {}),
    )
    db = _ConfigDb(SimpleNamespace(webhook_secret=configured_secret))

    with pytest.raises(HTTPException) as exc:
        await receive_webhook(
            tenant_id="00000000-0000-0000-0000-000000000001",
            request=request,
            background_tasks=BackgroundTasks(),
            db=db,
        )

    assert exc.value.status_code == expected_status


@pytest.mark.asyncio
async def test_whatsapp_custom_token_is_checked_before_payload_parsing():
    secret = "whatsapp-webhook-secret"
    request = _Request(
        b"not-json",
        {"X-CorePet-Webhook-Token": secret},
    )
    db = _ConfigDb(SimpleNamespace(webhook_secret=secret))

    with pytest.raises(HTTPException) as exc:
        await receive_webhook(
            tenant_id="00000000-0000-0000-0000-000000000001",
            request=request,
            background_tasks=BackgroundTasks(),
            db=db,
        )

    assert exc.value.status_code == 400
