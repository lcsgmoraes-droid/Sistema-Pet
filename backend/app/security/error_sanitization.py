"""Shared safeguards for public errors and production telemetry."""

from __future__ import annotations

import re
from typing import Any


STRICT_ENVIRONMENTS = {"production", "prod", "staging"}

# Pydantic v2 prefixes a @validator-raised ValueError/AssertionError message
# with "Value error, "/"Assertion failed, " — stripped before showing it to
# the user, who doesn't care about that internal framing.
_PYDANTIC_VALIDATOR_PREFIX = re.compile(r"^(Value error|Assertion failed), ")


def is_strict_runtime_environment() -> bool:
    """Return the current runtime mode without freezing config at import time."""
    from app import config as app_config

    environment = str(getattr(app_config, "ENVIRONMENT", "development") or "")
    return environment.strip().lower() in STRICT_ENVIRONMENTS


def sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep field diagnostics and the validator's own message; still remove
    the submitted value and any other unsafe context.

    Validators in this codebase (`@validator`/`@field_validator`) are written
    to raise only static, Portuguese, user-facing text and never interpolate
    the submitted value into the message — that invariant is what makes it
    safe to pass `msg` through unmodified here. `input`/`ctx` (where the real
    submitted value lives) are always dropped below, regardless of type.
    """
    sanitized: list[dict[str, Any]] = []
    for error in errors:
        error_type = str(error.get("type") or "validation_error")
        message = str(error.get("msg") or "Valor invalido")
        message = _PYDANTIC_VALIDATOR_PREFIX.sub("", message, count=1)

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
