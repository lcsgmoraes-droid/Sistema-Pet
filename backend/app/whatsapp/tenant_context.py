"""Helpers de contexto tenant para fluxos WhatsApp fora de Depends."""

from contextlib import contextmanager
from typing import Iterator
from uuid import UUID

from app.tenancy.context import clear_current_tenant, get_current_tenant, set_current_tenant


@contextmanager
def whatsapp_tenant_context(tenant_id) -> Iterator[UUID]:
    """Ativa temporariamente o tenant do fluxo WhatsApp e restaura o contexto anterior."""
    previous_tenant = get_current_tenant()
    tenant_uuid = UUID(str(tenant_id))
    set_current_tenant(tenant_uuid)
    try:
        yield tenant_uuid
    finally:
        if previous_tenant is None:
            clear_current_tenant()
        else:
            set_current_tenant(previous_tenant)
