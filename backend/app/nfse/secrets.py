from __future__ import annotations

from app.encryption import decrypt_data, encrypt_data, is_encryption_enabled


SECRET_PREFIX = "fernet:"


class NfseSecretConfigurationError(RuntimeError):
    pass


def encrypt_nfse_secret(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    if not is_encryption_enabled():
        raise NfseSecretConfigurationError(
            "A chave ENCRYPTION_KEY precisa estar configurada para salvar credenciais fiscais."
        )
    return SECRET_PREFIX + encrypt_data(raw)


def decrypt_nfse_secret(value: str | None) -> str:
    stored = (value or "").strip()
    if not stored:
        return ""
    if not stored.startswith(SECRET_PREFIX):
        return ""
    if not is_encryption_enabled():
        raise NfseSecretConfigurationError(
            "A chave ENCRYPTION_KEY precisa estar configurada para ler credenciais fiscais."
        )
    return decrypt_data(stored.removeprefix(SECRET_PREFIX))


def nfse_secret_is_configured(value: str | None) -> bool:
    return bool((value or "").startswith(SECRET_PREFIX))
