"""Ponte interna protegida entre o piloto do WhatsApp e o CorePet."""

from __future__ import annotations

import os
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import case, or_
from sqlalchemy.orm import Session, joinedload

from app.api.whatsapp_orchestrator_internal_routes import (
    _parse_tenant_uuid,
    _validate_internal_token,
)
from app.db import get_session
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.whatsapp.order_checkout_service import (
    WhatsAppOrderCreateData,
    WhatsAppOrderPreviewData,
    build_order_preview as _build_order_preview,
    create_order as _create_order,
    customer_delivery_address as _customer_delivery_address,
    phone_digits,
    resolve_customer as _resolve_customer,
)

router = APIRouter(
    prefix="/internal/whatsapp-orchestrator",
    tags=["whatsapp-data-internal"],
)


def _normalize_text(value: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        character for character in normalized if not unicodedata.combining(character)
    ).lower()


def _phone_digits(value: str) -> str:
    return phone_digits(value)


def _validate_internal_write_token(value: Optional[str]) -> None:
    expected = (os.getenv("WHATSAPP_ORCHESTRATOR_WRITE_TOKEN") or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Canal interno de escrita não configurado.",
        )
    if not value or not secrets.compare_digest(value.strip(), expected):
        raise HTTPException(
            status_code=401, detail="Token interno de escrita inválido."
        )


def _latest_purchase(db: Session, tenant_id: str, customer_id: int):
    from app.produtos_models import Produto
    from app.vendas_models import Venda, VendaItem

    sale = (
        db.query(Venda)
        .options(joinedload(Venda.itens).joinedload(VendaItem.produto))
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.cliente_id == customer_id,
            Venda.status == "finalizada",
        )
        .order_by(Venda.data_venda.desc(), Venda.id.desc())
        .first()
    )
    if not sale:
        return None

    items = []
    for item in sale.itens or []:
        product: Optional[Produto] = item.produto
        items.append(
            {
                "product_id": item.produto_id,
                "name": (
                    product.nome
                    if product and product.nome
                    else item.servico_descricao or "Item"
                ),
                "quantity": float(item.quantidade or 0),
                "unit_price": float(item.preco_unitario or 0),
                "image_url": (str(product.imagem_principal or "") if product else ""),
            }
        )
    if not items:
        return None
    return {
        "sale_id": sale.id,
        "number": sale.numero_venda,
        "date": sale.data_venda,
        "total": float(sale.total or 0),
        "items": items,
    }


def _latest_delivery(db: Session, tenant_id: str, customer_id: int):
    from app.vendas_models import Venda

    sale = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.cliente_id == customer_id,
            Venda.tem_entrega.is_(True),
            Venda.status != "cancelada",
            Venda.status_entrega.isnot(None),
        )
        .order_by(Venda.data_venda.desc(), Venda.id.desc())
        .first()
    )
    if not sale:
        return None
    return {
        "sale_id": sale.id,
        "number": sale.numero_venda,
        "date": sale.data_venda,
        "status": sale.status_entrega,
        "delivered_at": sale.data_entrega,
    }


@router.get("/{tenant_id}/catalog-data")
def get_catalog_data(
    tenant_id: str,
    query: str = Query(min_length=1, max_length=180),
    categoria: Optional[str] = Query(default=None, max_length=100),
    limit: int = Query(default=5, ge=1, le=15),
    x_internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
    db: Session = Depends(get_session),
):
    """Consulta produtos do tenant, sem executar qualquer gravação."""
    from app.produtos_models import Categoria, Produto

    _validate_internal_token(x_internal_token)
    tenant_uuid = _parse_tenant_uuid(tenant_id)
    set_current_tenant(tenant_uuid)
    try:
        tokens = [token for token in _normalize_text(query).split() if token]
        product_query = db.query(Produto).filter(
            Produto.tenant_id == tenant_uuid,
            Produto.situacao.is_(True),
            Produto.tipo_produto != "PAI",
        )
        for token in tokens:
            token_like = f"%{token}%"
            product_query = product_query.filter(
                or_(
                    Produto.nome.ilike(token_like),
                    Produto.descricao_curta.ilike(token_like),
                    Produto.codigo.ilike(token_like),
                    Produto.codigo_barras.ilike(token_like),
                )
            )

        if categoria:
            category = (
                db.query(Categoria)
                .filter(
                    Categoria.tenant_id == tenant_uuid,
                    Categoria.nome.ilike(f"%{categoria.strip()}%"),
                )
                .first()
            )
            if category:
                product_query = product_query.filter(
                    Produto.categoria_id == category.id
                )

        products = (
            product_query.order_by(
                case((Produto.estoque_atual > 0, 0), else_=1),
                Produto.nome.asc(),
            )
            .limit(limit)
            .all()
        )
        serialized = [
            {
                "id": str(product.id),
                "nome": product.nome,
                "sku": product.codigo or "",
                "ean": product.codigo_barras or "",
                "preco": float(product.preco_venda or 0),
                "estoque": float(product.estoque_atual or 0),
                "estoque_disponivel": bool((product.estoque_atual or 0) > 0),
                "descricao": product.descricao_curta or "",
                "imagem_url": product.imagem_principal or "",
            }
            for product in products
        ]
        return {"success": True, "produtos": serialized, "total": len(serialized)}
    finally:
        clear_current_tenant()


@router.get("/{tenant_id}/customer-context-data")
def get_customer_context_data(
    tenant_id: str,
    phone: Optional[str] = Query(default=None, max_length=30),
    customer_id: Optional[int] = Query(default=None, ge=1),
    x_internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
    db: Session = Depends(get_session),
):
    """Consulta cliente e histórico necessário ao atendimento, sem gravar."""
    from app.models import Cliente

    _validate_internal_token(x_internal_token)
    tenant_uuid = _parse_tenant_uuid(tenant_id)
    set_current_tenant(tenant_uuid)
    try:
        customer = None
        if customer_id is not None:
            customer = (
                db.query(Cliente)
                .filter(
                    Cliente.tenant_id == tenant_uuid,
                    Cliente.id == customer_id,
                )
                .first()
            )
        elif phone:
            customer = _resolve_customer(db, tenant_uuid, phone=phone)

        if not customer:
            return {
                "success": True,
                "customer": None,
                "latest_purchase": None,
                "latest_delivery": None,
                "benefits": {},
            }

        return {
            "success": True,
            "customer": {
                "id": customer.id,
                "name": customer.nome or "",
                "phone": customer.celular or customer.telefone or "",
                "store_credit": float(customer.credito or 0),
                "delivery_address": _customer_delivery_address(customer),
            },
            "latest_purchase": _latest_purchase(db, tenant_id, customer.id),
            "latest_delivery": _latest_delivery(db, tenant_id, customer.id),
            "benefits": {},
        }
    finally:
        clear_current_tenant()


@router.get("/{tenant_id}/store-context-data")
def get_store_context_data(
    tenant_id: str,
    x_internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
    db: Session = Depends(get_session),
):
    """Consulta nome e horário cadastrados da loja, sem gravar."""
    from app.models import Tenant
    from app.whatsapp.models import TenantWhatsAppConfig

    _validate_internal_token(x_internal_token)
    tenant_uuid = _parse_tenant_uuid(tenant_id)
    set_current_tenant(tenant_uuid)
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_uuid).first()
        config = (
            db.query(TenantWhatsAppConfig)
            .filter(TenantWhatsAppConfig.tenant_id == tenant_uuid)
            .first()
        )
        hours = None
        if config and config.working_hours_start and config.working_hours_end:
            hours = {
                "start": config.working_hours_start.strftime("%H:%M"),
                "end": config.working_hours_end.strftime("%H:%M"),
            }
        elif (
            tenant
            and tenant.ecommerce_horario_abertura
            and tenant.ecommerce_horario_fechamento
        ):
            hours = {
                "start": str(tenant.ecommerce_horario_abertura),
                "end": str(tenant.ecommerce_horario_fechamento),
            }
        return {
            "success": True,
            "store": ({"id": str(tenant.id), "name": tenant.name} if tenant else None),
            "store_hours": hours,
        }
    finally:
        clear_current_tenant()


@router.post("/{tenant_id}/order-preview-data")
def preview_order_data(
    tenant_id: str,
    data: WhatsAppOrderPreviewData,
    x_internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
    db: Session = Depends(get_session),
):
    """Valida itens e calcula o resumo real sem criar venda ou baixar estoque."""
    _validate_internal_token(x_internal_token)
    tenant_uuid = _parse_tenant_uuid(tenant_id)
    set_current_tenant(tenant_uuid)
    try:
        return _build_order_preview(
            db,
            tenant_uuid,
            phone=data.phone,
            requested_items=data.items,
        )
    finally:
        clear_current_tenant()


@router.post("/{tenant_id}/order-create-data")
def create_order_data(
    tenant_id: str,
    data: WhatsAppOrderCreateData,
    x_internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
    x_internal_write_token: Optional[str] = Header(
        default=None, alias="X-Internal-Write-Token"
    ),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_session),
):
    """Cria uma única venda em aberto após a confirmação explícita do cliente."""
    _validate_internal_token(x_internal_token)
    _validate_internal_write_token(x_internal_write_token)
    if not idempotency_key or len(idempotency_key) < 16:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key é obrigatório e deve ter ao menos 16 caracteres.",
        )

    tenant_uuid = _parse_tenant_uuid(tenant_id)
    set_current_tenant(tenant_uuid)
    try:
        return _create_order(
            db,
            tenant_uuid,
            data=data,
            idempotency_key=idempotency_key,
            preview_builder=_build_order_preview,
        )
    finally:
        clear_current_tenant()
