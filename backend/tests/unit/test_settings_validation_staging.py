from types import SimpleNamespace

import pytest

from app.core.settings_validation import (
    EnvironmentValidationError,
    get_validation_summary,
    validate_settings,
)


def _staging_settings(**overrides):
    values = {
        "ENV": "staging",
        "DATABASE_URL": "postgresql://corepet_homolog:secret@postgres/corepet_homolog",
        "SQL_AUDIT_ENFORCE": True,
        "SQL_AUDIT_ENFORCE_LEVEL": "error",
        "DEBUG": False,
        "ENABLE_GUARDRAILS": True,
        "LOG_LEVEL": "INFO",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_staging_accepts_strict_isolated_configuration(monkeypatch):
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "staging-only-key")

    validate_settings(_staging_settings())


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"DEBUG": True}, "Debug está ATIVADO"),
        (
            {"DATABASE_URL": "postgresql://user:secret@prod/corepet_production"},
            "NÃO DEVE usar banco de produção",
        ),
        ({"SQL_AUDIT_ENFORCE_LEVEL": "warn"}, "SQL Audit level inadequado"),
    ],
)
def test_staging_rejects_unsafe_configuration(monkeypatch, overrides, expected):
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "staging-only-key")

    with pytest.raises(EnvironmentValidationError, match=expected):
        validate_settings(_staging_settings(**overrides))


def test_staging_requires_its_own_payment_encryption_key(monkeypatch):
    monkeypatch.delenv("PAYMENT_CONFIG_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    with pytest.raises(
        EnvironmentValidationError, match="PAYMENT_CONFIG_ENCRYPTION_KEY ausente"
    ):
        validate_settings(_staging_settings())


def test_staging_summary_rejects_debug_but_allows_guardrails():
    valid = get_validation_summary(_staging_settings())
    invalid = get_validation_summary(_staging_settings(DEBUG=True))

    assert valid["is_valid"] is True
    assert invalid["is_valid"] is False
    assert invalid["warnings"] == ["Debug ativado em staging"]
