from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from app.campaigns.models import Campaign, Coupon


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", str(value))


def _money(value: Any) -> float | None:
    if value is None:
        return None
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _start_of_day(value: date | None) -> datetime | None:
    return datetime.combine(value, time.min) if value else None


def _end_of_day(value: date | None) -> datetime | None:
    return datetime.combine(value, time.max) if value else None


def _date_in_range(
    value: datetime | None, start: datetime | None, end: datetime | None
) -> bool:
    if value is None:
        return False
    if value.tzinfo is not None:
        if start is not None and start.tzinfo is None:
            start = start.replace(tzinfo=value.tzinfo)
        if end is not None and end.tzinfo is None:
            end = end.replace(tzinfo=value.tzinfo)
    elif value.tzinfo is None:
        if start is not None and start.tzinfo is not None:
            start = start.replace(tzinfo=None)
        if end is not None and end.tzinfo is not None:
            end = end.replace(tzinfo=None)
    if start and value < start:
        return False
    if end and value > end:
        return False
    return True


def _coupon_value(coupon: Coupon) -> float | None:
    if coupon.discount_value is not None:
        return _money(coupon.discount_value)
    if coupon.discount_percent is not None:
        return float(coupon.discount_percent)
    return None


def _coupon_value_label(coupon: Coupon) -> str | None:
    if coupon.discount_value is not None:
        return "valor"
    if coupon.discount_percent is not None:
        return "percentual"
    return None


def _consumed_stamps_from_meta(meta: dict[str, Any] | None) -> int:
    data = dict(meta or {})
    consumed = data.get("consumed_stamps")
    if consumed is None:
        consumed = data.get("stamps_to_complete_snapshot")
    try:
        return max(int(consumed or 0), 0)
    except (TypeError, ValueError):
        return 0


def _append_event(events: list[dict[str, Any]], event: dict[str, Any]) -> None:
    event.setdefault("valor", None)
    event.setdefault("quantidade", None)
    event.setdefault("saldo_carimbos", None)
    event.setdefault("saldo_cashback", None)
    event.setdefault("campanha_id", None)
    event.setdefault("campanha_nome", None)
    event.setdefault("campanha_tipo", None)
    event.setdefault("venda_id", None)
    event.setdefault("numero_venda", None)
    event.setdefault("cupom_id", None)
    event.setdefault("cupom_codigo", None)
    event.setdefault("status", None)
    event.setdefault("metadata", {})
    events.append(event)


def _sort_weight(categoria: str | None, tipo: str | None) -> int:
    if categoria == "carimbo" and tipo == "credito":
        return 10
    if categoria == "carimbo" and tipo == "conversao":
        return 20
    if categoria == "cupom" and tipo == "gerado":
        return 30
    if categoria == "cashback":
        return 40
    if categoria == "cupom":
        return 50
    if categoria == "carimbo":
        return 60
    return 90


def _campaign_fields(campaign: Campaign | None) -> dict[str, Any]:
    return {
        "campanha_id": int(campaign.id) if campaign else None,
        "campanha_nome": campaign.name if campaign else None,
        "campanha_tipo": _enum_value(campaign.campaign_type) if campaign else None,
    }


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
