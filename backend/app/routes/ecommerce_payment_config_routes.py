"""Rotas de configuracao de pagamento online do e-commerce."""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.services.ecommerce_payment_config import (
    MERCADO_PAGO_PROVIDER,
    get_mercado_pago_config,
    new_webhook_token,
    save_mercado_pago_config,
    serialize_mercado_pago_config,
)
from app.ecommerce_payment_models import EcommercePaymentGatewayConfig


router = APIRouter(prefix="/ecommerce-payment-config", tags=["ecommerce-payment-config"])


class MercadoPagoConfigResponse(BaseModel):
    provider: str
    enabled: bool
    environment: str
    public_key: Optional[str]
    access_token_configured: bool
    webhook_secret_configured: bool
    webhook_url: str
    updated_at: Optional[str]


class MercadoPagoConfigUpdate(BaseModel):
    enabled: bool = False
    environment: str = Field(default="production")
    public_key: Optional[str] = None
    access_token: Optional[str] = None
    webhook_secret: Optional[str] = None


def _ensure_config(
    db: Session,
    *,
    tenant_id,
) -> EcommercePaymentGatewayConfig:
    config = get_mercado_pago_config(db, tenant_id)
    if config:
        return config

    config = EcommercePaymentGatewayConfig(
        tenant_id=tenant_id,
        provider=MERCADO_PAGO_PROVIDER,
        enabled=False,
        environment="production",
        webhook_token=new_webhook_token(),
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.get("/mercadopago", response_model=MercadoPagoConfigResponse)
def buscar_config_mercado_pago(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Retorna configuracao Mercado Pago do tenant sem expor segredos."""
    _, tenant_id = user_and_tenant
    config = _ensure_config(db, tenant_id=tenant_id)
    return serialize_mercado_pago_config(config)


@router.put("/mercadopago", response_model=MercadoPagoConfigResponse)
def salvar_config_mercado_pago(
    body: MercadoPagoConfigUpdate,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Salva credenciais Mercado Pago do tenant sem retornar valores sensiveis."""
    current_user, tenant_id = user_and_tenant
    config = save_mercado_pago_config(
        db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        enabled=body.enabled,
        environment=body.environment,
        public_key=body.public_key,
        access_token=body.access_token,
        webhook_secret=body.webhook_secret,
    )
    return serialize_mercado_pago_config(config)
