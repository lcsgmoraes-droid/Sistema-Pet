"""
Request Context Middleware - Pré-Prod Bloco 4
==============================================

Middleware para observabilidade e correlação de logs em produção.

Garante que:
1. Todo request tem request_id único (UUID)
2. request_id é propagado via contextvars
3. request_id é incluído automaticamente em logs
4. Contexto suficiente para diagnóstico (método, path, status, duração)
5. Dados sensíveis NÃO são logados

Autor: Sistema Pet - Pré-Prod Block 4
Data: 2026-02-05
"""

import os
import re
import time
import uuid
from typing import Optional
import asyncio
import anyio

from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from fastapi import Request
from contextvars import ContextVar
import logging

from app.services.error_event_reporter import record_request_event
from app.services.request_failure_diagnostics import (
    CANCELLATION_CODES,
    exception_diagnostics,
)
from app.services.journey_event_reporter import record_http_journey_event
from app.security.error_sanitization import is_strict_runtime_environment
from app.utils.logger import clear_context as clear_log_context
from app.utils.logger import set_endpoint, set_trace_id

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


SLOW_REQUEST_LOG_MS = _env_int("REQUEST_CONTEXT_SLOW_MS", 3000)
REQUEST_ID_MAX_LENGTH = 80
REQUEST_ID_SAFE_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def _record_http_journey_event_safely(**event) -> None:
    """Garante que uma falha de telemetria nunca altere a resposta do cliente."""

    try:
        record_http_journey_event(**event)
    except Exception:
        logger.debug("Journey telemetry failed", exc_info=False)


# ============================================================================
# CONTEXTVARS PARA REQUEST_ID E METADATA
# ============================================================================

request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
request_method_ctx: ContextVar[Optional[str]] = ContextVar(
    "request_method", default=None
)
request_path_ctx: ContextVar[Optional[str]] = ContextVar("request_path", default=None)


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================


def generate_request_id() -> str:
    """
    Gera novo request_id único (UUID4).

    Returns:
        String UUID no formato: "a1b2c3d4-e5f6-..."
    """
    return str(uuid.uuid4())


def normalize_request_id(value: Optional[str]) -> str:
    """
    Retorna um request_id seguro para log/header.

    IDs vindos do cliente so sao aceitos quando curtos e compostos por
    caracteres seguros. Qualquer valor vazio, longo ou estranho vira UUID novo.
    """
    candidate = (value or "").strip()
    if (
        candidate
        and len(candidate) <= REQUEST_ID_MAX_LENGTH
        and REQUEST_ID_SAFE_PATTERN.fullmatch(candidate)
    ):
        return candidate
    return generate_request_id()


def set_request_id(request_id: str) -> None:
    """Define request_id no contexto da request atual"""
    request_id_ctx.set(request_id)


def get_request_id() -> Optional[str]:
    """Obtém request_id do contexto da request atual"""
    return request_id_ctx.get()


def set_request_metadata(method: str, path: str) -> None:
    """Define metadata da request no contexto"""
    request_method_ctx.set(method)
    request_path_ctx.set(path)


def get_request_metadata() -> dict:
    """Obtém metadata da request do contexto"""
    return {
        "request_id": request_id_ctx.get(),
        "method": request_method_ctx.get(),
        "path": request_path_ctx.get(),
    }


def clear_request_context() -> None:
    """Limpa contexto da request após processamento"""
    request_id_ctx.set(None)
    request_method_ctx.set(None)
    request_path_ctx.set(None)


# ============================================================================
# MIDDLEWARE
# ============================================================================


class _RequestTelemetry:
    def __init__(self, request: Request, request_id: str):
        self.request = request
        self.request_id = request_id
        self.started_at = time.perf_counter()
        self.status_code = None
        self.response_complete = False
        self.disconnected = False
        self.replayed = False
        self.emitted = False
        self.exception = None

    async def emit(self) -> None:
        if self.emitted:
            return
        self.emitted = True
        duration_ms = round((time.perf_counter() - self.started_at) * 1000, 2)
        exception = self.exception
        diagnostics = exception_diagnostics(exception) if exception else {}
        if self.disconnected:
            diagnostics["diagnostic_code"] = "client_disconnected"
        strict_runtime = is_strict_runtime_environment()
        event = {
            "request": self.request,
            "request_id": self.request_id,
            "method": self.request.method,
            "path": self.request.url.path,
            "status_code": self.status_code,
            "status_source": "asgi_response_start" if self.status_code else "not_sent",
            "duration_ms": duration_ms,
            "exception_type": type(exception).__name__ if exception else None,
            "exception_message": (
                str(exception)[:200] if exception and not strict_runtime else None
            ),
            **diagnostics,
        }
        cancellation = diagnostics.get("diagnostic_code") in CANCELLATION_CODES
        event["response_incomplete"] = (
            self.status_code is not None and not self.response_complete
        )
        if exception and event["response_incomplete"] and not cancellation:
            event["diagnostic_code"] = "response_stream_failure"
        log_level = (
            logging.WARNING
            if cancellation
            else (
                logging.ERROR
                if exception or (self.status_code or 0) >= 500
                else logging.WARNING
                if (self.status_code or 0) >= 400 or duration_ms >= SLOW_REQUEST_LOG_MS
                else logging.DEBUG
            )
        )
        logger.log(
            log_level,
            "Request cancelled" if cancellation else "Request finished",
            extra={key: value for key, value in event.items() if key != "request"},
        )

        def persist():
            try:
                record_request_event(**event)
            except Exception:
                logger.debug("Request telemetry failed", exc_info=False)
            if not cancellation:
                journey = dict(
                    request=self.request,
                    request_id=self.request_id,
                    method=self.request.method,
                    path=self.request.url.path,
                    status_code=self.status_code,
                    duration_ms=duration_ms,
                    replayed=self.replayed,
                )
                if exception is not None:
                    journey["exception"] = True
                _record_http_journey_event_safely(**journey)

        # Each reporter opens its own session in this thread; no request session
        # crosses threads or blocks the API event loop while telemetry is saved.
        # A cancelled client request must not cancel the diagnostic write itself.
        with anyio.CancelScope(shield=True):
            await run_in_threadpool(persist)


class ObservedErrorResponse(JSONResponse):
    """Observe the 500 sent outside user middleware by ServerErrorMiddleware."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        telemetry = scope.get("_ops_request_telemetry")

        async def observed_send(message: Message):
            if message["type"] == "http.response.start" and telemetry is not None:
                MutableHeaders(scope=message)["X-Request-ID"] = telemetry.request_id
            await send(message)
            if message["type"] == "http.response.start" and telemetry is not None:
                telemetry.status_code = message["status"]
            elif (
                message["type"] == "http.response.body"
                and not message.get("more_body", False)
                and telemetry is not None
            ):
                telemetry.response_complete = True

        try:
            await super().__call__(scope, receive, observed_send)
        finally:
            if telemetry is not None:
                await telemetry.emit()


class RequestContextMiddleware:
    """Observe HTTP directly, without BaseHTTPMiddleware tasks/response streams."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = normalize_request_id(request.headers.get("X-Request-ID"))
        telemetry = _RequestTelemetry(request, request_id)
        scope["_ops_request_telemetry"] = telemetry
        request.state.request_id = request_id
        set_request_id(request_id)
        set_trace_id(request_id)
        set_request_metadata(request.method, request.url.path)
        set_endpoint(request.url.path)

        async def observed_receive() -> Message:
            message = await receive()
            if message["type"] == "http.disconnect" and not telemetry.response_complete:
                telemetry.disconnected = True
            return message

        async def observed_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                telemetry.replayed = (
                    headers.get("X-Idempotency-Replayed", "").lower() == "true"
                )
            await send(message)
            if message["type"] == "http.response.start":
                telemetry.status_code = message["status"]
            elif message["type"] == "http.response.pathsend" or (
                message["type"] == "http.response.body"
                and not message.get("more_body", False)
            ):
                telemetry.response_complete = True

        try:
            await self.app(scope, observed_receive, observed_send)
            await telemetry.emit()
        except asyncio.CancelledError as exc:
            telemetry.exception = exc
            await telemetry.emit()
            raise
        except Exception as exc:
            telemetry.exception = exc
            app = scope.get("app")
            has_observed_handler = bool(
                getattr(
                    getattr(app, "state", None), "ops_observed_error_handler", False
                )
            )
            # The outer server-error handler sends the 500 after this middleware
            # unwinds. Keep pending telemetry until its response really starts.
            if telemetry.status_code is not None or not has_observed_handler:
                await telemetry.emit()
            raise
        finally:
            clear_request_context()
            clear_log_context()


# ============================================================================
# LOGGING FILTER (OPCIONAL)
# ============================================================================


class RequestContextFilter(logging.Filter):
    """
    Filtro de logging que adiciona request_id automaticamente a TODOS os logs.

    Uso:
    ----
    import logging

    handler = logging.StreamHandler()
    handler.addFilter(RequestContextFilter())
    logging.getLogger().addHandler(handler)

    Resultado:
    ----------
    Qualquer log feito durante uma request terá request_id automaticamente:

    >>> logger.info("Processando pagamento")
    # Output: {"message": "Processando pagamento", "request_id": "a1b2c3d4-..."}
    """

    def filter(self, record):
        """Adiciona request_id ao record de log"""
        record.request_id = get_request_id() or "-"
        record.request_method = request_method_ctx.get() or "-"
        record.request_path = request_path_ctx.get() or "-"
        return True


# ============================================================================
# FUNÇÕES DE UTILIDADE
# ============================================================================


def get_current_request_context() -> dict:
    """
    Retorna o contexto completo da request atual.

    Útil para:
    - Logging customizado
    - Rastreamento de operações
    - Debug

    Returns:
        {
            'request_id': str | None,
            'method': str | None,
            'path': str | None
        }

    Example:
        >>> context = get_current_request_context()
        >>> logger.info(f"Processing order", extra=context)
    """
    return get_request_metadata()


def log_with_context(level: int, message: str, **kwargs) -> None:
    """
    Helper para logging com contexto de request automaticamente.

    Args:
        level: logging.INFO, logging.WARNING, etc.
        message: Mensagem do log
        **kwargs: Campos extras para o log

    Example:
        >>> log_with_context(logging.INFO, "User logged in", user_id=123)
        # Log terá automaticamente request_id, method, path, user_id
    """
    context = get_current_request_context()
    logger.log(level, message, extra={**context, **kwargs})
