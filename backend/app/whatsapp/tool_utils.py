"""Utilitarios compartilhados das tools do WhatsApp."""

import unicodedata
from typing import Optional


def _normalize_text(value: Optional[str]) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _only_digits(value: Optional[str]) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


__all__ = ["_normalize_text", "_only_digits"]
