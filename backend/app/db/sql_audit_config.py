"""Configuration helpers for SQL raw-query auditing."""

import os


PROD_LIKE_ENVIRONMENTS = {"production", "prod", "staging"}
VALID_ENFORCEMENT_LEVELS = (
    "HIGH",
    "MEDIUM",
    "LOW",
    "ERROR",
    "WARN",
    "WARNING",
    "STRICT",
)


def current_environment_name() -> str:
    return (
        (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or os.getenv("ENV") or "")
        .strip()
        .lower()
    )


def env_truthy(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"true", "1", "yes", "y", "on"}


def normalize_enforcement_level(raw_value: str | None) -> tuple[str, str]:
    raw_level = (raw_value or "HIGH").strip().upper()
    aliases = {
        "ERROR": "HIGH",
        "WARN": "HIGH",
        "WARNING": "HIGH",
        "STRICT": "MEDIUM",
        "HIGH": "HIGH",
        "MEDIUM": "MEDIUM",
        "LOW": "LOW",
    }
    return aliases.get(raw_level, "HIGH"), raw_level
