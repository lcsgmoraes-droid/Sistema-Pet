import os

import pytest


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ENVIRONMENT", "test")

from app.security.tenant_config_crypto import (
    SECRET_PREFIX,
    SecretDecryptionError,
    decrypt_secret,
    decrypt_secret_strict,
    encrypt_secret,
    is_encrypted_secret,
)


def test_encrypt_secret_roundtrip_does_not_keep_plaintext(monkeypatch):
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "unit-test-master-key")
    plaintext = "credencial-super-secreta"

    encrypted = encrypt_secret(plaintext)

    assert encrypted is not None
    assert encrypted.startswith(SECRET_PREFIX)
    assert plaintext not in encrypted
    assert is_encrypted_secret(encrypted) is True
    assert decrypt_secret(encrypted) == plaintext
    assert encrypt_secret(encrypted) == encrypted


def test_decryption_fails_closed_when_master_key_is_wrong(monkeypatch):
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "master-key-a")
    encrypted = encrypt_secret("segredo")
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "master-key-b")

    assert decrypt_secret(encrypted) == ""
    with pytest.raises(SecretDecryptionError):
        decrypt_secret_strict(encrypted)


def test_production_requires_an_explicit_master_key(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("PAYMENT_CONFIG_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="obrigatorio em producao"):
        encrypt_secret("segredo")


@pytest.mark.parametrize(
    ("public_name", "encrypted_name", "legacy_name"),
    (
        ("api_key", "_api_key_encrypted", "_api_key_legacy"),
        (
            "webhook_secret",
            "_webhook_secret_encrypted",
            "_webhook_secret_legacy",
        ),
        (
            "openai_api_key",
            "_openai_api_key_encrypted",
            "_openai_api_key_legacy",
        ),
    ),
)
def test_whatsapp_model_encrypts_writes_and_reads_transparently(
    monkeypatch,
    public_name,
    encrypted_name,
    legacy_name,
):
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "whatsapp-model-test-key")

    import app.models  # noqa: F401 - registra relacionamentos SQLAlchemy
    import app.whatsapp.models_handoff  # noqa: F401 - registra relacionamentos
    from app.whatsapp.models import TenantWhatsAppConfig

    config = TenantWhatsAppConfig()
    setattr(config, legacy_name, "valor-legado")

    assert getattr(config, public_name) == "valor-legado"

    setattr(config, public_name, "novo-segredo")
    encrypted = getattr(config, encrypted_name)

    assert encrypted.startswith(SECRET_PREFIX)
    assert "novo-segredo" not in encrypted
    assert getattr(config, legacy_name) is None
    assert getattr(config, public_name) == "novo-segredo"


def test_empty_whatsapp_secret_clears_encrypted_and_legacy_values(monkeypatch):
    monkeypatch.setenv("PAYMENT_CONFIG_ENCRYPTION_KEY", "whatsapp-clear-test-key")

    import app.models  # noqa: F401 - registra relacionamentos SQLAlchemy
    import app.whatsapp.models_handoff  # noqa: F401 - registra relacionamentos
    from app.whatsapp.models import TenantWhatsAppConfig

    config = TenantWhatsAppConfig()
    config._api_key_legacy = "valor-legado"
    config.api_key = "   "

    assert config._api_key_encrypted is None
    assert config._api_key_legacy is None
    assert config.api_key == ""
