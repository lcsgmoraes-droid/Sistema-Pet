"""Helpers for consistent tenant identity rules."""

import re
import unicodedata


def normalize_tenant_name(value: str | None) -> str:
    """Normalize store names for case- and accent-insensitive uniqueness."""
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents)
