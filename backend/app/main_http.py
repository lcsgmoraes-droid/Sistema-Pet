"""HTTP middleware and exception handler registration."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import ALLOWED_ORIGINS
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.request_context import RequestContextMiddleware, get_request_id
from app.middlewares.request_logging import RequestLoggingMiddleware
from app.middlewares.security_audit import SecurityAuditMiddleware
from app.middlewares.security_headers import SecurityHeadersMiddleware
from app.middlewares.tenant_middleware import TenantSecurityMiddleware
from app.security.error_sanitization import (
    internal_error_payload,
    is_strict_runtime_environment,
    sanitize_validation_errors,
)
from app.tenancy.context import TenantContextMiddleware
from app.tenancy.middleware import TenancyMiddleware

logger = logging.getLogger(__name__)


def register_proxy_headers_middleware(app: FastAPI) -> None:
    """Register proxy header handling for HTTPS redirects behind nginx."""

    @app.middleware("http")
    async def proxy_headers_middleware(request: Request, call_next):
        if request.headers.get("X-Forwarded-Proto") == "https":
            request.scope["scheme"] = "https"
        response = await call_next(request)
        return response


def configure_middlewares(app: FastAPI, limiter) -> None:
    """Register global middlewares in the established execution order."""
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityAuditMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(TenantSecurityMiddleware)
    app.add_middleware(TenancyMiddleware)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.exception_handler(RateLimitExceeded)
    async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
        logger.warning(
            f"[RATE_LIMIT] Rate limit exceeded: {get_remote_address(request)} on {request.url.path}"
        )
        return JSONResponse(
            status_code=429,
            content={
                "error": "too_many_requests",
                "message": "Muitas requisições. Aguarde alguns minutos e tente novamente.",
            },
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Require-2FA"],
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register API exception handlers."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        safe_errors = sanitize_validation_errors(exc.errors())
        logger.warning(
            "[VALIDATION] Request rejeitada: method=%s path=%s fields=%s",
            request.method,
            request.url.path,
            [{"loc": error["loc"], "type": error["type"]} for error in safe_errors],
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Dados inválidos",
                "details": safe_errors,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code >= 500:
            logger.error(
                "[HTTP] HTTP %s retornado pela aplicacao: method=%s path=%s",
                exc.status_code,
                request.method,
                request.url.path,
            )
            if is_strict_runtime_environment():
                return JSONResponse(
                    status_code=exc.status_code,
                    content=internal_error_payload(get_request_id()),
                    headers=exc.headers,
                )
        elif exc.status_code != 404 or "Segmento não encontrado" not in str(exc.detail):
            logger.warning(
                "[HTTP] HTTP %s: method=%s path=%s",
                exc.status_code,
                request.method,
                request.url.path,
            )

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        from app.utils.logger import logger as structured_logger

        strict_runtime = is_strict_runtime_environment()
        request_id = get_request_id()
        structured_message = (
            "Erro interno nao tratado" if strict_runtime else f"Erro 500: {str(exc)}"
        )
        structured_logger.error(
            event="unhandled_exception",
            message=structured_message,
            path=request.url.path,
            method=request.method,
            exception_type=type(exc).__name__,
            request_id=request_id,
        )
        if strict_runtime:
            logger.error(
                "[ERROR] Erro 500 sem detalhes: type=%s method=%s path=%s request_id=%s",
                type(exc).__name__,
                request.method,
                request.url.path,
                request_id,
            )
        else:
            logger.error("[ERROR] Erro 500: %s", str(exc), exc_info=True)

        if strict_runtime:
            return JSONResponse(
                status_code=500,
                content=internal_error_payload(request_id),
            )

        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "Erro interno no servidor",
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )
