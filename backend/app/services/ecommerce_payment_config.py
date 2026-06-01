"""Servicos para configuracao de pagamentos do e-commerce por tenant."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi import HTTPException, status
import requests
from sqlalchemy.orm import Session

from app.config import JWT_SECRET_KEY
from app.ecommerce_payment_models import EcommercePaymentGatewayConfig


MERCADO_PAGO_PROVIDER = "mercadopago"
VALID_ENVIRONMENTS = {"production", "sandbox"}
SECRET_PREFIX = "fernet:"
OAUTH_AUTH_URL = "https://auth.mercadopago.com/authorization"
OAUTH_TOKEN_URL = "https://api.mercadopago.com/oauth/token"
OAUTH_STATE_TTL_SECONDS = 15 * 60
OAUTH_REFRESH_SKEW_SECONDS = 5 * 60


@dataclass(frozen=True)
class MercadoPagoRuntimeConfig:
    tenant_id: str
    provider: str
    enabled: bool
    environment: str
    public_key: str | None
    access_token: str
    webhook_secret: str
    webhook_token: str
    webhook_url: str

    @property
    def use_sandbox(self) -> bool:
        return self.environment == "sandbox"


def _public_base_url() -> str:
    value = (
        os.getenv("ECOMMERCE_PUBLIC_BASE_URL")
        or os.getenv("ECOMMERCE_BASE_URL")
        or os.getenv("FRONTEND_URL")
        or "https://corepet.com.br"
    )
    return str(value).strip().rstrip("/")


def _frontend_base_url() -> str:
    value = (
        os.getenv("FRONTEND_PUBLIC_BASE_URL")
        or os.getenv("FRONTEND_URL")
        or os.getenv("ECOMMERCE_PUBLIC_BASE_URL")
        or "https://corepet.com.br"
    )
    base = str(value).strip().rstrip("/")
    if base.endswith("/api"):
        base = base[: -len("/api")]
    return base


def _normalize_tenant_id(tenant_id: str | UUID) -> UUID:
    return tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))


def _secret_key() -> str:
    return (
        os.getenv("PAYMENT_CONFIG_ENCRYPTION_KEY")
        or os.getenv("ENCRYPTION_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or JWT_SECRET_KEY
        or "corepet-local-payment-config-key"
    ).strip()


def _fernet_key() -> bytes:
    raw_secret = _secret_key()
    try:
        Fernet(raw_secret.encode("utf-8"))
        return raw_secret.encode("utf-8")
    except Exception:
        digest = hashlib.sha256(raw_secret.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)


def _cipher() -> Fernet:
    return Fernet(_fernet_key())


def encrypt_secret(value: str | None) -> str | None:
    """Criptografa um segredo do gateway sem expor texto claro no banco."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.startswith(SECRET_PREFIX):
        return raw
    return SECRET_PREFIX + _cipher().encrypt(raw.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str:
    """Descriptografa segredo, mantendo compatibilidade com dados legados em texto."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    if not raw.startswith(SECRET_PREFIX):
        return raw
    token = raw[len(SECRET_PREFIX) :]
    try:
        return _cipher().decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def new_webhook_token() -> str:
    return f"mp_{secrets.token_urlsafe(24)}"


def build_mercado_pago_webhook_url(
    webhook_token: str,
    *,
    base_url: str | None = None,
) -> str:
    base = (base_url or _public_base_url()).strip().rstrip("/")
    return f"{base}/api/webhooks/mercadopago/{webhook_token}"


def build_mercado_pago_oauth_redirect_uri(*, base_url: str | None = None) -> str:
    configured = str(os.getenv("MERCADO_PAGO_OAUTH_REDIRECT_URI") or "").strip()
    if configured:
        return configured
    base = (base_url or _public_base_url()).strip().rstrip("/")
    return f"{base}/api/ecommerce-payment-config/mercadopago/oauth/callback"


def build_mercado_pago_oauth_return_url(status_value: str, *, message: str | None = None) -> str:
    base = _frontend_base_url()
    params = {"mercadopago_oauth": status_value}
    if message:
        params["mercadopago_message"] = message[:180]
    return f"{base}/ecommerce/configuracoes?{urlencode(params)}"


def _mask_config_value(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if len(raw) <= 10:
        return "configurado"
    return f"{raw[:6]}...{raw[-4:]}"


def _oauth_client_id(config: Any | None = None) -> str:
    configured = str(getattr(config, "oauth_client_id", None) or "").strip()
    if configured:
        return configured
    return (
        os.getenv("MERCADO_PAGO_OAUTH_CLIENT_ID")
        or os.getenv("MERCADOPAGO_OAUTH_CLIENT_ID")
        or os.getenv("MERCADO_PAGO_CLIENT_ID")
        or ""
    ).strip()


def _oauth_client_secret(config: Any | None = None) -> str:
    configured = decrypt_secret(getattr(config, "oauth_client_secret_encrypted", None))
    if configured:
        return configured
    return (
        os.getenv("MERCADO_PAGO_OAUTH_CLIENT_SECRET")
        or os.getenv("MERCADOPAGO_OAUTH_CLIENT_SECRET")
        or os.getenv("MERCADO_PAGO_CLIENT_SECRET")
        or ""
    ).strip()


def is_mercado_pago_oauth_available(config: Any | None = None) -> bool:
    return bool(_oauth_client_id(config) and _oauth_client_secret(config))


def missing_mercado_pago_oauth_settings(config: Any | None = None) -> list[str]:
    missing: list[str] = []
    if not _oauth_client_id(config):
        missing.append("MERCADO_PAGO_OAUTH_CLIENT_ID")
    if not _oauth_client_secret(config):
        missing.append("MERCADO_PAGO_OAUTH_CLIENT_SECRET")
    return missing


def _global_mercado_pago_webhook_secret() -> str:
    return (
        os.getenv("MERCADO_PAGO_WEBHOOK_SECRET")
        or os.getenv("MERCADOPAGO_WEBHOOK_SECRET")
        or ""
    ).strip()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def encode_mercado_pago_oauth_state(
    *,
    tenant_id: str | UUID,
    user_id: int,
    expires_in: int = OAUTH_STATE_TTL_SECONDS,
) -> str:
    expires_at = int(time.time()) + int(expires_in)
    payload = {
        "tenant_id": str(_normalize_tenant_id(tenant_id)),
        "user_id": int(user_id),
        "exp": expires_at,
        "nonce": secrets.token_urlsafe(16),
    }
    payload_raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_part = _b64url_encode(payload_raw)
    signature = hmac.new(_secret_key().encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64url_encode(signature)}"


def validate_mercado_pago_oauth_state(state: str | None) -> dict[str, Any] | None:
    raw = str(state or "").strip()
    if not raw or "." not in raw:
        return None
    payload_part, signature_part = raw.split(".", 1)
    expected = hmac.new(_secret_key().encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    try:
        received = _b64url_decode(signature_part)
    except Exception:
        return None
    if not hmac.compare_digest(expected, received):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    except Exception:
        return None
    try:
        if int(payload.get("exp") or 0) < int(time.time()):
            return None
        payload["tenant_id"] = str(_normalize_tenant_id(payload.get("tenant_id")))
        payload["user_id"] = int(payload.get("user_id"))
    except Exception:
        return None
    return payload


def build_mercado_pago_oauth_authorization_url(
    *,
    tenant_id: str | UUID,
    user_id: int,
    redirect_uri: str,
    config: Any | None = None,
) -> str:
    client_id = _oauth_client_id(config)
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Client ID OAuth do Mercado Pago nao configurado.",
        )
    state_value = encode_mercado_pago_oauth_state(tenant_id=tenant_id, user_id=user_id)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "platform_id": "mp",
        "state": state_value,
        "redirect_uri": redirect_uri,
    }
    return f"{OAUTH_AUTH_URL}?{urlencode(params)}"


def exchange_mercado_pago_oauth_code(
    *,
    code: str,
    redirect_uri: str,
    environment: str = "production",
    config: Any | None = None,
    http_post=requests.post,
) -> dict[str, Any]:
    if not is_mercado_pago_oauth_available(config):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth Mercado Pago nao configurado no servidor CorePet.",
        )

    payload = {
        "client_id": _oauth_client_id(config),
        "client_secret": _oauth_client_secret(config),
        "code": str(code or "").strip(),
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "test_token": "true" if _normalize_environment(environment) == "sandbox" else "false",
    }
    response = http_post(
        OAUTH_TOKEN_URL,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        json=payload,
        timeout=20,
    )
    if getattr(response, "status_code", 500) >= 300:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Mercado Pago recusou a autorizacao OAuth: {getattr(response, 'text', '')[:300]}",
        )
    data = response.json()
    if not data.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Mercado Pago nao retornou access_token no OAuth.",
        )
    return data


def _normalize_environment(value: str | None) -> str:
    environment = str(value or "production").strip().lower()
    if environment in {"prod", "producao", "produção"}:
        environment = "production"
    if environment in {"test", "teste", "homologacao", "homologação"}:
        environment = "sandbox"
    if environment not in VALID_ENVIRONMENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ambiente Mercado Pago invalido. Use production ou sandbox.",
        )
    return environment


def get_mercado_pago_config(
    db: Session,
    tenant_id: str | UUID,
) -> EcommercePaymentGatewayConfig | None:
    return (
        db.query(EcommercePaymentGatewayConfig)
        .filter(
            EcommercePaymentGatewayConfig.tenant_id == _normalize_tenant_id(tenant_id),
            EcommercePaymentGatewayConfig.provider == MERCADO_PAGO_PROVIDER,
        )
        .first()
    )


def get_mercado_pago_config_by_webhook_token(
    db: Session,
    webhook_token: str,
) -> EcommercePaymentGatewayConfig | None:
    token = str(webhook_token or "").strip()
    if not token:
        return None
    return (
        db.query(EcommercePaymentGatewayConfig)
        .filter(
            EcommercePaymentGatewayConfig.provider == MERCADO_PAGO_PROVIDER,
            EcommercePaymentGatewayConfig.webhook_token == token,
        )
        .first()
    )


def _effective_webhook_secret(config: Any | None) -> str:
    if not config:
        return _global_mercado_pago_webhook_secret()
    return decrypt_secret(getattr(config, "webhook_secret_encrypted", None)) or _global_mercado_pago_webhook_secret()


def save_mercado_pago_oauth_tokens(
    config: Any,
    token_payload: dict[str, Any],
    *,
    connected_at: datetime | None = None,
) -> None:
    access_token = str(token_payload.get("access_token") or "").strip()
    refresh_token = str(token_payload.get("refresh_token") or "").strip()
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Mercado Pago nao retornou access_token no OAuth.",
        )

    now = connected_at or datetime.utcnow()
    expires_in = int(token_payload.get("expires_in") or 21600)
    config.access_token_encrypted = encrypt_secret(access_token)
    if refresh_token:
        config.refresh_token_encrypted = encrypt_secret(refresh_token)
    config.access_token_expires_at = now + timedelta(seconds=max(expires_in, 60))
    config.oauth_connected = True
    config.oauth_connected_at = now
    config.oauth_last_error = None
    config.oauth_refresh_failed_at = None

    user_id = token_payload.get("user_id") or token_payload.get("collector_id")
    if user_id is not None:
        config.mercado_pago_user_id = str(user_id)

    scope = str(token_payload.get("scope") or "").strip()
    if scope:
        config.oauth_scope = scope


def _token_expires_soon(config: Any, *, now: datetime | None = None) -> bool:
    expires_at = getattr(config, "access_token_expires_at", None)
    if not expires_at:
        return False
    reference = now or datetime.utcnow()
    if getattr(expires_at, "tzinfo", None) is not None:
        expires_at = expires_at.replace(tzinfo=None)
    return expires_at <= reference + timedelta(seconds=OAUTH_REFRESH_SKEW_SECONDS)


def refresh_mercado_pago_oauth_token(
    config: Any,
    *,
    http_post=requests.post,
) -> dict[str, Any]:
    refresh_token = decrypt_secret(getattr(config, "refresh_token_encrypted", None))
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token Mercado Pago nao configurado.",
        )
    if not is_mercado_pago_oauth_available(config):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth Mercado Pago nao configurado no servidor CorePet.",
        )

    payload = {
        "client_id": _oauth_client_id(config),
        "client_secret": _oauth_client_secret(config),
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = http_post(
        OAUTH_TOKEN_URL,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        json=payload,
        timeout=20,
    )
    if getattr(response, "status_code", 500) >= 300:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Mercado Pago recusou a renovacao OAuth: {getattr(response, 'text', '')[:300]}",
        )
    data = response.json()
    if not data.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Mercado Pago nao retornou access_token na renovacao OAuth.",
        )
    return data


def ensure_mercado_pago_access_token_fresh(
    db: Session,
    config: Any,
    *,
    http_post=requests.post,
) -> str:
    current_token = decrypt_secret(getattr(config, "access_token_encrypted", None))
    if not current_token:
        return ""
    if not getattr(config, "oauth_connected", False):
        return current_token
    if not _token_expires_soon(config):
        return current_token
    if not decrypt_secret(getattr(config, "refresh_token_encrypted", None)):
        return current_token

    try:
        token_payload = refresh_mercado_pago_oauth_token(config, http_post=http_post)
        save_mercado_pago_oauth_tokens(config, token_payload)
        db.commit()
        return decrypt_secret(getattr(config, "access_token_encrypted", None))
    except HTTPException as exc:
        config.oauth_last_error = str(exc.detail)
        config.oauth_refresh_failed_at = datetime.utcnow()
        db.commit()
        return current_token


def disconnect_mercado_pago_oauth_config(config: Any) -> None:
    config.enabled = False
    config.oauth_connected = False
    config.oauth_connected_at = None
    config.mercado_pago_user_id = None
    config.oauth_scope = None
    config.oauth_last_error = None
    config.oauth_refresh_failed_at = None
    config.access_token_encrypted = None
    config.refresh_token_encrypted = None
    config.access_token_expires_at = None


def save_mercado_pago_config(
    db: Session,
    *,
    tenant_id: str | UUID,
    user_id: int,
    enabled: bool,
    environment: str | None,
    public_key: str | None,
    access_token: str | None = None,
    webhook_secret: str | None = None,
    oauth_client_id: str | None = None,
    oauth_client_secret: str | None = None,
) -> EcommercePaymentGatewayConfig:
    config = get_mercado_pago_config(db, tenant_id)
    if not config:
        config = EcommercePaymentGatewayConfig(
            tenant_id=_normalize_tenant_id(tenant_id),
            provider=MERCADO_PAGO_PROVIDER,
            webhook_token=new_webhook_token(),
        )
        db.add(config)

    access_token_value = (access_token or "").strip()
    webhook_secret_value = (webhook_secret or "").strip()
    public_key_value = (public_key or "").strip()
    oauth_client_id_value = (oauth_client_id or "").strip()
    oauth_client_secret_value = (oauth_client_secret or "").strip()

    if public_key_value:
        config.public_key = public_key_value
    if access_token_value:
        config.access_token_encrypted = encrypt_secret(access_token_value)
        config.refresh_token_encrypted = None
        config.access_token_expires_at = None
        config.oauth_connected = False
        config.oauth_connected_at = None
        config.mercado_pago_user_id = None
        config.oauth_scope = None
        config.oauth_last_error = None
        config.oauth_refresh_failed_at = None
    if webhook_secret_value:
        config.webhook_secret_encrypted = encrypt_secret(webhook_secret_value)
    if oauth_client_id_value:
        config.oauth_client_id = oauth_client_id_value
    if oauth_client_secret_value:
        config.oauth_client_secret_encrypted = encrypt_secret(oauth_client_secret_value)

    if enabled:
        existing_access_token = decrypt_secret(config.access_token_encrypted)
        existing_oauth_settings = is_mercado_pago_oauth_available(config)
        existing_webhook_secret = _effective_webhook_secret(config)
        if not existing_access_token and not existing_oauth_settings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Access token ou Client ID/Client Secret OAuth do Mercado Pago "
                    "obrigatorios para ativar o pagamento online."
                ),
            )
        if not existing_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assinatura secreta do webhook Mercado Pago obrigatoria para ativar.",
            )

    config.enabled = bool(enabled)
    config.environment = _normalize_environment(environment)

    # Mantido para auditoria futura; a tabela nao expõe esse campo.
    _ = user_id

    db.commit()
    db.refresh(config)
    return config


def _runtime_config_from_gateway_config(
    db: Session,
    config: Any,
) -> MercadoPagoRuntimeConfig | None:
    if not config or not config.enabled:
        return None

    access_token = ensure_mercado_pago_access_token_fresh(db, config)
    webhook_secret = _effective_webhook_secret(config)
    if not access_token or not webhook_secret:
        return None

    return MercadoPagoRuntimeConfig(
        tenant_id=str(config.tenant_id),
        provider=MERCADO_PAGO_PROVIDER,
        enabled=True,
        environment=_normalize_environment(config.environment),
        public_key=config.public_key,
        access_token=access_token,
        webhook_secret=webhook_secret,
        webhook_token=config.webhook_token,
        webhook_url=build_mercado_pago_webhook_url(config.webhook_token),
    )


def get_active_mercado_pago_runtime_config(
    db: Session,
    tenant_id: str | UUID,
) -> MercadoPagoRuntimeConfig | None:
    config = get_mercado_pago_config(db, tenant_id)
    return _runtime_config_from_gateway_config(db, config)


def runtime_config_from_webhook_token(
    db: Session,
    webhook_token: str,
) -> MercadoPagoRuntimeConfig | None:
    config = get_mercado_pago_config_by_webhook_token(db, webhook_token)
    return _runtime_config_from_gateway_config(db, config)


def serialize_mercado_pago_config(
    config: Any | None,
    *,
    base_url: str | None = None,
) -> dict[str, Any]:
    if not config:
        token = new_webhook_token()
        env_oauth_client_id = _oauth_client_id()
        return {
            "provider": MERCADO_PAGO_PROVIDER,
            "enabled": False,
            "environment": "production",
            "public_key": None,
            "public_key_configured": False,
            "public_key_preview": None,
            "access_token_configured": False,
            "webhook_secret_configured": False,
            "oauth_client_id_configured": bool(env_oauth_client_id),
            "oauth_client_id_preview": _mask_config_value(env_oauth_client_id),
            "oauth_client_secret_configured": bool(_oauth_client_secret()),
            "oauth_available": is_mercado_pago_oauth_available(),
            "oauth_connected": False,
            "oauth_connected_at": None,
            "mercado_pago_user_id": None,
            "oauth_redirect_uri": build_mercado_pago_oauth_redirect_uri(base_url=base_url),
            "webhook_url": build_mercado_pago_webhook_url(token, base_url=base_url),
            "updated_at": None,
        }

    oauth_client_id = _oauth_client_id(config)
    public_key = str(getattr(config, "public_key", None) or "").strip()
    return {
        "provider": MERCADO_PAGO_PROVIDER,
        "enabled": bool(config.enabled),
        "environment": _normalize_environment(config.environment),
        "public_key": None,
        "public_key_configured": bool(public_key),
        "public_key_preview": _mask_config_value(public_key),
        "access_token_configured": bool(decrypt_secret(config.access_token_encrypted)),
        "webhook_secret_configured": bool(_effective_webhook_secret(config)),
        "oauth_client_id_configured": bool(oauth_client_id),
        "oauth_client_id_preview": _mask_config_value(oauth_client_id),
        "oauth_client_secret_configured": bool(_oauth_client_secret(config)),
        "oauth_available": is_mercado_pago_oauth_available(config),
        "oauth_connected": bool(getattr(config, "oauth_connected", False)),
        "oauth_connected_at": (
            config.oauth_connected_at.isoformat()
            if getattr(config, "oauth_connected_at", None)
            else None
        ),
        "mercado_pago_user_id": getattr(config, "mercado_pago_user_id", None),
        "oauth_redirect_uri": build_mercado_pago_oauth_redirect_uri(base_url=base_url),
        "webhook_url": build_mercado_pago_webhook_url(config.webhook_token, base_url=base_url),
        "updated_at": config.updated_at.isoformat() if getattr(config, "updated_at", None) else None,
    }
