"""Ponte interna somente leitura para o piloto local do WhatsApp."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import case, or_
from sqlalchemy.orm import Session, joinedload

from app.api.whatsapp_orchestrator_internal_routes import (
    _parse_tenant_uuid,
    _validate_internal_token,
)
from app.db import get_session
from app.tenancy.context import clear_current_tenant, set_current_tenant


router = APIRouter(
    prefix="/internal/whatsapp-orchestrator",
    tags=["whatsapp-data-internal"],
)


def _normalize_text(value: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    ).lower()


def _phone_digits(value: str) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


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
                "image_url": (
                    str(product.imagem_principal or "") if product else ""
                ),
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
            digits = _phone_digits(phone)
            if len(digits) >= 8:
                last_four = digits[-4:]
                candidates = (
                    db.query(Cliente)
                    .filter(
                        Cliente.tenant_id == tenant_uuid,
                        or_(
                            Cliente.celular.ilike(f"%{last_four}%"),
                            Cliente.telefone.ilike(f"%{last_four}%"),
                        ),
                    )
                    .limit(20)
                    .all()
                )
                matches = [
                    candidate
                    for candidate in candidates
                    if any(
                        _phone_digits(value).endswith(digits[-8:])
                        for value in (candidate.celular, candidate.telefone)
                        if value
                    )
                ]
                if len(matches) == 1:
                    customer = matches[0]

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
            "store": (
                {"id": str(tenant.id), "name": tenant.name} if tenant else None
            ),
            "store_hours": hours,
        }
    finally:
        clear_current_tenant()
