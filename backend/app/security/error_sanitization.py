"""Shared safeguards for public errors and production telemetry."""

from __future__ import annotations

from typing import Any


STRICT_ENVIRONMENTS = {"production", "prod", "staging"}


def is_strict_runtime_environment() -> bool:
    """Return the current runtime mode without freezing config at import time."""
    from app import config as app_config

    environment = str(getattr(app_config, "ENVIRONMENT", "development") or "")
    return environment.strip().lower() in STRICT_ENVIRONMENTS


def sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep field diagnostics while removing submitted values and unsafe context."""
    sanitized: list[dict[str, Any]] = []
    for error in errors:
        error_type = str(error.get("type") or "validation_error")
        message = str(error.get("msg") or "Valor invalido")
        if error_type.startswith(("value_error", "assertion_error")):
            message = "Valor invalido"

        location = error.get("loc") or ()
        sanitized.append(
            {
                "type": error_type,
                "loc": [item for item in location if isinstance(item, (str, int))],
                "msg": message[:160],
            }
        )
    return sanitized


def internal_error_payload(request_id: str | None = None) -> dict[str, str]:
    """Build the only public payload allowed for server errors in strict runtimes."""
    payload = {
        "error": "internal_server_error",
        "message": "Erro interno no servidor. Nossa equipe foi notificada.",
    }
    if request_id:
        payload["request_id"] = request_id
    return payload
