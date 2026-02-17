from contextvars import ContextVar
from typing import Optional
from uuid import UUID
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_current_tenant: ContextVar[Optional[UUID]] = ContextVar(
    "current_tenant", default=None
)

def set_current_tenant(tenant_id: UUID):
    _current_tenant.set(tenant_id)

def clear_current_tenant():
    _current_tenant.set(None)

def get_current_tenant() -> Optional[UUID]:
    return _current_tenant.get()

# Aliases
set_tenant_context = set_current_tenant
get_current_tenant_id = get_current_tenant
clear_tenant_context = clear_current_tenant


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware APENAS para isolamento entre requests.
    NÃO valida tenant.
    NÃO seta tenant.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        clear_current_tenant()
        response = await call_next(request)
        return response