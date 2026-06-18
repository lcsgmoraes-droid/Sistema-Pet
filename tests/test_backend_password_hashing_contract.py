from __future__ import annotations


def test_passlib_bcrypt_hash_and_verify_works_with_backend_pin():
    from passlib.context import CryptContext

    password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = password_context.hash("secret123")

    assert password_context.verify("secret123", hashed_password)
