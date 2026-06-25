"""Seguranca, tenant e identificacao de eventos dos webhooks de ecommerce."""

import hashlib
import hmac
import os
from uuid import UUID

from fastapi import HTTPException, Request, status


TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
PAGARME_SIGNATURE_HEADERS = (
    "X-Hub-Signature",
    "X-PagarMe-Signature",
    "X-Pagarme-Signature",
    "X-PagarMe-Hmac-SHA256",
    "X-Pagarme-Hmac-SHA256",
    "X-Signature",
)


def _env_flag_enabled(name: str) -> bool:
    return (os.getenv(name, "") or "").strip().lower() in TRUE_ENV_VALUES


def _payment_gateway_requires_signature() -> bool:
    if not _env_flag_enabled("ECOMMERCE_PAYMENT_GATEWAY_ENABLED"):
        return False

    provider = (os.getenv("ECOMMERCE_PAYMENT_PROVIDER", "") or "").strip().lower()
    return not provider or "pagar" in provider


def _get_signature_config() -> tuple[str, bool]:
    secret = (os.getenv("PAGARME_WEBHOOK_SECRET", "") or "").strip()
    validate = (
        _env_flag_enabled("PAGARME_WEBHOOK_VALIDATE_SIGNATURE")
        or _payment_gateway_requires_signature()
    )
    return secret, validate


def _find_tenant_id(payload: dict, request: Request) -> str:
    candidates = [
        payload.get("tenant_id"),
        payload.get("tenantId"),
        (payload.get("metadata") or {}).get("tenant_id"),
        (payload.get("metadata") or {}).get("tenantId"),
        ((payload.get("data") or {}).get("metadata") or {}).get("tenant_id"),
        ((payload.get("data") or {}).get("metadata") or {}).get("tenantId"),
        request.headers.get("X-Tenant-ID"),
    ]

    for value in candidates:
        if not value:
            continue
        try:
            return str(UUID(str(value)))
        except Exception:
            continue

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="tenant_id obrigatorio (payload metadata.tenant_id ou header X-Tenant-ID)",
    )


def _extract_event_info(payload: dict, raw_body: bytes) -> tuple[str, str, str]:
    event_type = str(payload.get("type") or payload.get("event") or "unknown")

    event_id = (
        payload.get("id")
        or (payload.get("data") or {}).get("id")
        or (payload.get("data") or {}).get("event_id")
    )

    if not event_id:
        event_id = hashlib.sha256(raw_body).hexdigest()

    request_hash = hashlib.sha256(raw_body).hexdigest()
    return str(event_id), event_type, request_hash


def _validate_optional_signature(raw_body: bytes, request: Request) -> str:
    secret, validate_signature = _get_signature_config()

    if not validate_signature:
        return "skipped_by_config"

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook Pagar.me sem segredo configurado",
        )

    signature_header = ""
    for header_name in PAGARME_SIGNATURE_HEADERS:
        signature_header = (request.headers.get(header_name) or "").strip()
        if signature_header:
            break

    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura do webhook ausente",
        )

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    received = signature_header.split("=")[-1].strip()

    if not hmac.compare_digest(expected, received):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura do webhook invalida",
        )

    return "validated"
