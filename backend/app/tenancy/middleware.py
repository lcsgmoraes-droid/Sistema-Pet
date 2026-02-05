"""
Middleware de Multi-Tenancy (Cleanup Phase 1.2)
================================================

RESPONSABILIDADE REDUZIDA:
- Apenas limpa o contexto de tenant ao final de cada request
- NÃO extrai tenant_id
- NÃO decodifica JWT
- NÃO define tenant via set_current_tenant

FONTE ÚNICA DE TENANT:
- get_current_user_and_tenant (app/auth/dependencies.py)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from app.tenancy.context import clear_current_tenant


class TenancyMiddleware(BaseHTTPMiddleware):
    """
    Middleware minimalista para multi-tenancy.
    
    Após Phase 1.2:
    - Remove toda lógica de extração de tenant
    - Remove todos os fallbacks perigosos
    - Apenas garante limpeza do contexto
    
    Tenant é definido SOMENTE por get_current_user_and_tenant.
    """
    
    async def dispatch(self, request, call_next):
        try:
            # Processar request sem tocar em tenant
            response = await call_next(request)
            return response
        finally:
            # Garantir limpeza do contexto ao final do request
            clear_current_tenant()