from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from app.models import Cliente, User, UserPushDevice
from app.services.sales_channel import normalize_sales_channel
from app.services.sales_channel_labels import channel_label_for


logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

EVENT_CONTENT = {
    "checkout_created": (
        "Pedido recebido",
        "Recebemos seu pedido. Acompanhe o status em Meus Pedidos.",
    ),
    "payment_approved": (
        "Pagamento aprovado",
        "Pagamento confirmado. A loja ja vai preparar seu pedido.",
    ),
    "payment_in_analysis": (
        "Pagamento em analise",
        "O pagamento ainda esta em analise. Avisaremos quando atualizar.",
    ),
    "payment_failed": (
        "Pagamento nao concluido",
        "Nao foi possivel confirmar o pagamento desse pedido.",
    ),
    "ready_for_pickup": (
        "Pedido pronto para retirada",
        "Seu pedido ja esta pronto para retirada na loja.",
    ),
    "preparing": (
        "Pedido em separacao",
        "A loja esta separando os itens do seu pedido.",
    ),
    "out_for_delivery": (
        "Pedido saiu para entrega",
        "Seu pedido ja esta em rota de entrega.",
    ),
    "delivered": (
        "Pedido entregue",
        "Seu pedido foi entregue. Obrigado pela compra!",
    ),
}


def build_order_push_content(
    *,
    event: str,
    pedido_id: str | None = None,
    venda_id: int | None = None,
    canal: str | None = None,
) -> dict[str, Any]:
    title, body = EVENT_CONTENT.get(
        event,
        (
            "Atualizacao do pedido",
            "Seu pedido recebeu uma atualizacao. Veja os detalhes em Meus Pedidos.",
        ),
    )
    normalized_channel = normalize_sales_channel(canal, default="ecommerce")
    return {
        "title": title,
        "body": body,
        "data": {
            "source": "order",
            "kind": "order_status",
            "event": event,
            "pedido_id": pedido_id,
            "venda_id": venda_id,
            "canal": normalized_channel,
            "canal_label": channel_label_for(normalized_channel),
        },
    }


def _load_user(db, *, tenant_id: str, user_id: int | None) -> User | None:
    if not user_id:
        return None
    return (
        db.query(User)
        .filter(
            User.id == user_id,
            User.tenant_id == tenant_id,
        )
        .first()
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_active_devices(db, *, tenant_id: str, user_id: int | None) -> list:
    if not user_id:
        return []
    try:
        return (
            db.query(UserPushDevice)
            .filter(
                UserPushDevice.user_id == user_id,
                UserPushDevice.tenant_id == tenant_id,
                UserPushDevice.enabled.is_(True),
            )
            .order_by(UserPushDevice.last_seen_at.desc())
            .all()
        )
    except Exception as exc:
        logger.warning("[OrderPush] Falha ao consultar dispositivos push: %s", exc)
        return []


def _send_expo_push(
    push_token: str, content: dict[str, Any]
) -> tuple[bool, str | None, str | None]:
    payload = {
        "to": push_token,
        "sound": "default",
        "priority": "high",
        "channelId": "default",
        "title": content["title"],
        "body": content["body"],
        "data": content["data"],
    }
    response = requests.post(
        EXPO_PUSH_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    try:
        response_body = response.json()
    except Exception:
        return True, None, None
    data = response_body.get("data") if isinstance(response_body, dict) else None
    if isinstance(data, dict) and data.get("status") not in (None, "ok"):
        logger.warning("[OrderPush] Expo retornou falha: %s", data)
        return False, None, str(data)
    ticket_id = data.get("id") if isinstance(data, dict) else None
    return True, ticket_id, None


def _mark_device_push_result(
    device, *, sent: bool, ticket_id: str | None, error: str | None
) -> None:
    now = _utcnow()
    if sent:
        device.last_success_at = now
        device.last_ticket_id = ticket_id
        device.last_error = None
        device.last_error_at = None
        return
    device.last_error = error or "Falha ao enviar push"
    device.last_error_at = now
    if "DeviceNotRegistered" in device.last_error:
        device.enabled = False


def _legacy_token_device(push_token: str) -> Any:
    return type(
        "LegacyPushDevice",
        (),
        {
            "id": None,
            "expo_push_token": push_token,
            "last_success_at": None,
            "last_ticket_id": None,
            "last_error": None,
            "last_error_at": None,
            "enabled": True,
        },
    )()


def notify_order_event(
    db,
    *,
    tenant_id: str,
    user_id: int | None,
    event: str,
    pedido_id: str | None = None,
    venda_id: int | None = None,
    canal: str | None = None,
) -> bool:
    try:
        user = _load_user(db, tenant_id=tenant_id, user_id=user_id)
        devices = _load_active_devices(db, tenant_id=tenant_id, user_id=user_id)
        legacy_token = str(getattr(user, "push_token", "") or "").strip()
        if not devices and legacy_token:
            devices = [_legacy_token_device(legacy_token)]
        if not devices:
            logger.warning(
                "[OrderPush] usuario sem dispositivo push tenant_id=%s user_id=%s event=%s pedido_id=%s venda_id=%s canal=%s",
                tenant_id,
                user_id,
                event,
                pedido_id,
                venda_id,
                canal,
            )
            return False

        content = build_order_push_content(
            event=event,
            pedido_id=pedido_id,
            venda_id=venda_id,
            canal=canal,
        )
        any_sent = False
        for device in devices:
            token = str(getattr(device, "expo_push_token", "") or "").strip()
            if not token:
                continue
            try:
                sent, ticket_id, error = _send_expo_push(token, content)
            except Exception as exc:
                sent, ticket_id, error = False, None, str(exc)
            any_sent = any_sent or sent
            if getattr(device, "id", None):
                _mark_device_push_result(
                    device, sent=sent, ticket_id=ticket_id, error=error
                )
        if hasattr(db, "commit"):
            try:
                db.commit()
            except Exception:
                if hasattr(db, "rollback"):
                    db.rollback()
        return any_sent
    except Exception as exc:
        logger.warning("[OrderPush] Falha ao enviar push de pedido: %s", exc)
        return False


def notify_sale_order_event(
    db,
    *,
    venda,
    event: str,
    pedido_id: str | None = None,
) -> bool:
    cliente_id = getattr(venda, "cliente_id", None)
    tenant_id = str(getattr(venda, "tenant_id", "") or "")
    if not cliente_id or not tenant_id:
        return False

    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id,
        )
        .first()
    )
    return notify_order_event(
        db,
        tenant_id=tenant_id,
        user_id=getattr(cliente, "user_id", None),
        event=event,
        pedido_id=pedido_id,
        venda_id=getattr(venda, "id", None),
        canal=getattr(venda, "canal", None),
    )
