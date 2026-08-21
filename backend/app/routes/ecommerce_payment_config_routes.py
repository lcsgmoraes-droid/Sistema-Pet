"""Rotas de configuracao de pagamento online do e-commerce."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict
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
    get_mercado_pago_account_identity,
    get_mercado_pago_config,
    is_mercado_pago_connection_available,
    new_webhook_token,
    save_mercado_pago_config,
    save_mercado_pago_oauth_tokens,
    serialize_mercado_pago_config,
    validate_mercado_pago_oauth_state,
)
from app.ecommerce_payment_models import EcommercePaymentGatewayConfig
from app.tenancy.context import set_current_tenant


router = APIRouter(
    prefix="/ecommerce-payment-config", tags=["ecommerce-payment-config"]
)
public_router = APIRouter(
    prefix="/ecommerce-payment-config", tags=["ecommerce-payment-config"]
)


class MercadoPagoConfigResponse(BaseModel):
    provider: str
    enabled: bool
    access_token_configured: bool
    oauth_available: bool
    oauth_connected: bool
    oauth_connected_at: Optional[str]
    mercado_pago_user_id: Optional[str]
    updated_at: Optional[str]


class MercadoPagoConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False


class MercadoPagoOAuthUrlResponse(BaseModel):
    configured: bool
    authorization_url: Optional[str] = None


class MercadoPagoAccountIdentityResponse(BaseModel):
    verified: bool
    mercado_pago_user_id: Optional[str]
    account_holder: Optional[str]
    email_masked: Optional[str]
    identification_type: Optional[str]
    identification_last_four: Optional[str]


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


@router.get(
    "/mercadopago/account-identity",
    response_model=MercadoPagoAccountIdentityResponse,
)
def buscar_identidade_conta_mercado_pago(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Confirma no Mercado Pago a identidade da conta autorizada pelo tenant."""
    _, tenant_id = user_and_tenant
    config = _ensure_config(db, tenant_id=tenant_id)
    return get_mercado_pago_account_identity(db, config)


@router.get("/mercadopago/oauth/url", response_model=MercadoPagoOAuthUrlResponse)
def gerar_url_oauth_mercado_pago(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Gera URL para o tenant conectar sua conta Mercado Pago via OAuth."""
    current_user, tenant_id = user_and_tenant
    config = _ensure_config(db, tenant_id=tenant_id)
    redirect_uri = build_mercado_pago_oauth_redirect_uri()
    if not is_mercado_pago_connection_available(config):
        return MercadoPagoOAuthUrlResponse(
            configured=False,
            authorization_url=None,
        )
    return MercadoPagoOAuthUrlResponse(
        configured=True,
        authorization_url=build_mercado_pago_oauth_authorization_url(
            tenant_id=tenant_id,
            user_id=current_user.id,
            redirect_uri=redirect_uri,
            config=config,
        ),
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
            build_mercado_pago_oauth_return_url(
                "error", message="state invalido ou expirado"
            ),
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
            config.webhook_secret_encrypted
            or serialize_mercado_pago_config(config)["webhook_secret_configured"]
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
    """Atualiza somente a preferência de pagamento do tenant."""
    current_user, tenant_id = user_and_tenant
    config = save_mercado_pago_config(
        db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        enabled=body.enabled,
        environment=None,
        public_key=None,
        access_token=None,
        webhook_secret=None,
        oauth_client_id=None,
        oauth_client_secret=None,
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
