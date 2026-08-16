"""Consultas somente leitura do CorePet usadas pelo atendimento do WhatsApp."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app.models import Cliente, Tenant
from app.produtos_models import Produto
from app.vendas_models import Venda, VendaItem
from app.whatsapp.models import TenantWhatsAppConfig, WhatsAppSession
from app.whatsapp.remote_corepet_client import (
    fetch_remote_customer_context,
    fetch_remote_store_context,
    remote_data_enabled,
)


def _digits(value: Any) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def resolve_session_customer(
    db,
    *,
    tenant_id: str,
    session: WhatsAppSession,
) -> Optional[Cliente]:
    """Resolve um cliente apenas quando o vínculo ou o telefone forem inequívocos."""
    if remote_data_enabled():
        payload = fetch_remote_customer_context(
            tenant_id,
            phone=session.phone_number,
        )
        if payload is not None:
            customer = payload.get("customer")
            if not isinstance(customer, dict):
                return None
            return SimpleNamespace(
                id=int(customer["id"]),
                nome=str(customer.get("name") or ""),
                celular=str(customer.get("phone") or ""),
                telefone=str(customer.get("phone") or ""),
                credito=float(customer.get("store_credit") or 0),
                _remote_source=True,
            )

    if session.cliente_id:
        return (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.id == session.cliente_id,
            )
            .first()
        )

    phone_digits = _digits(session.phone_number)
    if len(phone_digits) < 8:
        return None

    last_four = phone_digits[-4:]
    candidates = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            or_(
                Cliente.celular.ilike(f"%{last_four}%"),
                Cliente.telefone.ilike(f"%{last_four}%"),
            ),
        )
        .limit(20)
        .all()
    )
    matched = [
        customer
        for customer in candidates
        if any(
            _digits(phone).endswith(phone_digits[-8:])
            for phone in (customer.celular, customer.telefone)
            if phone
        )
    ]
    if len(matched) != 1:
        return None

    return matched[0]


def load_latest_purchase(db, *, tenant_id: str, customer_id: int) -> Optional[dict]:
    """Carrega a compra concluída mais recente com itens e fotos reais."""
    if remote_data_enabled():
        payload = fetch_remote_customer_context(
            tenant_id,
            customer_id=customer_id,
        )
        if payload is not None:
            purchase = payload.get("latest_purchase")
            return purchase if isinstance(purchase, dict) else None

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
        name = (
            product.nome
            if product and product.nome
            else item.servico_descricao or "Item"
        )
        items.append(
            {
                "product_id": item.produto_id,
                "name": name,
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


def load_latest_delivery(db, *, tenant_id: str, customer_id: int) -> Optional[dict]:
    """Carrega o status de entrega mais recente registrado no CorePet."""
    if remote_data_enabled():
        payload = fetch_remote_customer_context(
            tenant_id,
            customer_id=customer_id,
        )
        if payload is not None:
            delivery = payload.get("latest_delivery")
            return delivery if isinstance(delivery, dict) else None

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


def load_customer_benefits(db, *, tenant_id: str, customer: Cliente) -> dict:
    """Consulta crédito, cashback, carimbos e cupons digitais do cliente."""
    if remote_data_enabled():
        payload = fetch_remote_customer_context(
            tenant_id,
            customer_id=customer.id,
        )
        if payload is not None:
            benefits = payload.get("benefits")
            return benefits if isinstance(benefits, dict) else {}

    from app.campaigns.loyalty_service import (
        summarize_loyalty_balances_for_customer,
    )
    from app.campaigns.models import (
        CashbackTransaction,
        Coupon,
        CouponStatusEnum,
    )

    now = datetime.now(timezone.utc)
    cashback_raw = (
        db.query(func.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == customer.id,
            or_(
                CashbackTransaction.expires_at.is_(None),
                CashbackTransaction.expires_at > now,
                CashbackTransaction.tx_type != "credit",
            ),
        )
        .scalar()
    )
    loyalty = summarize_loyalty_balances_for_customer(
        db,
        tenant_id=tenant_id,
        customer_id=customer.id,
    )
    coupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.customer_id == customer.id,
            Coupon.status == CouponStatusEnum.active,
            or_(Coupon.valid_until.is_(None), Coupon.valid_until > now),
        )
        .order_by(Coupon.created_at.desc(), Coupon.id.desc())
        .limit(5)
        .all()
    )

    return {
        "store_credit": float(customer.credito or 0),
        "cashback": max(0.0, float(cashback_raw or 0)),
        "loyalty_stamps": max(0, int(loyalty.get("total_carimbos") or 0)),
        "coupons": [
            {
                "code": coupon.code,
                "type": getattr(coupon.coupon_type, "value", coupon.coupon_type),
                "discount_value": (
                    float(coupon.discount_value)
                    if coupon.discount_value is not None
                    else None
                ),
                "discount_percent": (
                    float(coupon.discount_percent)
                    if coupon.discount_percent is not None
                    else None
                ),
                "valid_until": coupon.valid_until,
            }
            for coupon in coupons
        ],
    }


def load_store_hours(db, *, tenant_id: str) -> Optional[dict[str, str]]:
    """Retorna horário somente quando ele estiver cadastrado no CorePet."""
    if remote_data_enabled():
        payload = fetch_remote_store_context(tenant_id)
        if payload is not None:
            hours = payload.get("store_hours")
            return hours if isinstance(hours, dict) else None

    config = (
        db.query(TenantWhatsAppConfig)
        .filter(TenantWhatsAppConfig.tenant_id == tenant_id)
        .first()
    )
    if config and config.working_hours_start and config.working_hours_end:
        return {
            "start": config.working_hours_start.strftime("%H:%M"),
            "end": config.working_hours_end.strftime("%H:%M"),
        }

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if (
        tenant
        and tenant.ecommerce_horario_abertura
        and tenant.ecommerce_horario_fechamento
    ):
        return {
            "start": str(tenant.ecommerce_horario_abertura),
            "end": str(tenant.ecommerce_horario_fechamento),
        }

    return None
