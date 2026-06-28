from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.campaigns.models import Campaign, Coupon, CouponRedemption, CouponStatusEnum
from app.campaigns.statement_service_parts.common import (
    _append_event,
    _campaign_fields,
    _consumed_stamps_from_meta,
    _coupon_value,
    _coupon_value_label,
    _date_in_range,
    _enum_value,
    _iso,
    _money,
    _parse_datetime,
)


def _load_coupon_redemptions_by_coupon(
    db: Session,
    *,
    tenant_id,
    customer_id: int,
) -> dict[int, list[CouponRedemption]]:
    redemptions = (
        db.query(CouponRedemption)
        .filter(
            CouponRedemption.tenant_id == tenant_id,
            CouponRedemption.customer_id == customer_id,
        )
        .all()
    )
    grouped: dict[int, list[CouponRedemption]] = {}
    for redemption in redemptions:
        grouped.setdefault(int(redemption.coupon_id), []).append(redemption)
    return grouped


def _add_coupon_events(
    db: Session,
    events: list[dict[str, Any]],
    *,
    tenant_id,
    customer_id: int,
    campaign_map: dict[int, Campaign],
    redemptions_by_coupon: dict[int, list[CouponRedemption]],
    start_dt: datetime | None,
    end_dt: datetime | None,
    include_coupon_events: bool,
    include_stamp_conversion_events: bool,
) -> None:
    coupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.customer_id == customer_id,
        )
        .all()
    )
    for coupon in coupons:
        campaign = (
            campaign_map.get(int(coupon.campaign_id)) if coupon.campaign_id else None
        )
        meta = dict(coupon.meta or {})
        consumed_stamps = _consumed_stamps_from_meta(meta)
        coupon_redemptions = redemptions_by_coupon.get(int(coupon.id), [])

        if (
            include_stamp_conversion_events
            and consumed_stamps > 0
            and _date_in_range(coupon.created_at, start_dt, end_dt)
        ):
            _append_event(
                events,
                {
                    "id": f"coupon:{coupon.id}:stamps-consumed",
                    "data": _iso(coupon.created_at),
                    "categoria": "carimbo",
                    "tipo": "conversao",
                    "direcao": "debito",
                    "titulo": "Carimbos convertidos em cupom",
                    "descricao": f"{consumed_stamps} carimbo(s) usados para gerar o cupom {coupon.code}.",
                    "quantidade": -consumed_stamps,
                    "cupom_id": int(coupon.id),
                    "cupom_codigo": coupon.code,
                    "status": _enum_value(coupon.status),
                    "origem": "fidelidade",
                    "metadata": {"coupon_meta": meta},
                    **_campaign_fields(campaign),
                },
            )

        if include_coupon_events and _date_in_range(
            coupon.created_at, start_dt, end_dt
        ):
            _append_event(
                events,
                {
                    "id": f"coupon:{coupon.id}:created",
                    "data": _iso(coupon.created_at),
                    "categoria": "cupom",
                    "tipo": "gerado",
                    "direcao": "credito",
                    "titulo": "Cupom gerado",
                    "descricao": f"Cupom {coupon.code} gerado.",
                    "valor": _coupon_value(coupon),
                    "cupom_id": int(coupon.id),
                    "cupom_codigo": coupon.code,
                    "status": _enum_value(coupon.status),
                    "origem": "campanha" if coupon.campaign_id else "manual",
                    "metadata": {
                        "coupon_type": _enum_value(coupon.coupon_type),
                        "valor_tipo": _coupon_value_label(coupon),
                        "valid_until": _iso(coupon.valid_until),
                        "min_purchase_value": _money(coupon.min_purchase_value),
                        "coupon_meta": meta,
                    },
                    **_campaign_fields(campaign),
                },
            )

        for redemption in coupon_redemptions:
            if include_coupon_events and _date_in_range(
                redemption.redeemed_at, start_dt, end_dt
            ):
                _append_event(
                    events,
                    {
                        "id": f"coupon-redemption:{redemption.id}:redeemed",
                        "data": _iso(redemption.redeemed_at),
                        "categoria": "cupom",
                        "tipo": "uso",
                        "direcao": "debito",
                        "titulo": "Cupom usado",
                        "descricao": f"Cupom {coupon.code} usado em venda.",
                        "valor": -abs(_money(redemption.discount_applied) or 0),
                        "venda_id": int(redemption.venda_id)
                        if redemption.venda_id
                        else None,
                        "cupom_id": int(coupon.id),
                        "cupom_codigo": coupon.code,
                        "status": "estornado" if redemption.voided_at else "usado",
                        "origem": "venda",
                        "metadata": {"redemption_id": int(redemption.id)},
                        **_campaign_fields(campaign),
                    },
                )

            if (
                redemption.voided_at
                and include_coupon_events
                and _date_in_range(redemption.voided_at, start_dt, end_dt)
            ):
                _append_event(
                    events,
                    {
                        "id": f"coupon-redemption:{redemption.id}:voided",
                        "data": _iso(redemption.voided_at),
                        "categoria": "cupom",
                        "tipo": "estorno",
                        "direcao": "credito",
                        "titulo": "Uso de cupom estornado",
                        "descricao": redemption.voided_reason
                        or f"Uso do cupom {coupon.code} estornado.",
                        "valor": abs(_money(redemption.discount_applied) or 0),
                        "venda_id": int(redemption.venda_id)
                        if redemption.venda_id
                        else None,
                        "cupom_id": int(coupon.id),
                        "cupom_codigo": coupon.code,
                        "status": "estornado",
                        "origem": "cancelamento",
                        "metadata": {"redemption_id": int(redemption.id)},
                        **_campaign_fields(campaign),
                    },
                )

        voided_at_raw = meta.get("voided_at") or meta.get("revoked_at")
        voided_at = _parse_datetime(voided_at_raw)
        if (
            coupon.status == CouponStatusEnum.voided
            and voided_at
            and _date_in_range(voided_at, start_dt, end_dt)
            and not coupon_redemptions
        ):
            if include_coupon_events:
                _append_event(
                    events,
                    {
                        "id": f"coupon:{coupon.id}:voided",
                        "data": _iso(voided_at),
                        "categoria": "cupom",
                        "tipo": "anulacao",
                        "direcao": "debito",
                        "titulo": "Cupom anulado",
                        "descricao": meta.get("voided_reason")
                        or f"Cupom {coupon.code} anulado.",
                        "valor": -abs(_coupon_value(coupon) or 0),
                        "cupom_id": int(coupon.id),
                        "cupom_codigo": coupon.code,
                        "status": "voided",
                        "origem": "manual",
                        "metadata": {"coupon_meta": meta},
                        **_campaign_fields(campaign),
                    },
                )
            if include_stamp_conversion_events and consumed_stamps > 0:
                _append_event(
                    events,
                    {
                        "id": f"coupon:{coupon.id}:stamps-restored",
                        "data": _iso(voided_at),
                        "categoria": "carimbo",
                        "tipo": "restauracao",
                        "direcao": "credito",
                        "titulo": "Carimbos restaurados por cupom anulado",
                        "descricao": f"{consumed_stamps} carimbo(s) restaurados do cupom {coupon.code}.",
                        "quantidade": consumed_stamps,
                        "cupom_id": int(coupon.id),
                        "cupom_codigo": coupon.code,
                        "status": "restaurado",
                        "origem": "anulacao_cupom",
                        "metadata": {"coupon_meta": meta},
                        **_campaign_fields(campaign),
                    },
                )
