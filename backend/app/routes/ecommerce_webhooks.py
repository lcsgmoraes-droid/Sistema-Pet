"""Endpoints de webhooks de ecommerce/app."""

import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.db.session import SessionLocal
from app.idempotency_models import IdempotencyKey
from app.pedido_models import Pedido
from app.routes import ecommerce_webhooks_payment as payment
from app.routes import ecommerce_webhooks_sales as sales
from app.routes import ecommerce_webhooks_security as security
from app.services.ecommerce_payment_config import (
    resolve_mercado_pago_tenant_id_from_webhook_token,
    runtime_config_from_webhook_token,
)
from app.services.mercado_pago_checkout import (
    extract_notification_payment_id,
    fetch_payment,
    normalize_payment_payload,
    validate_webhook_signature,
    validate_webhook_signature_from_env,
)
from app.services.order_push_notifications import notify_order_event
from app.tenancy.context import set_current_tenant

router = APIRouter(prefix="/webhooks", tags=["ecommerce-webhooks"])

_normalizar_canal_venda_online = sales._normalizar_canal_venda_online
_resolver_status_entrega_online = sales._resolver_status_entrega_online
_mapear_forma_pagamento_ecommerce = sales._mapear_forma_pagamento_ecommerce
_processar_pos_venda_ecommerce = sales._processar_pos_venda_ecommerce
_integrar_venda_ao_motor = sales._integrar_venda_ao_motor

_map_payment_status = payment._map_payment_status
_find_pedido_id = payment._find_pedido_id
_first_non_empty = payment._first_non_empty
_as_dict = payment._as_dict
_payment_payload_contexts = payment._payment_payload_contexts
_find_payload_value = payment._find_payload_value
_find_payment_preference_id = payment._find_payment_preference_id
_find_pedido_for_payment = payment._find_pedido_for_payment
_apply_payment_status_update = payment._apply_payment_status_update
_normalizar_payment_method_online = payment._normalizar_payment_method_online
_extrair_pagamento_do_webhook = payment._extrair_pagamento_do_webhook
_extrair_financeiro_gateway_online = payment._extrair_financeiro_gateway_online

_env_flag_enabled = security._env_flag_enabled
_payment_gateway_requires_signature = security._payment_gateway_requires_signature
_get_signature_config = security._get_signature_config
_find_tenant_id = security._find_tenant_id
_extract_event_info = security._extract_event_info
_validate_optional_signature = security._validate_optional_signature


def _order_push_event_for_payment_status(pedido_status: str | None) -> str | None:
    if pedido_status == "aprovado":
        return "payment_approved"
    if pedido_status == "pendente":
        return "payment_in_analysis"
    if pedido_status in {"recusado", "cancelado"}:
        return "payment_failed"
    return None


def _notify_payment_status_change(
    db,
    *,
    tenant_id: str,
    pedido: Pedido | None,
    pedido_status: str | None,
    venda_id: int | None,
) -> None:
    event = _order_push_event_for_payment_status(pedido_status)
    if not pedido or not event:
        return
    notify_order_event(
        db,
        tenant_id=str(tenant_id),
        user_id=pedido.cliente_id,
        event=event,
        pedido_id=pedido.pedido_id,
        venda_id=venda_id,
        canal=pedido.origem,
    )


@router.post("/pagarme")
async def webhook_pagarme(request: Request):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Payload JSON invalido"
        )

    signature_status = _validate_optional_signature(raw_body, request)
    tenant_id = _find_tenant_id(payload, request)
    set_current_tenant(UUID(tenant_id))
    event_id, event_type, request_hash = _extract_event_info(payload, raw_body)

    db = SessionLocal()
    try:
        endpoint_name = "POST /api/webhooks/pagarme"
        key_name = f"pagarme:{event_id}"

        existing = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.user_id == 0,
                IdempotencyKey.tenant_id == tenant_id,
                IdempotencyKey.endpoint == endpoint_name,
                IdempotencyKey.chave_idempotencia == key_name,
            )
            .first()
        )

        if existing:
            if existing.request_hash != request_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Conflito de idempotencia no webhook",
                )
            return {
                "status": "duplicate",
                "event_id": event_id,
                "event_type": event_type,
                "signature": signature_status,
            }

        registry = IdempotencyKey(
            user_id=0,
            tenant_id=tenant_id,
            endpoint=endpoint_name,
            chave_idempotencia=key_name,
            request_hash=request_hash,
            status="processing",
        )
        db.add(registry)
        db.flush()

        updated, venda_id, pedido_notificacao, pedido_status_notificacao = (
            _apply_payment_status_update(db, tenant_id=tenant_id, payload=payload)
        )
        response = {
            "status": "processed",
            "event_id": event_id,
            "event_type": event_type,
            "signature": signature_status,
            "pedido_atualizado": updated,
            "venda_id": venda_id,
            "ready_for_provider_config": True,
        }

        registry.status = "completed"
        registry.response_status_code = 200
        registry.response_body = json.dumps(response)
        registry.completed_at = datetime.utcnow()
        db.commit()
        _notify_payment_status_change(
            db,
            tenant_id=tenant_id,
            pedido=pedido_notificacao,
            pedido_status=pedido_status_notificacao,
            venda_id=venda_id,
        )
        return response

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar webhook Pagar.me: {exc}"
        )
    finally:
        db.close()


def _process_mercadopago_payment_update(
    db,
    *,
    tenant_id: str,
    endpoint_name: str,
    key_name: str,
    event_id: str,
    event_type: str,
    payment_id: str | None,
    payment_status: str,
    signature_status: str,
    request_hash: str,
    payload: dict,
) -> dict:
    existing = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.user_id == 0,
            IdempotencyKey.tenant_id == tenant_id,
            IdempotencyKey.endpoint == endpoint_name,
            IdempotencyKey.chave_idempotencia == key_name,
        )
        .first()
    )

    duplicate_response = {
        "event_id": event_id,
        "event_type": event_type,
        "payment_id": payment_id,
        "signature": signature_status,
    }
    if existing:
        if existing.request_hash != request_hash:
            return {"status": "duplicate_status", **duplicate_response}
        return {"status": "duplicate", **duplicate_response}

    registry = IdempotencyKey(
        user_id=0,
        tenant_id=tenant_id,
        endpoint=endpoint_name,
        chave_idempotencia=key_name,
        request_hash=request_hash,
        status="processing",
    )
    db.add(registry)
    db.flush()

    updated, venda_id, pedido_notificacao, pedido_status_notificacao = (
        _apply_payment_status_update(db, tenant_id=tenant_id, payload=payload)
    )
    response = {
        "status": "processed",
        "provider": "mercadopago",
        "event_id": event_id,
        "event_type": event_type,
        "payment_id": payment_id,
        "payment_status": payment_status,
        "signature": signature_status,
        "pedido_atualizado": updated,
        "venda_id": venda_id,
    }

    registry.status = "completed"
    registry.response_status_code = 200
    registry.response_body = json.dumps(response)
    registry.completed_at = datetime.utcnow()
    db.commit()
    _notify_payment_status_change(
        db,
        tenant_id=str(tenant_id),
        pedido=pedido_notificacao,
        pedido_status=pedido_status_notificacao,
        venda_id=venda_id,
    )
    return response


def _is_mercadopago_simulation(notification_payload: dict) -> bool:
    live_mode = notification_payload.get("live_mode")
    return live_mode is False or str(live_mode).strip().lower() == "false"


def _ignored_mercadopago_simulation_response(
    payment_id: str | None, signature_status: str
) -> dict:
    return {
        "status": "ignored_simulation",
        "provider": "mercadopago",
        "payment_id": payment_id,
        "signature": signature_status,
        "detail": "Simulacao Mercado Pago sem pagamento real consultavel",
    }


def _finish_mercadopago_webhook(
    db,
    *,
    tenant_id: str,
    endpoint_name: str,
    payment_id: str | None,
    signature_status: str,
    notification_payload: dict,
    raw_body: bytes,
    payload: dict,
) -> dict:
    event_id, event_type, request_hash = _extract_event_info(
        notification_payload, raw_body
    )
    payment_status = str(payload.get("status") or "unknown").strip().lower()
    key_name = f"mercadopago:{payment_id}:{event_type}:{payment_status}"
    return _process_mercadopago_payment_update(
        db,
        tenant_id=tenant_id,
        endpoint_name=endpoint_name,
        key_name=key_name,
        event_id=event_id,
        event_type=event_type,
        payment_id=payment_id,
        payment_status=payment_status,
        signature_status=signature_status,
        request_hash=request_hash,
        payload=payload,
    )


def _load_notification_payload(raw_body: bytes) -> dict:
    try:
        return json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Payload JSON invalido"
        )


@router.post("/mercadopago/{webhook_token}")
async def webhook_mercadopago_tenant(webhook_token: str, request: Request):
    raw_body = await request.body()
    notification_payload = _load_notification_payload(raw_body)
    payment_id = extract_notification_payment_id(notification_payload, request)

    db = SessionLocal()
    try:
        webhook_tenant_id = resolve_mercado_pago_tenant_id_from_webhook_token(
            db, webhook_token
        )
        if not webhook_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuracao Mercado Pago nao encontrada para este webhook",
            )

        set_current_tenant(UUID(str(webhook_tenant_id)))
        payment_config = runtime_config_from_webhook_token(db, webhook_token)
        if not payment_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuracao Mercado Pago nao encontrada para este webhook",
            )

        signature_status = validate_webhook_signature(
            request,
            payment_config.webhook_secret,
            data_id=payment_id,
        )

        try:
            payment_payload = fetch_payment(
                str(payment_id or ""),
                access_token=payment_config.access_token,
            )
        except HTTPException as exc:
            if _is_mercadopago_simulation(notification_payload):
                return _ignored_mercadopago_simulation_response(
                    payment_id, signature_status
                )
            raise exc

        payload = normalize_payment_payload(payment_payload, notification_payload)
        tenant_id = payment_config.tenant_id
        set_current_tenant(UUID(tenant_id))
        return _finish_mercadopago_webhook(
            db,
            tenant_id=tenant_id,
            endpoint_name="POST /api/webhooks/mercadopago/{webhook_token}",
            payment_id=payment_id,
            signature_status=signature_status,
            notification_payload=notification_payload,
            raw_body=raw_body,
            payload=payload,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar webhook Mercado Pago: {exc}"
        )
    finally:
        db.close()


@router.post("/mercadopago")
async def webhook_mercadopago(request: Request):
    raw_body = await request.body()
    notification_payload = _load_notification_payload(raw_body)
    payment_id = extract_notification_payment_id(notification_payload, request)
    signature_status = validate_webhook_signature_from_env(request, data_id=payment_id)

    try:
        payment_payload = fetch_payment(str(payment_id or ""))
    except HTTPException as exc:
        if _is_mercadopago_simulation(notification_payload):
            return _ignored_mercadopago_simulation_response(
                payment_id, signature_status
            )
        raise exc

    payload = normalize_payment_payload(payment_payload, notification_payload)
    tenant_id = _find_tenant_id(payload, request)
    set_current_tenant(UUID(tenant_id))

    db = SessionLocal()
    try:
        return _finish_mercadopago_webhook(
            db,
            tenant_id=tenant_id,
            endpoint_name="POST /api/webhooks/mercadopago",
            payment_id=payment_id,
            signature_status=signature_status,
            notification_payload=notification_payload,
            raw_body=raw_body,
            payload=payload,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar webhook Mercado Pago: {exc}"
        )
    finally:
        db.close()
