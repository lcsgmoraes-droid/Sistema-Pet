from __future__ import annotations

import re
from urllib.parse import urlparse


_TEXT_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[a-z0-9._\-]+"),
    re.compile(r"(?i)(password\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(client_secret\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s,;]+"),
)


def redact_text(text: str | None) -> str:
    if not text:
        return ""

    redacted = str(text)
    for pattern in _TEXT_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted


def validate_local_http_url(url: str, allowed_hosts: tuple[str, ...]) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL deve usar http ou https")

    host = parsed.hostname
    if not host:
        raise ValueError("URL sem host")

    normalized_allowed = {item.lower() for item in allowed_hosts}
    if host.lower() not in normalized_allowed:
        raise ValueError(f"Host nao permitido para MCP local: {host}")

    return url


def clamp_int(value: int, *, minimum: int, maximum: int) -> int:
    return max(minimum, min(int(value), maximum))
