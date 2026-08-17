"""Cliente somente leitura para consultar dados reais do CorePet em produção."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


def remote_data_enabled() -> bool:
    return bool((os.getenv("COREPET_WHATSAPP_DATA_BASE_URL") or "").strip())


def _get_remote_data(
    tenant_id: str,
    path: str,
    *,
    params: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    base_url = (os.getenv("COREPET_WHATSAPP_DATA_BASE_URL") or "").strip().rstrip("/")
    token = (os.getenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN") or "").strip()
    if not base_url or not token:
        return None

    try:
        response = httpx.get(
            f"{base_url}/{tenant_id}/{path.lstrip('/')}",
            params=params or {},
            headers={"X-Internal-Token": token},
            timeout=12.0,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except Exception as error:
        logger.warning("Falha na ponte de dados do CorePet (%s): %s", path, error)
        return None


def _post_remote_data(
    tenant_id: str,
    path: str,
    *,
    payload: dict[str, Any],
    idempotency_key: Optional[str] = None,
    require_write_token: bool = False,
) -> Optional[dict[str, Any]]:
    base_url = (os.getenv("COREPET_WHATSAPP_DATA_BASE_URL") or "").strip().rstrip("/")
    token = (os.getenv("WHATSAPP_ORCHESTRATOR_INTERNAL_TOKEN") or "").strip()
    write_token = (os.getenv("WHATSAPP_ORCHESTRATOR_WRITE_TOKEN") or "").strip()
    if not base_url or not token or (require_write_token and not write_token):
        return None

    headers = {"X-Internal-Token": token}
    if require_write_token:
        headers["X-Internal-Write-Token"] = write_token
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    try:
        response = httpx.post(
            f"{base_url}/{tenant_id}/{path.lstrip('/')}",
            json=payload,
            headers=headers,
            timeout=20.0,
        )
        response.raise_for_status()
        response_payload = response.json()
        return response_payload if isinstance(response_payload, dict) else None
    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code
        detail = ""
        if 400 <= status_code < 500:
            try:
                error_payload = error.response.json()
            except ValueError:
                error_payload = None
            if isinstance(error_payload, dict):
                detail = str(error_payload.get("detail") or "").strip()
        logger.warning(
            "Ponte de dados do CorePet recusou %s com status %s: %s",
            path,
            status_code,
            detail or "sem detalhe seguro",
        )
        return {
            "success": False,
            "status_code": status_code,
            "detail": detail[:500],
        }
    except Exception as error:
        logger.warning("Falha na ponte de dados do CorePet (%s): %s", path, error)
        return None


def fetch_remote_catalog(
    tenant_id: str,
    query: str,
    *,
    categoria: Optional[str] = None,
    limite: int = 5,
) -> Optional[dict[str, Any]]:
    params: dict[str, Any] = {"query": query, "limit": limite}
    if categoria:
        params["categoria"] = categoria
    return _get_remote_data(tenant_id, "catalog-data", params=params)


def fetch_remote_customer_context(
    tenant_id: str,
    *,
    phone: Optional[str] = None,
    customer_id: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    params: dict[str, Any] = {}
    if phone:
        params["phone"] = phone
    if customer_id is not None:
        params["customer_id"] = customer_id
    return _get_remote_data(tenant_id, "customer-context-data", params=params)


def fetch_remote_store_context(tenant_id: str) -> Optional[dict[str, Any]]:
    return _get_remote_data(tenant_id, "store-context-data")


def fetch_remote_order_preview(
    tenant_id: str,
    *,
    phone: str,
    items: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    return _post_remote_data(
        tenant_id,
        "order-preview-data",
        payload={"phone": phone, "items": items},
    )


def create_remote_order(
    tenant_id: str,
    *,
    phone: str,
    items: list[dict[str, Any]],
    fulfillment: str,
    payment_method: dict[str, Any],
    delivery_address: Optional[str],
    idempotency_key: str,
) -> Optional[dict[str, Any]]:
    return _post_remote_data(
        tenant_id,
        "order-create-data",
        payload={
            "phone": phone,
            "items": items,
            "fulfillment": fulfillment,
            "payment_method": payment_method,
            "delivery_address": delivery_address,
        },
        idempotency_key=idempotency_key,
        require_write_token=True,
    )
