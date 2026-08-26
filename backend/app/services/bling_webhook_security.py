from __future__ import annotations

import hashlib
import hmac
import logging
import os

from fastapi import HTTPException, Request, status


logger = logging.getLogger(__name__)

BLING_SIGNATURE_HEADER = "X-Bling-Signature-256"
BLING_SIGNATURE_PREFIX = "sha256="


def _configured_bling_client_secret() -> str:
    """Read the same client secret used by the Bling OAuth integration."""

    direct_value = str(os.getenv("BLING_CLIENT_SECRET") or "").strip()
    if direct_value:
        return direct_value

    # The Bling client can reload credentials from the shared environment file
    # after OAuth token rotation. Reuse that source instead of creating a second
    # webhook secret with an independent lifecycle.
    try:
        from app.bling_integration_parts.core import _load_bling_runtime_config

        return str(_load_bling_runtime_config().get("client_secret") or "").strip()
    except Exception as exc:
        logger.error(
            "Nao foi possivel carregar a credencial de verificacao do webhook Bling: %s",
            type(exc).__name__,
        )
        return ""


def validate_bling_webhook_signature(
    raw_body: bytes,
    provided_signature: str | None,
    client_secret: str,
) -> bool:
    """Validate the official Bling HMAC-SHA256 signature over the raw body."""

    secret = str(client_secret or "").strip()
    signature = str(provided_signature or "").strip()
    if not secret or not signature:
        return False

    if not signature.lower().startswith(BLING_SIGNATURE_PREFIX):
        return False

    received_digest = signature[len(BLING_SIGNATURE_PREFIX) :].strip().lower()
    if len(received_digest) != 64:
        return False
    try:
        bytes.fromhex(received_digest)
    except ValueError:
        return False

    expected_digest = hmac.new(
        secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_digest, received_digest)


async def require_bling_webhook_signature(request: Request) -> None:
    """Reject unsigned or forged Bling events before parsing or persistence."""

    client_secret = _configured_bling_client_secret()
    if not client_secret:
        logger.error(
            "Webhook Bling rejeitado porque BLING_CLIENT_SECRET nao esta configurado."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook do Bling indisponivel por configuracao.",
        )

    raw_body = await request.body()
    provided_signature = request.headers.get(BLING_SIGNATURE_HEADER)
    if not validate_bling_webhook_signature(
        raw_body,
        provided_signature,
        client_secret,
    ):
        logger.warning("Webhook Bling rejeitado por assinatura ausente ou invalida.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assinatura do webhook invalida.",
        )

    request.state.bling_webhook_signature_verified = True
