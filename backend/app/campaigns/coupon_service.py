"""
Servico de cupons do Campaign Engine.

Responsabilidades:
- gerar codigo unico por tenant
- validar cupom para pre-visualizacao no PDV
- consumir cupom apenas no fechamento atomico da venda
- reverter redemptions em cancelamento/reabertura
- oferecer utilitarios de backfill para redemptions antigos sem venda_id
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.campaigns.audit import (
    build_coupon_audit_metadata,
    build_coupon_redemption_audit_metadata,
    log_campaign_event,
)
from app.campaigns.models import (
    Campaign,
    Coupon,
    CouponChannelEnum,
    CouponRedemption,
    CouponStatusEnum,
    CouponTypeEnum,
)
from app.campaigns.coupon_rules import (
    _MONEY_CENTS,
    _as_decimal,
    _calculate_coupon_discount,
    _coupon_is_expired,
    _generate_code,
    _normalize_coupon_code,
    _restored_coupon_status,
)

logger = logging.getLogger(__name__)


def _validate_coupon_for_redemption(
    db: Session,
    *,
    tenant_id,
    code: str,
    venda_total: Any,
    customer_id: int | None,
    allowed_channels: tuple[str, ...] = ("pdv", "all"),
) -> Coupon:
    normalized_code = _normalize_coupon_code(code)
    coupon = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.code == normalized_code,
        )
        .first()
    )
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupom nao encontrado")

    if coupon.status != CouponStatusEnum.active:
        if coupon.status == CouponStatusEnum.used:
            raise HTTPException(status_code=400, detail="Este cupom ja foi utilizado")
        if coupon.status == CouponStatusEnum.expired:
            raise HTTPException(status_code=400, detail="Este cupom esta expirado")
        if coupon.status == CouponStatusEnum.voided:
            raise HTTPException(status_code=400, detail="Este cupom foi cancelado")
        raise HTTPException(
            status_code=400,
            detail=f"Cupom invalido (status: {coupon.status.value})",
        )

    now_ref = datetime.now(timezone.utc)
    if _coupon_is_expired(coupon, now_ref):
        coupon.status = CouponStatusEnum.expired
        db.flush()
        raise HTTPException(status_code=400, detail="Este cupom expirou")

    if coupon.channel.value not in allowed_channels:
        raise HTTPException(
            status_code=400,
            detail=(
                "Este cupom nao e valido neste canal "
                f"(canal permitido: {coupon.channel.value})"
            ),
        )

    if coupon.customer_id:
        if not customer_id:
            raise HTTPException(
                status_code=400,
                detail="Selecione o cliente correto para usar este cupom",
            )
        if int(coupon.customer_id) != int(customer_id):
            raise HTTPException(
                status_code=400,
                detail="Este cupom pertence a outro cliente",
            )

    sale_total = _as_decimal(venda_total)
    min_purchase = _as_decimal(coupon.min_purchase_value)
    if min_purchase > 0 and sale_total < min_purchase:
        raise HTTPException(
            status_code=400,
            detail=(
                "Valor minimo de compra nao atingido. "
                f"Minimo: R$ {float(min_purchase):.2f}"
            ),
        )

    return coupon


def create_coupon(
    db: Session,
    *,
    tenant_id,
    campaign: Campaign | None = None,
    customer_id: int,
    coupon_type: str = "fixed",
    discount_value=None,
    discount_percent=None,
    channel: str = "all",
    valid_days: int | None = None,
    min_purchase_value=None,
    prefix: str = "CAMP",
    meta: dict | None = None,
) -> Coupon:
    valid_until: datetime | None = None
    if valid_days:
        valid_until = datetime.now(timezone.utc) + timedelta(days=valid_days)

    for attempt in range(5):
        code = _generate_code(prefix)
        existing = (
            db.query(Coupon)
            .filter(Coupon.tenant_id == tenant_id, Coupon.code == code)
            .first()
        )
        if existing:
            continue

        coupon = Coupon(
            tenant_id=tenant_id,
            code=code,
            campaign_id=campaign.id if campaign is not None else None,
            customer_id=customer_id,
            coupon_type=CouponTypeEnum(coupon_type),
            discount_value=discount_value,
            discount_percent=discount_percent,
            channel=CouponChannelEnum(channel),
            valid_until=valid_until,
            min_purchase_value=min_purchase_value,
            meta=meta,
        )
        db.add(coupon)
        db.flush()
        logger.debug(
            "[coupon_service] Cupom criado: code=%s tenant=%s attempt=%d",
            code,
            tenant_id,
            attempt + 1,
        )
        log_campaign_event(
            db=db,
            tenant_id=tenant_id,
            event="campaign.coupon.created",
            entity_type="campaign_coupons",
            entity_id=coupon.id,
            metadata=build_coupon_audit_metadata(
                coupon,
                source="campaign" if campaign is not None else "system",
            ),
            details=f"Cupom {coupon.code} criado pelo motor de campanhas",
        )
        return coupon

    raise RuntimeError(
        "Nao foi possivel gerar codigo de cupom unico para tenant "
        f"{tenant_id} apos 5 tentativas com prefix='{prefix}'"
    )


def preview_coupon_redemption(
    db: Session,
    *,
    tenant_id,
    code: str,
    venda_total: Any,
    customer_id: int | None,
) -> dict[str, Any]:
    coupon = _validate_coupon_for_redemption(
        db,
        tenant_id=tenant_id,
        code=code,
        venda_total=venda_total,
        customer_id=customer_id,
    )
    discount_applied = _calculate_coupon_discount(coupon, venda_total)
    return {
        "code": coupon.code,
        "coupon_type": coupon.coupon_type.value,
        "discount_value": float(coupon.discount_value)
        if coupon.discount_value
        else None,
        "discount_percent": float(coupon.discount_percent)
        if coupon.discount_percent
        else None,
        "discount_applied": float(discount_applied),
        "preview_only": True,
        "message": f"Cupom validado. Desconto previsto de R$ {float(discount_applied):.2f}",
    }


def consume_coupon_redemption(
    db: Session,
    *,
    tenant_id,
    code: str,
    venda_total: Any,
    customer_id: int | None,
    venda_id: int,
    expected_discount_applied: float | None = None,
) -> dict[str, Any]:
    coupon = _validate_coupon_for_redemption(
        db,
        tenant_id=tenant_id,
        code=code,
        venda_total=venda_total,
        customer_id=customer_id,
    )
    discount_applied = _calculate_coupon_discount(coupon, venda_total)

    if expected_discount_applied is not None:
        expected_discount = _as_decimal(expected_discount_applied)
        if abs(discount_applied - expected_discount) > _MONEY_CENTS:
            raise HTTPException(
                status_code=400,
                detail=(
                    "O total da venda mudou apos aplicar o cupom. "
                    "Atualize a venda e aplique o cupom novamente."
                ),
            )

    coupon.status = CouponStatusEnum.used
    redemption = CouponRedemption(
        tenant_id=tenant_id,
        coupon_id=coupon.id,
        customer_id=customer_id,
        venda_id=venda_id,
        discount_applied=discount_applied,
    )
    db.add(redemption)
    db.flush()

    log_campaign_event(
        db=db,
        tenant_id=tenant_id,
        event="campaign.coupon.consumed",
        entity_type="campaign_coupon_redemptions",
        entity_id=redemption.id,
        metadata=build_coupon_redemption_audit_metadata(
            coupon=coupon,
            redemption=redemption,
            reason="Venda finalizada",
        ),
        details=f"Cupom {coupon.code} consumido na venda #{venda_id}",
    )

    logger.info(
        "[coupon_service] Cupom consumido no fechamento: code=%s tenant=%s venda_id=%s discount=R$%.2f",
        coupon.code,
        tenant_id,
        venda_id,
        float(discount_applied),
    )

    return {
        "coupon_id": coupon.id,
        "coupon_code": coupon.code,
        "discount_applied": float(discount_applied),
        "redemption_id": redemption.id,
    }


def reverse_coupon_redemptions_for_sale(
    db: Session,
    *,
    tenant_id,
    venda_id: int,
    reason: str,
) -> dict[str, int]:
    redemptions = (
        db.query(CouponRedemption)
        .filter(
            CouponRedemption.tenant_id == tenant_id,
            CouponRedemption.venda_id == venda_id,
            CouponRedemption.voided_at.is_(None),
        )
        .order_by(CouponRedemption.id.asc())
        .all()
    )
    if not redemptions:
        return {
            "redemptions_voided": 0,
            "loyalty_rewards_reversed": 0,
            "regular_coupons_restored": 0,
        }

    from app.campaigns.loyalty_service import revoke_loyalty_reward_by_coupon

    now_ref = datetime.now(timezone.utc)
    redemptions_voided = 0
    loyalty_rewards_reversed = 0
    regular_coupons_restored = 0

    for redemption in redemptions:
        coupon = (
            db.query(Coupon)
            .filter(
                Coupon.id == redemption.coupon_id,
                Coupon.tenant_id == tenant_id,
            )
            .first()
        )

        redemption.voided_at = now_ref
        redemption.voided_reason = reason
        redemptions_voided += 1

        if coupon is None:
            continue

        loyalty_result = revoke_loyalty_reward_by_coupon(
            db,
            tenant_id=tenant_id,
            coupon_id=coupon.id,
            reason=reason,
        )
        if loyalty_result.get("matched"):
            coupon.status = CouponStatusEnum.voided
            if loyalty_result.get("revoked"):
                loyalty_rewards_reversed += 1
            log_campaign_event(
                db=db,
                tenant_id=tenant_id,
                event="campaign.coupon.redemption_reversed",
                entity_type="campaign_coupon_redemptions",
                entity_id=redemption.id,
                metadata=build_coupon_redemption_audit_metadata(
                    coupon=coupon,
                    redemption=redemption,
                    reason=reason,
                    extra={
                        "coupon_status_after": coupon.status.value,
                        "loyalty_reversal": loyalty_result,
                    },
                ),
                details=f"Uso do cupom {getattr(coupon, 'code', coupon.id)} revertido",
            )
            continue

        coupon.status = _restored_coupon_status(coupon, now_ref)
        if coupon.status == CouponStatusEnum.active:
            regular_coupons_restored += 1
        log_campaign_event(
            db=db,
            tenant_id=tenant_id,
            event="campaign.coupon.redemption_reversed",
            entity_type="campaign_coupon_redemptions",
            entity_id=redemption.id,
            metadata=build_coupon_redemption_audit_metadata(
                coupon=coupon,
                redemption=redemption,
                reason=reason,
                extra={
                    "coupon_status_after": coupon.status.value,
                    "loyalty_reversal": loyalty_result,
                },
            ),
            details=f"Uso do cupom {getattr(coupon, 'code', coupon.id)} revertido",
        )

    db.flush()
    return {
        "redemptions_voided": redemptions_voided,
        "loyalty_rewards_reversed": loyalty_rewards_reversed,
        "regular_coupons_restored": regular_coupons_restored,
    }


def find_coupon_redemption_candidates_for_backfill(
    db: Session,
    *,
    redemption: CouponRedemption,
    window_hours: int = 12,
) -> list[int]:
    from app.vendas_models import Venda

    if not redemption.customer_id or not redemption.redeemed_at:
        return []

    reference_dt = redemption.redeemed_at
    if reference_dt.tzinfo is not None:
        start_dt = (reference_dt - timedelta(hours=window_hours)).replace(tzinfo=None)
        end_dt = (reference_dt + timedelta(hours=window_hours)).replace(tzinfo=None)
    else:
        start_dt = reference_dt - timedelta(hours=window_hours)
        end_dt = reference_dt + timedelta(hours=window_hours)

    candidates = (
        db.query(Venda)
        .filter(
            Venda.tenant_id == redemption.tenant_id,
            Venda.cliente_id == redemption.customer_id,
            Venda.data_venda >= start_dt,
            Venda.data_venda <= end_dt,
            Venda.status.in_(["finalizada", "baixa_parcial", "pago_nf", "cancelada"]),
        )
        .order_by(Venda.data_venda.asc(), Venda.id.asc())
        .all()
    )

    discount_target = _as_decimal(redemption.discount_applied)
    matched_ids: list[int] = []
    for venda in candidates:
        venda_discount = _as_decimal(getattr(venda, "desconto_valor", 0))
        if discount_target > 0 and abs(venda_discount - discount_target) > _MONEY_CENTS:
            continue
        matched_ids.append(int(venda.id))
    return matched_ids


def backfill_coupon_redemptions_venda_ids(
    db: Session,
    *,
    tenant_id=None,
    window_hours: int = 12,
) -> dict[str, Any]:
    # coupon_redemptions e TenantScoped (filtro global + fail-fast): toda query ORM
    # precisa de um tenant no contexto. Quando tenant_id e None (backfill de TODOS os
    # tenants), iteramos cada tenant setando o contexto por iteracao (a enumeracao usa a
    # tabela tenants, global/whitelist, segura sem contexto -- padrao de app/main.py).
    from uuid import UUID as _UUID
    from app.models import Tenant
    from app.tenancy.context import clear_current_tenant, set_current_tenant

    if tenant_id is None:
        filled: list[dict[str, int]] = []
        ambiguous: list[dict[str, Any]] = []
        skipped: list[int] = []
        for (tid_raw,) in db.query(Tenant.id).all():
            try:
                tid = _UUID(str(tid_raw))
            except (TypeError, ValueError):
                continue
            parcial = backfill_coupon_redemptions_venda_ids(
                db, tenant_id=tid, window_hours=window_hours
            )
            filled.extend(parcial["filled"])
            ambiguous.extend(parcial["ambiguous"])
            skipped.extend(parcial["skipped"])
        return {"filled": filled, "ambiguous": ambiguous, "skipped": skipped}

    set_current_tenant(
        tenant_id if isinstance(tenant_id, _UUID) else _UUID(str(tenant_id))
    )
    try:
        redemptions = (
            db.query(CouponRedemption)
            .filter(
                CouponRedemption.venda_id.is_(None),
                CouponRedemption.tenant_id == tenant_id,
            )
            .order_by(CouponRedemption.id.asc())
            .all()
        )
        filled: list[dict[str, int]] = []
        ambiguous: list[dict[str, Any]] = []
        skipped: list[int] = []

        for redemption in redemptions:
            candidates = find_coupon_redemption_candidates_for_backfill(
                db,
                redemption=redemption,
                window_hours=window_hours,
            )
            if len(candidates) == 1:
                redemption.venda_id = candidates[0]
                filled.append(
                    {
                        "redemption_id": int(redemption.id),
                        "venda_id": int(candidates[0]),
                    }
                )
                continue

            if len(candidates) > 1:
                ambiguous.append(
                    {
                        "redemption_id": int(redemption.id),
                        "candidate_venda_ids": candidates,
                    }
                )
                continue

            skipped.append(int(redemption.id))

        db.flush()
        return {
            "filled": filled,
            "ambiguous": ambiguous,
            "skipped": skipped,
        }
    finally:
        clear_current_tenant()
