import hashlib
import hmac
import os
from typing import Any, Callable
from urllib.parse import urlencode

import requests
from fastapi import HTTPException, status

from app.services.sales_channel import normalize_online_sales_channel


TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
MERCADO_PAGO_API_BASE_URL = "https://api.mercadopago.com"


def _env_flag(name: str) -> bool:
    return (os.getenv(name, "") or "").strip().lower() in TRUE_ENV_VALUES


def _public_base_url() -> str:
    value = (
        os.getenv("ECOMMERCE_PUBLIC_BASE_URL")
        or os.getenv("ECOMMERCE_BASE_URL")
        or os.getenv("FRONTEND_URL")
        or "https://corepet.com.br"
    )
    return str(value).strip().rstrip("/")


def _get_access_token() -> str:
    token = (
        os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
        or os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        or ""
    ).strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MERCADO_PAGO_ACCESS_TOKEN nao configurado",
        )
    return token


def is_mercado_pago_provider(provider: str | None = None) -> bool:
    provider_value = provider if provider is not None else os.getenv("ECOMMERCE_PAYMENT_PROVIDER")
    return str(provider_value or "").strip().lower().replace("-", "_") in {
        "mercado_pago",
        "mercadopago",
    }


def normalizar_canal_venda_online(canal: str | None) -> str:
    return normalize_online_sales_channel(canal)


def _delivery_mode(endereco_entrega: str | None, tipo_retirada: str | None) -> str:
    endereco = str(endereco_entrega or "").strip().lower()
    retirada = str(tipo_retirada or "").strip().lower()
    if retirada in {"proprio", "terceiro", "app_loja"} or "retirada" in endereco:
        return "retirada"
    return "entrega"


def _excluded_payment_types(forma_pagamento_tipo: str) -> list[dict[str, str]]:
    if forma_pagamento_tipo == "pix":
        return [{"id": "credit_card"}, {"id": "debit_card"}, {"id": "ticket"}]
    if forma_pagamento_tipo == "cartao_debito":
        return [{"id": "credit_card"}, {"id": "ticket"}, {"id": "bank_transfer"}]
    if forma_pagamento_tipo == "cartao_credito":
        return [{"id": "debit_card"}, {"id": "ticket"}, {"id": "bank_transfer"}]
    return [{"id": "ticket"}]


def _payment_return_url(
    base_url: str,
    payment_status: str,
    pedido_id: str,
    extra_params: dict[str, Any] | None = None,
) -> str:
    params = {
        "view": "pedidos",
        "payment_status": payment_status,
        "pedido_id": pedido_id,
    }
    for key, value in (extra_params or {}).items():
        if value is not None and str(value).strip():
            params[str(key)] = str(value).strip()
    query = urlencode(params)
    return f"{str(base_url or '').strip().rstrip('/')}?{query}"


def build_preference_payload(
    *,
    pedido: Any,
    total: float,
    forma_pagamento_tipo: str,
    endereco_entrega: str | None,
    tipo_retirada: str | None,
    notification_url: str | None = None,
    return_url_base: str | None = None,
    return_url_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_url = _public_base_url()
    payment_return_base_url = str(return_url_base or base_url).strip().rstrip("/")
    pedido_id = str(pedido.pedido_id)
    tenant_id = str(pedido.tenant_id)
    canal = normalizar_canal_venda_online(getattr(pedido, "origem", "") or "ecommerce")
    modo_entrega = _delivery_mode(endereco_entrega, tipo_retirada)
    total_value = round(float(total or 0.0), 2)

    metadata = {
        "pedido_id": pedido_id,
        "tenant_id": tenant_id,
        "canal": canal,
        "payment_method": forma_pagamento_tipo,
        "delivery_mode": modo_entrega,
        "tipo_retirada": tipo_retirada,
        "endereco_entrega": endereco_entrega,
        "tem_entrega": modo_entrega == "entrega",
    }

    return {
        "items": [
            {
                "id": pedido_id,
                "title": f"Pedido CorePet {pedido_id}",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": total_value,
            }
        ],
        "external_reference": pedido_id,
        "metadata": metadata,
        "notification_url": notification_url or f"{base_url}/api/webhooks/mercadopago",
        "back_urls": {
            "success": os.getenv("MERCADO_PAGO_BACK_URL_SUCCESS")
            or _payment_return_url(payment_return_base_url, "success", pedido_id, return_url_params),
            "pending": os.getenv("MERCADO_PAGO_BACK_URL_PENDING")
            or _payment_return_url(payment_return_base_url, "pending", pedido_id, return_url_params),
            "failure": os.getenv("MERCADO_PAGO_BACK_URL_FAILURE")
            or _payment_return_url(payment_return_base_url, "failure", pedido_id, return_url_params),
        },
        "auto_return": "approved",
        "payment_methods": {
            "excluded_payment_types": _excluded_payment_types(forma_pagamento_tipo),
            "installments": 12,
        },
    }


def select_checkout_url(preference: dict[str, Any], *, use_sandbox: bool | None = None) -> str:
    sandbox = _env_flag("MERCADO_PAGO_USE_SANDBOX") if use_sandbox is None else bool(use_sandbox)
    if sandbox:
        return str(preference.get("sandbox_init_point") or preference.get("init_point") or "")
    return str(preference.get("init_point") or preference.get("sandbox_init_point") or "")


def create_preference(
    *,
    pedido: Any,
    total: float,
    forma_pagamento_tipo: str,
    endereco_entrega: str | None,
    tipo_retirada: str | None,
    access_token: str | None = None,
    notification_url: str | None = None,
    return_url_base: str | None = None,
    return_url_params: dict[str, Any] | None = None,
    use_sandbox: bool | None = None,
    http_post: Callable[..., Any] = requests.post,
) -> dict[str, Any]:
    payload = build_preference_payload(
        pedido=pedido,
        total=total,
        forma_pagamento_tipo=forma_pagamento_tipo,
        endereco_entrega=endereco_entrega,
        tipo_retirada=tipo_retirada,
        notification_url=notification_url,
        return_url_base=return_url_base,
        return_url_params=return_url_params,
    )
    token = (access_token or "").strip() or _get_access_token()
    response = http_post(
        f"{MERCADO_PAGO_API_BASE_URL}/checkout/preferences",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )

    if response.status_code >= 400:
        detail = _safe_error_detail(response)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Mercado Pago recusou a preferencia: {detail}",
        )

    preference = response.json()
    checkout_url = select_checkout_url(preference, use_sandbox=use_sandbox)
    if not checkout_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Mercado Pago nao retornou URL de checkout",
        )

    return {
        "provider": "mercadopago",
        "preference_id": preference.get("id"),
        "payment_url": checkout_url,
        "init_point": preference.get("init_point"),
        "sandbox_init_point": preference.get("sandbox_init_point"),
    }


def fetch_payment(
    payment_id: str,
    *,
    access_token: str | None = None,
    http_get: Callable[..., Any] = requests.get,
) -> dict[str, Any]:
    if not payment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_id obrigatorio")

    response = http_get(
        f"{MERCADO_PAGO_API_BASE_URL}/v1/payments/{payment_id}",
        headers={"Authorization": f"Bearer {(access_token or '').strip() or _get_access_token()}"},
        timeout=20,
    )

    if response.status_code >= 400:
        detail = _safe_error_detail(response)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao consultar pagamento Mercado Pago: {detail}",
        )

    return response.json()


def _safe_error_detail(response: Any) -> str:
    try:
        payload = response.json()
        return str(payload.get("message") or payload.get("error") or payload)[:300]
    except Exception:
        return str(getattr(response, "text", "") or f"HTTP {response.status_code}")[:300]


def extract_notification_payment_id(payload: dict[str, Any], request: Any) -> str | None:
    data = payload.get("data") if isinstance(payload, dict) else None
    body_id = data.get("id") if isinstance(data, dict) else None
    query_id = None
    try:
        query_id = request.query_params.get("data.id")
    except Exception:
        query_id = None
    return str(query_id or body_id or payload.get("id") or "").strip() or None


def validate_webhook_signature(
    request: Any,
    secret: str,
    *,
    data_id: str | None = None,
) -> str:
    signature_header = (request.headers.get("x-signature") or "").strip()
    request_id = (request.headers.get("x-request-id") or "").strip()

    if not signature_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura Mercado Pago ausente")

    parts = {}
    for part in signature_header.split(","):
        key, _, value = part.partition("=")
        if key and value:
            parts[key.strip()] = value.strip()

    ts = parts.get("ts")
    received = parts.get("v1")
    if not ts or not received:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura Mercado Pago invalida")

    query_data_id = None
    try:
        query_data_id = request.query_params.get("data.id")
    except Exception:
        query_data_id = None

    resolved_data_id = str(query_data_id or data_id or "").strip()
    manifest = ""
    if resolved_data_id:
        manifest += f"id:{resolved_data_id};"
    if request_id:
        manifest += f"request-id:{request_id};"
    manifest += f"ts:{ts};"

    expected = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura Mercado Pago invalida")

    return "validated"


def validate_webhook_signature_from_env(request: Any, data_id: str | None = None) -> str:
    secret = (os.getenv("MERCADO_PAGO_WEBHOOK_SECRET") or os.getenv("MERCADOPAGO_WEBHOOK_SECRET") or "").strip()
    validate = (
        _env_flag("MERCADO_PAGO_WEBHOOK_VALIDATE_SIGNATURE")
        or (
            _env_flag("ECOMMERCE_PAYMENT_GATEWAY_ENABLED")
            and is_mercado_pago_provider()
        )
    )

    if not validate and not secret:
        return "skipped_by_config"
    if validate and not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MERCADO_PAGO_WEBHOOK_SECRET nao configurado",
        )

    return validate_webhook_signature(request, secret, data_id=data_id)


def normalize_payment_payload(payment: dict[str, Any], notification: dict[str, Any] | None = None) -> dict[str, Any]:
    notification = notification or {}
    metadata = payment.get("metadata") if isinstance(payment.get("metadata"), dict) else {}
    external_reference = payment.get("external_reference")

    normalized_metadata = dict(metadata)
    if external_reference and not normalized_metadata.get("pedido_id"):
        normalized_metadata["pedido_id"] = external_reference

    return {
        "provider": "mercadopago",
        "id": notification.get("id") or payment.get("id"),
        "event": notification.get("action") or notification.get("type") or "payment",
        "status": payment.get("status"),
        "pedido_id": normalized_metadata.get("pedido_id"),
        "metadata": normalized_metadata,
        "payment_method_id": payment.get("payment_method_id"),
        "payment_type_id": payment.get("payment_type_id"),
        "installments": payment.get("installments") or 1,
        "transaction_amount": payment.get("transaction_amount"),
        "date_approved": payment.get("date_approved"),
        "data": {
            "id": payment.get("id"),
            "status": payment.get("status"),
            "metadata": normalized_metadata,
        },
        "mercadopago": {
            "payment": payment,
            "notification": notification,
        },
    }
