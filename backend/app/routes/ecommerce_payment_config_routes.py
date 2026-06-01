"""Rotas de configuracao de pagamento online do e-commerce."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.services.ecommerce_payment_config import (
    MERCADO_PAGO_PROVIDER,
    build_mercado_pago_oauth_authorization_url,
    build_mercado_pago_oauth_redirect_uri,
    build_mercado_pago_oauth_return_url,
    disconnect_mercado_pago_oauth_config,
    exchange_mercado_pago_oauth_code,
    get_mercado_pago_config,
    is_mercado_pago_oauth_available,
    missing_mercado_pago_oauth_settings,
    new_webhook_token,
    save_mercado_pago_config,
    save_mercado_pago_oauth_tokens,
    serialize_mercado_pago_config,
    validate_mercado_pago_oauth_state,
)
from app.ecommerce_payment_models import EcommercePaymentGatewayConfig
from app.tenancy.context import set_current_tenant


router = APIRouter(prefix="/ecommerce-payment-config", tags=["ecommerce-payment-config"])
public_router = APIRouter(prefix="/ecommerce-payment-config", tags=["ecommerce-payment-config"])


class MercadoPagoConfigResponse(BaseModel):
    provider: str
    enabled: bool
    environment: str
    public_key: Optional[str]
    public_key_configured: bool
    public_key_preview: Optional[str]
    access_token_configured: bool
    webhook_secret_configured: bool
    oauth_client_id_configured: bool
    oauth_client_id_preview: Optional[str]
    oauth_client_secret_configured: bool
    oauth_available: bool
    oauth_connected: bool
    oauth_connected_at: Optional[str]
    mercado_pago_user_id: Optional[str]
    oauth_redirect_uri: str
    webhook_url: str
    updated_at: Optional[str]


class MercadoPagoConfigUpdate(BaseModel):
    enabled: bool = False
    environment: str = Field(default="production")
    public_key: Optional[str] = None
    access_token: Optional[str] = None
    webhook_secret: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None


class MercadoPagoOAuthUrlResponse(BaseModel):
    configured: bool
    authorization_url: Optional[str] = None
    redirect_uri: str
    missing: list[str] = Field(default_factory=list)


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


@router.get("/mercadopago/oauth/url", response_model=MercadoPagoOAuthUrlResponse)
def gerar_url_oauth_mercado_pago(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Gera URL para o tenant conectar sua conta Mercado Pago via OAuth."""
    current_user, tenant_id = user_and_tenant
    config = _ensure_config(db, tenant_id=tenant_id)
    redirect_uri = build_mercado_pago_oauth_redirect_uri()
    if not is_mercado_pago_oauth_available(config):
        return MercadoPagoOAuthUrlResponse(
            configured=False,
            authorization_url=None,
            redirect_uri=redirect_uri,
            missing=missing_mercado_pago_oauth_settings(config),
        )
    return MercadoPagoOAuthUrlResponse(
        configured=True,
        authorization_url=build_mercado_pago_oauth_authorization_url(
            tenant_id=tenant_id,
            user_id=current_user.id,
            redirect_uri=redirect_uri,
            config=config,
        ),
        redirect_uri=redirect_uri,
        missing=[],
    )


@public_router.get("/mercadopago/oauth/callback")
def callback_oauth_mercado_pago(
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_session),
):
    """Recebe o retorno OAuth do Mercado Pago e salva tokens no tenant."""
    if error:
        return RedirectResponse(
            build_mercado_pago_oauth_return_url("error", message=error),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    state_payload = validate_mercado_pago_oauth_state(state)
    if not state_payload:
        return RedirectResponse(
            build_mercado_pago_oauth_return_url("error", message="state invalido ou expirado"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if not code:
        return RedirectResponse(
            build_mercado_pago_oauth_return_url("error", message="codigo nao recebido"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    tenant_id = state_payload["tenant_id"]
    set_current_tenant(UUID(str(tenant_id)))
    config = _ensure_config(db, tenant_id=tenant_id)
    try:
        token_payload = exchange_mercado_pago_oauth_code(
            code=code,
            redirect_uri=build_mercado_pago_oauth_redirect_uri(),
            environment=config.environment,
            config=config,
        )
        save_mercado_pago_oauth_tokens(config, token_payload)
        if config.access_token_encrypted and (
            config.webhook_secret_encrypted or serialize_mercado_pago_config(config)["webhook_secret_configured"]
        ):
            config.enabled = True
        db.commit()
    except HTTPException as exc:
        db.rollback()
        return RedirectResponse(
            build_mercado_pago_oauth_return_url("error", message=str(exc.detail)),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        build_mercado_pago_oauth_return_url("connected"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


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
        oauth_client_id=body.oauth_client_id,
        oauth_client_secret=body.oauth_client_secret,
    )
    return serialize_mercado_pago_config(config)


@router.post("/mercadopago/oauth/disconnect", response_model=MercadoPagoConfigResponse)
def desconectar_oauth_mercado_pago(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Remove tokens OAuth do tenant e desativa pagamento online."""
    _, tenant_id = user_and_tenant
    config = _ensure_config(db, tenant_id=tenant_id)
    disconnect_mercado_pago_oauth_config(config)
    db.commit()
    db.refresh(config)
    return serialize_mercado_pago_config(config)
