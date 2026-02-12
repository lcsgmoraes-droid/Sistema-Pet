from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class TenantSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            # Middleware apenas passa a request adiante
            # Validação de tenant_id acontece em get_current_user_and_tenant (dependency)
            return await call_next(request)

        except Exception as e:
            logger.error(
                f"[TenantSecurityMiddleware] ❌ Erro inesperado: {str(e)}",
                exc_info=True,
            )
            raise
