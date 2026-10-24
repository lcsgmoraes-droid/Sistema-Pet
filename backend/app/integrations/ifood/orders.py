"""Persistencia idempotente e ciclo de vida dos pedidos iFood."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ifood_integration_models import IfoodMerchantConfig
from app.ifood_order_models import IfoodEvent, IfoodOrder
from app.config import settings

from .client import IfoodClient, IfoodClientError

_STATUS_BY_CODE = {
    "PLC": "PLACED",
    "CFM": "CONFIRMED",
    "SPS": "SEPARATION_STARTED",
    "SPE": "SEPARATION_ENDED",
    "RTP": "READY_TO_PICKUP",
    "DSP": "DISPATCHED",
    "CON": "CONCLUDED",
    "CAN": "CANCELLED",
    "CAR": "CANCELLATION_REQUESTED",
    "CARF": "CANCELLATION_REQUEST_FAILED",
    "OPA": "ORDER_PATCHED",
}
_PROGRESS = {
    value: index
    for index, value in enumerate(
        (
            "PLACED",
            "CONFIRMED",
            "PREPARATION_STARTED",
            "SEPARATION_STARTED",
            "SEPARATION_ENDED",
            "READY_TO_PICKUP",
            "DISPATCHED",
            "CONCLUDED",
            "CANCELLED",
        )
    )
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> datetime | None:
    normalized = _text(value)
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None


def _event_status(event: dict[str, Any]) -> str | None:
    full_code = _text(event.get("fullCode"))
    code = _text(event.get("code"))
    if full_code:
        return full_code.removeprefix("ORDER_")
    return _STATUS_BY_CODE.get(code or "", code)


def _delivery_details(payload: dict[str, Any]) -> dict[str, Any]:
    delivery = _mapping(payload.get("delivery"))
    operation_delivery = _mapping(
        _mapping(payload.get("operationMode")).get("delivery")
    )
    return (
        _mapping(delivery.get("deliveryAddress"))
        or _mapping(operation_delivery.get("destination"))
        or delivery
        or operation_delivery
    )


def _order_total(payload: dict[str, Any]) -> float | None:
    total = _mapping(payload.get("total"))
    for value in (
        total.get("orderAmount"),
        total.get("subTotal"),
        payload.get("orderAmount"),
        payload.get("totalPrice"),
    ):
        parsed = _number(value)
        if parsed is not None:
            return parsed
    bag_prices = _mapping(_mapping(payload.get("bag")).get("prices"))
    bag_total = _number(_mapping(bag_prices.get("grossValue")).get("value"))
    if bag_total is not None:
        return bag_total / 100
    return None


def upsert_ifood_order(
    db: Session,
    *,
    tenant_id: UUID,
    merchant_id: str,
    order_id: str,
    payload: dict[str, Any],
    event_status: str | None = None,
    event_at: datetime | None = None,
) -> IfoodOrder:
    order = (
        db.query(IfoodOrder)
        .filter(
            IfoodOrder.tenant_id == tenant_id,
            IfoodOrder.ifood_order_id == order_id,
        )
        .with_for_update()
        .populate_existing()
        .first()
    )
    if order is None:
        order = IfoodOrder(
            tenant_id=tenant_id,
            merchant_id=merchant_id,
            ifood_order_id=order_id,
            payload={},
        )
        db.add(order)

    old_time = _date(str(order.last_event_at)) if order.last_event_at else None
    new_time = _date(str(event_at)) if event_at else None
    if old_time and old_time.tzinfo is None:
        old_time = old_time.replace(tzinfo=timezone.utc)
    if new_time and new_time.tzinfo is None:
        new_time = new_time.replace(tzinfo=timezone.utc)
    stale = bool(old_time and new_time and new_time < old_time)
    if stale:
        return order

    delivery = _mapping(payload.get("delivery"))
    operation_mode = _mapping(payload.get("operationMode"))
    operation_delivery = _mapping(operation_mode.get("delivery"))
    schedule = _mapping(payload.get("schedule")) or _mapping(payload.get("scheduling"))
    order.merchant_id = merchant_id
    order.display_id = (
        _text(payload.get("displayId"))
        or _text(payload.get("shortCode"))
        or order.display_id
    )
    incoming_status = (
        event_status or _text(payload.get("status")) or order.status or "PLACED"
    )
    incoming_status = incoming_status.removeprefix("ORDER_")
    terminal = order.status in {"CONCLUDED", "CANCELLED"}
    regresses = _PROGRESS.get(incoming_status, -1) < _PROGRESS.get(
        order.status or "", -1
    )
    if (
        not stale
        and (
            not regresses
            or incoming_status
            in {"CANCELLATION_REQUESTED", "CANCELLATION_REQUEST_FAILED"}
        )
        and not (terminal and incoming_status != "CANCELLED")
    ):
        order.status = incoming_status
    order.order_type = (
        _text(payload.get("orderType"))
        or _text(operation_mode.get("type"))
        or order.order_type
    )
    order.order_timing = (
        _text(payload.get("orderTiming"))
        or _text(operation_mode.get("schedulingType"))
        or order.order_timing
    )
    order.delivered_by = (
        _text(delivery.get("deliveredBy"))
        or _text(operation_delivery.get("provider"))
        or _text(payload.get("deliveredBy"))
        or order.delivered_by
    )
    order.total = _order_total(payload) if payload else order.total
    order.placed_at = (
        _date(payload.get("createdAt"))
        or _date(payload.get("placedAt"))
        or order.placed_at
    )
    order.preparation_start_at = (
        _date(schedule.get("preparationStartDateTime"))
        or _date(payload.get("preparationStartDateTime"))
        or order.preparation_start_at
    )
    if event_at and not stale:
        order.last_event_at = event_at
    if payload and not stale:
        order.payload = payload
        if settings.IFOOD_PDV_PILOT_ENABLED:
            from .pdv_pilot import pilot_order_display_total

            try:
                pilot_total = pilot_order_display_total(order)
            except HTTPException:
                # Fora do contrato estrito do piloto, mantem a leitura legada.
                pass
            else:
                # Virtual Bag separa itens e frete. A validacao tambem exige
                # pagamento exato e taxas zeradas antes de exibir a soma.
                order.total = float(pilot_total)
    return order


def _event_record(db: Session, *, tenant_id: UUID, event_id: str) -> IfoodEvent | None:
    return (
        db.query(IfoodEvent)
        .filter(
            IfoodEvent.tenant_id == tenant_id,
            IfoodEvent.ifood_event_id == event_id,
        )
        .first()
    )


def process_order_events(
    db: Session,
    *,
    tenant_id: UUID,
    config: IfoodMerchantConfig,
    client: IfoodClient,
) -> dict[str, Any]:
    """Persiste antes do ACK e reprocessa eventos sem sucesso anterior."""

    merchant_id = _text(config.merchant_id)
    if not merchant_id:
        raise IfoodClientError("Informe o Merchant ID antes de consultar pedidos.")
    if settings.IFOOD_PDV_PILOT_ENABLED:
        from .pdv_pilot import pilot_settings_reason

        reason = pilot_settings_reason(
            tenant_id=tenant_id, merchant_id=merchant_id, require_order=False
        )
        if reason:
            raise IfoodClientError(reason)

    events = sorted(
        client.poll_events([merchant_id]),
        key=lambda item: _text(item.get("createdAt")) or "",
    )
    acknowledged_ids: list[str] = []
    failed = 0
    created_orders = 0
    updated_orders = 0

    for event_payload in events:
        if _text(event_payload.get("merchantId")) != merchant_id:
            failed += 1
            continue
        event_id = _text(event_payload.get("id"))
        if not event_id:
            failed += 1
            continue
        event = _event_record(db, tenant_id=tenant_id, event_id=event_id)
        if event and event.processed_at is not None:
            acknowledged_ids.append(event_id)
            continue

        order_id = _text(event_payload.get("orderId"))
        provider_created_at = _date(event_payload.get("createdAt"))
        if event is None:
            event = IfoodEvent(
                tenant_id=tenant_id,
                merchant_id=_text(event_payload.get("merchantId")) or merchant_id,
                ifood_event_id=event_id,
                ifood_order_id=order_id,
                code=_text(event_payload.get("code")),
                full_code=_text(event_payload.get("fullCode")),
                provider_created_at=provider_created_at,
                payload=event_payload,
            )
            db.add(event)
            db.commit()

        try:
            if order_id:
                existing = (
                    db.query(IfoodOrder)
                    .filter(
                        IfoodOrder.tenant_id == tenant_id,
                        IfoodOrder.ifood_order_id == order_id,
                    )
                    .first()
                )
                details: dict[str, Any] = {}
                if existing is None or _event_status(event_payload) == "PLACED":
                    details = client.get_order(order_id)
                    details_merchant = _text(
                        _mapping(details.get("merchant")).get("id")
                    )
                    if details_merchant and details_merchant != merchant_id:
                        raise IfoodClientError(
                            "A loja do pedido recebido diverge da loja consultada."
                        )
                    if settings.IFOOD_PDV_PILOT_ENABLED and (
                        details.get("test") is not True
                        or details_merchant != merchant_id
                    ):
                        raise IfoodClientError(
                            "Este piloto DEV recebe somente pedidos oficiais da loja de teste autorizada."
                        )
                order = upsert_ifood_order(
                    db,
                    tenant_id=tenant_id,
                    merchant_id=event.merchant_id,
                    order_id=order_id,
                    payload=details,
                    event_status=_event_status(event_payload),
                    event_at=provider_created_at,
                )
                if existing is None:
                    created_orders += 1
                else:
                    updated_orders += 1
                db.add(order)

            event.processed_at = _utcnow()
            event.processing_error = None
            db.commit()
            acknowledged_ids.append(event_id)
        except IfoodClientError as exc:
            db.rollback()
            stored_event = _event_record(db, tenant_id=tenant_id, event_id=event_id)
            if stored_event:
                stored_event.processing_error = str(exc)
                db.commit()
            failed += 1

    if acknowledged_ids:
        client.acknowledge_events(acknowledged_ids)
        acknowledged_at = _utcnow()
        (
            db.query(IfoodEvent)
            .filter(
                IfoodEvent.tenant_id == tenant_id,
                IfoodEvent.ifood_event_id.in_(acknowledged_ids),
            )
            .update(
                {IfoodEvent.acknowledged_at: acknowledged_at},
                synchronize_session=False,
            )
        )

    config.last_orders_poll_at = _utcnow()
    config.last_orders_error = None
    db.commit()
    return {
        "received": len(events),
        "acknowledged": len(acknowledged_ids),
        "failed": failed,
        "created_orders": created_orders,
        "updated_orders": updated_orders,
    }


def mark_order_action(order: IfoodOrder, action: str) -> None:
    if (
        settings.IFOOD_PDV_PILOT_ENABLED
        and order.last_action == "pdv_bag_review_required"
    ):
        # Confirmar/despachar nao e uma nova leitura da sacola nem pode apagar
        # a pendencia de conferencia do piloto.
        return
    order.last_action = action
    order.last_action_at = _utcnow()


def order_summary(order: IfoodOrder, db: Session | None = None) -> dict[str, Any]:
    payload = _mapping(order.payload)
    customer = _mapping(payload.get("customer"))
    address = _delivery_details(payload)
    summary = {
        "id": order.id,
        "ifood_order_id": order.ifood_order_id,
        "display_id": order.display_id,
        "merchant_id": order.merchant_id,
        "status": order.status,
        "order_type": order.order_type,
        "order_timing": order.order_timing,
        "delivered_by": order.delivered_by,
        "total": order.total,
        "placed_at": order.placed_at,
        "preparation_start_at": order.preparation_start_at,
        "last_event_at": order.last_event_at,
        "last_action": order.last_action,
        "last_action_at": order.last_action_at,
        "customer_name": _text(customer.get("name")),
        "delivery_address": address,
    }
    if db is not None:
        from .pdv_pilot import pdv_bridge_summary

        summary["pdv_bridge"] = pdv_bridge_summary(db, order)
    return summary


def order_detail(order: IfoodOrder, db: Session | None = None) -> dict[str, Any]:
    return {**order_summary(order, db=db), "payload": _mapping(order.payload)}
