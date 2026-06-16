"""
Middleware de logging de requests
Loga método, path, status_code e tempo de resposta
NÃO loga body nem headers sensíveis (segurança)
"""

import os
import time
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.middlewares.request_context import get_request_id
from app.utils.logger import logger


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


SLOW_REQUEST_LOG_MS = _env_int("REQUEST_LOGGING_SLOW_MS", 3000)
QUIET_PATHS = {"/health", "/health/watchdog"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging estruturado de requests HTTP"""

    async def dispatch(self, request: Request, call_next):
        # Capturar timestamp de início
        start_time = time.time()

        # Processar request
        response = await call_next(request)

        # Calcular tempo de resposta (em ms)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        path = request.url.path
        status_code = response.status_code
        request_id = get_request_id() or response.headers.get("X-Request-ID")

        if path in QUIET_PATHS and status_code < 500:
            return response

        if status_code >= 500:
            log_method = logger.error
        elif status_code >= 400 or duration_ms >= SLOW_REQUEST_LOG_MS:
            log_method = logger.warning
        else:
            log_method = logger.debug

        log_method(
            event="http_request",
            message=f"{request.method} {path}",
            method=request.method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            client_ip=request.client.host if request.client else None,
        )

        return response
