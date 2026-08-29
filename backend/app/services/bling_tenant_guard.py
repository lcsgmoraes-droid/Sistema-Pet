"""Isolamento do conector Bling global enquanto ele pertence a um unico tenant."""

from __future__ import annotations

import os
from uuid import UUID

from app.tenancy.context import get_current_tenant


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


def resolver_tenant_bling(
    payload: dict | None = None,
    *,
    db=None,
) -> UUID | None:
    """Resolve o tenant pelo companyId assinado e preserva o legado como fallback."""
    if payload:
        from app.services.bling_connection_service import (
            resolve_bling_webhook_tenant,
            webhook_company_id,
        )

        # Se o Bling informou a empresa, o identificador precisa estar mapeado.
        # Nao fazemos fallback para outro CNPJ, mesmo que exista uma integracao
        # legada configurada no ambiente.
        if webhook_company_id(payload):
            return resolve_bling_webhook_tenant(payload, db=db)

    current = get_current_tenant()
    if current:
        return current

    configured = bling_tenant_id_configurado()
    return UUID(configured) if configured else None
