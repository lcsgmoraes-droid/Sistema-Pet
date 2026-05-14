from fastapi import Request, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from uuid import UUID

from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY

logger = logging.getLogger(__name__)

TENANT_EXEMPT_PATHS = {
    "/auth/register",
    "/auth/login-multitenant",
    "/auth/verify-email",
    "/auth/resend-verification",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/select-tenant",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def _normalize_path(path: str) -> str:
    normalized = path.rstrip("/") or "/"
    if normalized.startswith("/api/"):
        return normalized[4:] or "/"
    return normalized


def _is_tenant_exempt_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized in TENANT_EXEMPT_PATHS or normalized.startswith("/ecommerce/")


def _extract_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


class TenantSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            token = _extract_bearer_token(request)
            if token and not _is_tenant_exempt_path(request.url.path):
                try:
                    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
                except JWTError:
                    # Token invalido continua para as dependencies devolverem o erro oficial.
                    return await call_next(request)

                tenant_id = payload.get("tenant_id")
                try:
                    if not tenant_id:
                        raise ValueError("tenant_id ausente")
                    UUID(str(tenant_id))
                except (TypeError, ValueError):
                    logger.warning(
                        "[TenantSecurityMiddleware] Bloqueando JWT sem tenant_id valido em %s",
                        request.url.path,
                    )
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "detail": "Tenant nao selecionado. Use /auth/select-tenant.",
                        },
                        headers={"WWW-Authenticate": "Bearer"},
                    )

            return await call_next(request)

        except Exception as e:
            logger.error(
                f"[TenantSecurityMiddleware] ❌ Erro inesperado: {str(e)}",
                exc_info=True,
            )
            raise
