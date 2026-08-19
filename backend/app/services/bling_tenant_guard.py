"""Isolamento do conector Bling global enquanto ele pertence a um unico tenant."""

from __future__ import annotations

import os
from uuid import UUID


BLING_TENANT_ENV = "BLING_WEBHOOK_TENANT_ID"


def bling_tenant_id_configurado() -> str | None:
    value = str(os.getenv(BLING_TENANT_ENV) or "").strip()
    if not value:
        return None
    try:
        return str(UUID(value))
    except (TypeError, ValueError):
        return None


def tenant_pode_usar_bling_global(tenant_id) -> bool:
    configurado = bling_tenant_id_configurado()
    if not configurado or tenant_id is None:
        return False
    try:
        return str(UUID(str(tenant_id))) == configurado
    except (TypeError, ValueError):
        return False
