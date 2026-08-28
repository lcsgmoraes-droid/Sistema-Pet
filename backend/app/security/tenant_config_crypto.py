"""Criptografia versionada para segredos de configuracoes por tenant."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

from app.config import JWT_SECRET_KEY


SECRET_PREFIX = "fernet:"


class SecretDecryptionError(ValueError):
    """Indica que um segredo criptografado nao pode ser recuperado."""


def secret_key() -> str:
    """Resolve a chave mestra ja exigida para configuracoes em producao."""
    key = (
        os.getenv("PAYMENT_CONFIG_ENCRYPTION_KEY") or os.getenv("ENCRYPTION_KEY") or ""
    ).strip()
    if key:
        return key

    if (os.getenv("ENVIRONMENT") or "").strip().lower() == "production":
        raise RuntimeError(
            "PAYMENT_CONFIG_ENCRYPTION_KEY (ou ENCRYPTION_KEY) e obrigatorio em "
            "producao para criptografar segredos de configuracao."
        )

    # Conveniencia exclusiva para DEV/teste. Producao sempre falha sem chave.
    return (
        os.getenv("JWT_SECRET_KEY") or JWT_SECRET_KEY or "corepet-dev-only-payment-key"
    ).strip()


def _fernet_key() -> bytes:
    raw_secret = secret_key()
    try:
        Fernet(raw_secret.encode("utf-8"))
        return raw_secret.encode("utf-8")
    except Exception:
        digest = hashlib.sha256(raw_secret.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)


def _cipher() -> Fernet:
    return Fernet(_fernet_key())


def is_encrypted_secret(value: str | None) -> bool:
    return str(value or "").strip().startswith(SECRET_PREFIX)


def encrypt_secret(value: str | None) -> str | None:
    """Criptografa texto claro e preserva valores que ja estao criptografados."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if is_encrypted_secret(raw):
        return raw
    token = _cipher().encrypt(raw.encode("utf-8")).decode("utf-8")
    return SECRET_PREFIX + token


def decrypt_secret_strict(value: str | None) -> str:
    """Descriptografa sem esconder erro de chave, para migrations e rotacao."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    if not is_encrypted_secret(raw):
        return raw

    token = raw[len(SECRET_PREFIX) :]
    try:
        return _cipher().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError) as exc:
        raise SecretDecryptionError(
            "Nao foi possivel descriptografar o segredo de configuracao."
        ) from exc


def decrypt_secret(value: str | None) -> str:
    """Le segredo sem devolver ciphertext quando a chave estiver incorreta."""
    try:
        return decrypt_secret_strict(value)
    except SecretDecryptionError:
        return ""
