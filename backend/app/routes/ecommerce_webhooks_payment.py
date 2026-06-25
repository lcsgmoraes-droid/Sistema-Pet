"""Normalizacao e aplicacao de pagamento em webhooks de ecommerce."""

from fastapi import HTTPException, status

from app.pedido_models import Pedido
from app.services.mercado_pago_checkout import extract_gateway_financials


PAYMENT_METHODS_ONLINE_ACEITOS = {
    "pix": "pix",
    "credit_card": "cartao_credito",
    "debit_card": "cartao_debito",
}

PEDIDO_ID_SOURCES = (
    ("root", "pedido_id"),
    ("root", "external_reference"),
    ("metadata", "pedido_id"),
    ("metadata", "external_reference"),
    ("data", "pedido_id"),
    ("data", "external_reference"),
    ("data_metadata", "pedido_id"),
    ("data_metadata", "external_reference"),
    ("mp_payment", "external_reference"),
    ("mp_metadata", "pedido_id"),
    ("mp_metadata", "external_reference"),
)

PAYMENT_PREFERENCE_ID_SOURCES = (
    ("root", "payment_preference_id"),
    ("root", "preference_id"),
    ("metadata", "payment_preference_id"),
    ("metadata", "preference_id"),
    ("data", "payment_preference_id"),
    ("data", "preference_id"),
    ("data_metadata", "payment_preference_id"),
    ("data_metadata", "preference_id"),
    ("mp_payment", "payment_preference_id"),
    ("mp_payment", "preference_id"),
    ("mp_metadata", "payment_preference_id"),
    ("mp_metadata", "preference_id"),
    ("mp_order", "id"),
    ("mp_notification", "payment_preference_id"),
    ("mp_notification", "preference_id"),
    ("mp_notification_data", "payment_preference_id"),
    ("mp_notification_data", "preference_id"),
)


def _map_payment_status(payload: dict) -> str | None:
    status_value = (
        payload.get("status")
        or (payload.get("data") or {}).get("status")
        or (payload.get("payment") or {}).get("status")
    )

    if not status_value:
        return None

    raw = str(status_value).strip().lower()
    mapping = {
        "paid": "aprovado",
        "approved": "aprovado",
        "authorized": "pendente",
        "processing": "pendente",
        "in_process": "pendente",
        "pending": "pendente",
        "waiting_payment": "pendente",
        "refused": "recusado",
        "rejected": "recusado",
        "failed": "recusado",
        "canceled": "cancelado",
        "cancelled": "cancelado",
        "refunded": "cancelado",
        "chargedback": "cancelado",
        "charged_back": "cancelado",
    }
    return mapping.get(raw)


def _find_pedido_id(payload: dict) -> str | None:
    return _find_payload_value(payload, PEDIDO_ID_SOURCES)


def _first_non_empty(*values) -> str | None:
    for value in values:
        if value is None:
            continue
        normalized = str(value).strip()
        if normalized:
            return normalized
    return None


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _payment_payload_contexts(payload: dict) -> dict[str, dict]:
    data = _as_dict(payload.get("data"))
    metadata = _as_dict(payload.get("metadata"))
    data_metadata = _as_dict(data.get("metadata"))
    mercadopago = _as_dict(payload.get("mercadopago"))
    mp_payment = _as_dict(mercadopago.get("payment"))
    mp_metadata = _as_dict(mp_payment.get("metadata"))
    mp_order = _as_dict(mp_payment.get("order"))
    mp_notification = _as_dict(mercadopago.get("notification"))
    mp_notification_data = _as_dict(mp_notification.get("data"))

    return {
        "root": payload,
        "data": data,
        "metadata": metadata,
        "data_metadata": data_metadata,
        "mp_payment": mp_payment,
        "mp_metadata": mp_metadata,
        "mp_order": mp_order,
        "mp_notification": mp_notification,
        "mp_notification_data": mp_notification_data,
    }


def _find_payload_value(
    payload: dict, sources: tuple[tuple[str, str], ...]
) -> str | None:
    contexts = _payment_payload_contexts(payload)
    return _first_non_empty(
        *(contexts[context_name].get(key) for context_name, key in sources)
    )


def _find_payment_preference_id(payload: dict) -> str | None:
    return _find_payload_value(payload, PAYMENT_PREFERENCE_ID_SOURCES)


def _find_pedido_for_payment(db, *, tenant_id: str, payload: dict) -> Pedido | None:
    pedido_id = _find_pedido_id(payload)
    if pedido_id:
        pedido = (
            db.query(Pedido)
            .filter(Pedido.pedido_id == pedido_id, Pedido.tenant_id == tenant_id)
            .first()
        )
        if pedido:
            return pedido

    payment_preference_id = _find_payment_preference_id(payload)
    if not payment_preference_id:
        return None

    return (
        db.query(Pedido)
        .filter(
            Pedido.payment_preference_id == payment_preference_id,
            Pedido.tenant_id == tenant_id,
        )
        .order_by(Pedido.id.desc())
        .first()
    )


def _normalizar_payment_method_online(payment_method: str | None) -> str:
    raw = str(payment_method or "").strip().lower()
    if raw not in PAYMENT_METHODS_ONLINE_ACEITOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forma de pagamento online nao permitida para app/ecommerce",
        )
    return raw


def _safe_installments(*values) -> int:
    for value in values:
        if value is None:
            continue
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            continue
    return 1


def _extrair_pagamento_mercadopago(payload: dict, data: dict, metadata: dict) -> tuple:
    mp_method_id = (
        payload.get("payment_method_id")
        or data.get("payment_method_id")
        or metadata.get("payment_method_id")
    )
    mp_type_id = (
        payload.get("payment_type_id")
        or data.get("payment_type_id")
        or metadata.get("payment_type_id")
    )
    if str(mp_method_id or "").strip().lower() == "pix":
        return "pix", _safe_installments(
            payload.get("installments"), data.get("installments")
        )
    if str(mp_type_id or "").strip().lower() in {"credit_card", "debit_card"}:
        return str(mp_type_id).strip().lower(), _safe_installments(
            payload.get("installments"), data.get("installments")
        )
    return None, 1


def _extrair_pagamento_pagarme(charges) -> tuple:
    if not charges or not isinstance(charges, list):
        return None, 1
    charge = charges[0]
    if not isinstance(charge, dict):
        return None, 1
    payment_method = charge.get("payment_method")
    last_tx = charge.get("last_transaction") or {}
    installments = (
        _safe_installments(last_tx.get("installments"))
        if isinstance(last_tx, dict)
        else 1
    )
    return payment_method, installments


def _extrair_pagamento_fallback(payload: dict, metadata: dict) -> tuple:
    payment_method = (
        metadata.get("payment_method")
        or metadata.get("metodo_pagamento")
        or payload.get("payment_method")
        or payload.get("metodo_pagamento")
    )
    installments = _safe_installments(
        metadata.get("installments"),
        metadata.get("parcelas"),
        payload.get("installments"),
        payload.get("parcelas"),
    )
    return payment_method, installments


def _extrair_pagamento_do_webhook(payload: dict) -> tuple:
    """
    Extrai payment_method e installments do payload do Pagar.me.
    Suporta tanto o webhook real (com charges[]) quanto simulacoes com metadata.
    """
    data = payload.get("data") or {}
    metadata = payload.get("metadata") or data.get("metadata") or {}
    charges = data.get("charges") or payload.get("charges") or []

    payment_method, installments = _extrair_pagamento_mercadopago(
        payload, data, metadata
    )
    if payment_method:
        return str(payment_method or "").strip().lower(), installments

    payment_method, installments = _extrair_pagamento_pagarme(charges)
    if not payment_method:
        payment_method, installments = _extrair_pagamento_fallback(payload, metadata)

    return str(payment_method or "").strip().lower(), installments


def _extrair_financeiro_gateway_online(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}

    provider = (
        str(payload.get("gateway_provider") or payload.get("provider") or "")
        .strip()
        .lower()
    )
    if provider not in {"mercadopago", "mercado_pago"} and not isinstance(
        payload.get("mercadopago"), dict
    ):
        return {}

    return extract_gateway_financials(payload)


def _apply_payment_status_update(
    db,
    *,
    tenant_id: str,
    payload: dict,
) -> tuple[bool, int | None, Pedido | None, str | None]:
    pedido_status = _map_payment_status(payload)
    if not pedido_status:
        return False, None, None, None

    pedido = _find_pedido_for_payment(db, tenant_id=tenant_id, payload=payload)
    if not pedido:
        return False, None, None, pedido_status

    pedido.status = pedido_status
    venda_id = None
    if pedido_status == "aprovado":
        payment_method, _ = _extrair_pagamento_do_webhook(payload)
        _normalizar_payment_method_online(payment_method)
        from app.routes.ecommerce_webhooks_sales import _integrar_venda_ao_motor

        venda_id = _integrar_venda_ao_motor(db, pedido, payload)

    return True, venda_id, pedido, pedido_status
