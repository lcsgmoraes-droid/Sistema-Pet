"""Servicos para configuracao de pagamentos do e-commerce por tenant."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import JWT_SECRET_KEY
from app.ecommerce_payment_models import EcommercePaymentGatewayConfig


MERCADO_PAGO_PROVIDER = "mercadopago"
VALID_ENVIRONMENTS = {"production", "sandbox"}
SECRET_PREFIX = "fernet:"


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


def _normalize_tenant_id(tenant_id: str | UUID) -> UUID:
    return tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))


def _fernet_key() -> bytes:
    raw_secret = (
        os.getenv("PAYMENT_CONFIG_ENCRYPTION_KEY")
        or os.getenv("ENCRYPTION_KEY")
        or JWT_SECRET_KEY
        or "corepet-local-payment-config-key"
    ).strip()
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

    if access_token_value:
        config.access_token_encrypted = encrypt_secret(access_token_value)
    if webhook_secret_value:
        config.webhook_secret_encrypted = encrypt_secret(webhook_secret_value)

    if enabled:
        existing_access_token = decrypt_secret(config.access_token_encrypted)
        existing_webhook_secret = decrypt_secret(config.webhook_secret_encrypted)
        if not existing_access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access token do Mercado Pago obrigatorio para ativar o pagamento online.",
            )
        if not existing_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assinatura secreta do webhook Mercado Pago obrigatoria para ativar.",
            )

    config.enabled = bool(enabled)
    config.environment = _normalize_environment(environment)
    config.public_key = str(public_key or "").strip() or None

    # Mantido para auditoria futura; a tabela nao expõe esse campo.
    _ = user_id

    db.commit()
    db.refresh(config)
    return config


def get_active_mercado_pago_runtime_config(
    db: Session,
    tenant_id: str | UUID,
) -> MercadoPagoRuntimeConfig | None:
    config = get_mercado_pago_config(db, tenant_id)
    if not config or not config.enabled:
        return None

    access_token = decrypt_secret(config.access_token_encrypted)
    webhook_secret = decrypt_secret(config.webhook_secret_encrypted)
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


def runtime_config_from_webhook_token(
    db: Session,
    webhook_token: str,
) -> MercadoPagoRuntimeConfig | None:
    config = get_mercado_pago_config_by_webhook_token(db, webhook_token)
    if not config or not config.enabled:
        return None

    access_token = decrypt_secret(config.access_token_encrypted)
    webhook_secret = decrypt_secret(config.webhook_secret_encrypted)
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


def serialize_mercado_pago_config(
    config: Any | None,
    *,
    base_url: str | None = None,
) -> dict[str, Any]:
    if not config:
        token = new_webhook_token()
        return {
            "provider": MERCADO_PAGO_PROVIDER,
            "enabled": False,
            "environment": "production",
            "public_key": None,
            "access_token_configured": False,
            "webhook_secret_configured": False,
            "webhook_url": build_mercado_pago_webhook_url(token, base_url=base_url),
            "updated_at": None,
        }

    return {
        "provider": MERCADO_PAGO_PROVIDER,
        "enabled": bool(config.enabled),
        "environment": _normalize_environment(config.environment),
        "public_key": config.public_key,
        "access_token_configured": bool(decrypt_secret(config.access_token_encrypted)),
        "webhook_secret_configured": bool(decrypt_secret(config.webhook_secret_encrypted)),
        "webhook_url": build_mercado_pago_webhook_url(config.webhook_token, base_url=base_url),
        "updated_at": config.updated_at.isoformat() if getattr(config, "updated_at", None) else None,
    }
