"""Operacoes manuais do piloto Item, uma revisao e um produto por envio."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.config import settings
from app.db import get_session
from app.ifood_integration_models import IfoodMerchantConfig
from app.integrations.ifood import catalog_pilot as pilot
from app.routes.ifood_integration_routes import (
    _available_stocks,
    _client,
    _credentials_configured,
    _get_config,
    _products,
)
from app.security import permissions_service
from app.security.permissions_decorator import require_permission

router = APIRouter(prefix="/integracoes/ifood/catalogo/produtos", tags=["iFood"])
RESPONSES = {
    403: {"description": "Sem permissao na empresa"},
    404: {"description": "Produto nao encontrado"},
    409: {"description": "Conferencia, revisao ou configuracao divergente"},
    503: {"description": "Credenciais indisponiveis"},
}


class PortalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    merchant_id: UUID
    barcode: str = Field(min_length=8, max_length=13, pattern=r"^[0-9]+$")
    price: Decimal | None = Field(
        default=None, ge=0, le=1000000, decimal_places=2, allow_inf_nan=False
    )
    stock: Decimal | None = Field(
        default=None, ge=0, le=1000000, decimal_places=3, allow_inf_nan=False
    )
    portal_active: bool | None = None


class LinkBody(PortalEvidence):
    mode: Literal["existing", "new"]
    portal_checked: bool = False


class ConfirmationBody(PortalEvidence):
    present: bool
    confirmation_context_token: str | None = Field(
        default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]+$"
    )


class PrepareBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["create", "update"]
    fields: list[Literal["price", "stock"]] = Field(default_factory=list, max_length=2)


class SendBody(PrepareBody):
    review_token: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]+$")
    request_key: UUID
    confirm_send: bool = False


def _can_edit(db, user, tenant_id):
    try:
        permissions_service.check_permission(
            db, user.id, "produtos.editar", tenant_id, current_user=user
        )
        return True
    except HTTPException as exc:
        if exc.status_code == 403:
            return False
        raise


def _state(db, tenant_id, product_id, *, lock=False):
    config = _get_config(db, tenant_id)
    if lock and config:
        config = (
            db.query(IfoodMerchantConfig)
            .filter(IfoodMerchantConfig.tenant_id == tenant_id)
            .populate_existing()
            .with_for_update()
            .one()
        )
    products = _products(db, tenant_id, [product_id])
    if not products:
        raise HTTPException(404, "Produto nao encontrado nesta empresa.")
    return config, products[0]


def _view(db, tenant_id, config, product, user):
    return pilot.publication_view(
        db,
        tenant_id,
        config,
        product,
        can_edit=_can_edit(db, user, tenant_id),
        write_enabled=settings.IFOOD_CATALOG_WRITE_ENABLED,
        credentials=_credentials_configured(),
    )


def _prepare(db, tenant_id, config, product, body):
    stocks = _available_stocks(db, tenant_id, [product])
    return pilot.prepare(
        db,
        tenant_id,
        config,
        product,
        stocks.get(product.id),
        body.operation,
        body.fields,
        can_edit=True,
        write_enabled=settings.IFOOD_CATALOG_WRITE_ENABLED,
        credentials=_credentials_configured(),
        public_base_url=settings.COREPET_FRONTEND_URL,
    )


def _commit(db):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            409,
            "Este EAN ja esta vinculado a outro produto ou a revisao mudou. Confira novamente.",
        ) from exc


@router.get("/{product_id}/publicacao", responses=RESPONSES)
@require_permission("produtos.visualizar")
def get_publication(
    product_id: int,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    user, tenant_id = user_and_tenant
    config, product = _state(db, tenant_id, product_id)
    return _view(db, tenant_id, config, product, user)


@router.put("/{product_id}/vinculo", responses=RESPONSES)
@require_permission("produtos.editar")
def put_link(
    product_id: int,
    body: LinkBody,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    user, tenant_id = user_and_tenant
    config, product = _state(db, tenant_id, product_id, lock=True)
    try:
        pilot.record_link(
            db, tenant_id, config, product, body.model_dump(mode="python"), user.id
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            409,
            "Este EAN ja esta vinculado a outro produto da loja. Confira novamente.",
        ) from exc
    _commit(db)
    return _view(db, tenant_id, config, product, user)


@router.post("/{product_id}/preparar", responses=RESPONSES)
@require_permission("produtos.editar")
def prepare_publication(
    product_id: int,
    body: PrepareBody,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    _, tenant_id = user_and_tenant
    config, product = _state(db, tenant_id, product_id)
    return _prepare(db, tenant_id, config, product, body)


@router.post("/{product_id}/enviar", responses=RESPONSES)
@require_permission("produtos.editar")
def send_publication(
    product_id: int,
    body: SendBody,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    user, tenant_id = user_and_tenant
    config, product = _state(db, tenant_id, product_id, lock=True)
    prepared = _prepare(db, tenant_id, config, product, body)
    if not body.confirm_send:
        return prepared
    if not settings.IFOOD_CATALOG_WRITE_ENABLED:
        raise HTTPException(409, "Envios ao iFood estao desabilitados no servidor.")
    if not config or not config.active or not config.merchant_id:
        raise HTTPException(409, "Ative a integracao e confira a loja antes de enviar.")
    if not _credentials_configured():
        raise HTTPException(503, "Credenciais iFood nao configuradas no servidor.")
    try:
        row, replayed = pilot.send_prepared(
            db,
            tenant_id,
            config,
            product,
            prepared,
            review_token=body.review_token,
            request_key=str(body.request_key),
            actor_id=user.id,
            client_factory=_client,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            409,
            "Ja existe um envio desta revisao. Reabra o historico antes de tentar novamente.",
        ) from exc
    return {
        "dry_run": False,
        "replayed": replayed,
        "status": row.status,
        "submission": pilot.submission_view(row),
        "publication": _view(db, tenant_id, config, product, user),
    }


@router.post("/{product_id}/confirmar-portal", responses=RESPONSES)
@require_permission("produtos.editar")
def confirm_publication(
    product_id: int,
    body: ConfirmationBody,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    user, tenant_id = user_and_tenant
    config, product = _state(db, tenant_id, product_id, lock=True)
    pilot.confirm_portal(
        db, tenant_id, config, product, body.model_dump(mode="python"), user.id
    )
    _commit(db)
    return _view(db, tenant_id, config, product, user)
