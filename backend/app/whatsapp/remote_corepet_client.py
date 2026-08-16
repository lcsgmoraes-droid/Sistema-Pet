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
