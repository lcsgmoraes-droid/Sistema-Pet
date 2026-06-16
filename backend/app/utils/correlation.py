from __future__ import annotations

from contextlib import contextmanager
import hashlib
import re
import uuid
from typing import Any, Iterator

from app.middlewares import request_context
from app.utils.logger import endpoint_ctx, trace_id_ctx


_SOURCE_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9.]+")
_MAX_CORRELATION_ID_LENGTH = 80


def _safe_source(source: str | None) -> str:
    normalized = _SOURCE_SAFE_PATTERN.sub("-", str(source or "job").strip())
    normalized = normalized.strip(".-")
    return (normalized or "job")[:42]


def _safe_request_id(value: Any) -> str | None:
    candidate = str(value or "").strip()
    if (
        candidate
        and len(candidate) <= request_context.REQUEST_ID_MAX_LENGTH
        and request_context.REQUEST_ID_SAFE_PATTERN.fullmatch(candidate)
    ):
        return candidate
    return None


def derive_correlation_id(source: str, reference: Any | None = None) -> str:
    """Build a safe correlation id for jobs and external integrations."""
    source_key = _safe_source(source)
    if reference is None:
        suffix = str(uuid.uuid4())
    else:
        raw = str(reference).encode("utf-8", errors="replace")
        suffix = hashlib.sha256(raw).hexdigest()[:20]
    return f"{source_key}-{suffix}"[:_MAX_CORRELATION_ID_LENGTH]


def current_correlation_id(
    source: str,
    *,
    reference: Any | None = None,
    correlation_id: Any | None = None,
) -> str:
    provided = _safe_request_id(correlation_id)
    if provided:
        return provided

    active_request_id = request_context.get_request_id()
    if active_request_id:
        return active_request_id

    return derive_correlation_id(source, reference)


@contextmanager
def operation_correlation_context(
    source: str,
    *,
    reference: Any | None = None,
    correlation_id: Any | None = None,
    method: str = "JOB",
    path: str | None = None,
) -> Iterator[str]:
    """Temporarily expose a job/integration correlation id through request contextvars."""
    resolved = current_correlation_id(
        source, reference=reference, correlation_id=correlation_id
    )
    endpoint = path or source

    request_id_token = request_context.request_id_ctx.set(resolved)
    method_token = request_context.request_method_ctx.set(method)
    path_token = request_context.request_path_ctx.set(endpoint)
    trace_token = trace_id_ctx.set(resolved)
    endpoint_token = endpoint_ctx.set(endpoint)

    try:
        yield resolved
    finally:
        request_context.request_id_ctx.reset(request_id_token)
        request_context.request_method_ctx.reset(method_token)
        request_context.request_path_ctx.reset(path_token)
        trace_id_ctx.reset(trace_token)
        endpoint_ctx.reset(endpoint_token)
