from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import unicodedata
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.core import hash_password
from app.models import Role, User, UserTenant
from app.tenancy.rls import sync_rls_auth_email


USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 40
RESERVED_USERNAMES = {
    "admin",
    "administrador",
    "corepet",
    "root",
    "sistema",
    "suporte",
}


@dataclass(slots=True)
class UserAccountError(Exception):
    detail: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.detail


def normalize_email(value: Any) -> str | None:
    normalized = str(value or "").strip().lower()
    return normalized or None


def normalize_username(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    ascii_value = raw.encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9._-]+", ".", ascii_value)
    normalized = re.sub(r"[._-]{2,}", ".", normalized).strip("._-")

    if not (USERNAME_MIN_LENGTH <= len(normalized) <= USERNAME_MAX_LENGTH):
        raise UserAccountError(
            "O nome de usuario deve ter entre 3 e 40 caracteres.",
        )
    if normalized in RESERVED_USERNAMES:
        raise UserAccountError(
            "Este nome de usuario e reservado. Escolha outro.",
            status_code=409,
        )
    return normalized


def validate_password(password: Any) -> str:
    normalized = str(password or "")
    if len(normalized) < 8:
        raise UserAccountError("A senha deve ter no minimo 8 caracteres.")
    if len(normalized.encode("utf-8")) > 72:
        raise UserAccountError("A senha deve ter no maximo 72 caracteres.")
    return normalized


def email_exists_globally(db: Session, email: str | None) -> bool:
    if not email:
        return False
    sync_rls_auth_email(db, email)
    row = db.execute(
        text("SELECT id FROM users WHERE lower(email) = :email LIMIT 1"),
        {"email": email},
    ).first()
    return row is not None


def username_exists_in_tenant(
    db: Session,
    *,
    tenant_id: Any,
    username: str,
    exclude_user_id: int | None = None,
) -> bool:
    query = db.query(User.id).filter(
        User.tenant_id == tenant_id,
        User.username == username,
    )
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.first() is not None


def is_unique_email_violation(exc: IntegrityError) -> bool:
    error_text = str(getattr(exc, "orig", exc)).lower()
    return (
        "users_email" in error_text
        or "users.email" in error_text
        or ("unique" in error_text and "email" in error_text)
    )


def is_unique_username_violation(exc: IntegrityError) -> bool:
    error_text = str(getattr(exc, "orig", exc)).lower()
    return "uq_users_tenant_username" in error_text or (
        "unique" in error_text and "username" in error_text
    )


def get_tenant_role(db: Session, *, tenant_id: Any, role_id: int) -> Role:
    role = (
        db.query(Role).filter(Role.id == role_id, Role.tenant_id == tenant_id).first()
    )
    if not role:
        raise UserAccountError(
            "Perfil de acesso invalido para esta loja. Atualize a pagina e selecione novamente."
        )
    return role


def create_tenant_user_account(
    db: Session,
    *,
    tenant_id: Any,
    username: Any,
    email: Any,
    password: Any,
    role_id: int,
    nome: str | None = None,
) -> tuple[User, Role]:
    normalized_username = normalize_username(username) if username else None
    normalized_email = normalize_email(email)
    normalized_password = validate_password(password)
    role = get_tenant_role(db, tenant_id=tenant_id, role_id=role_id)

    if not normalized_username and not normalized_email:
        raise UserAccountError("Informe um nome de usuario ou um e-mail.")
    if normalized_username and username_exists_in_tenant(
        db,
        tenant_id=tenant_id,
        username=normalized_username,
    ):
        raise UserAccountError(
            "Este nome de usuario ja esta em uso nesta loja.",
            status_code=409,
        )
    if email_exists_globally(db, normalized_email):
        raise UserAccountError(
            "Este e-mail ja esta cadastrado. Use outro e-mail ou deixe o campo vazio.",
            status_code=409,
        )

    now = datetime.now(timezone.utc)
    user = User(
        email=normalized_email,
        username=normalized_username,
        hashed_password=hash_password(normalized_password),
        nome=(str(nome or "").strip() or None),
        is_active=True,
        tenant_id=tenant_id,
        # Contas provisionadas pelo administrador nao dependem de confirmacao
        # por e-mail. Quando nao existe e-mail, o administrador recupera a senha.
        email_verified=True,
        email_verified_at=now if normalized_email else None,
        password_changed_at=now,
    )
    db.add(user)
    db.flush()
    db.add(
        UserTenant(
            user_id=user.id,
            tenant_id=tenant_id,
            role_id=role.id,
            is_active=True,
        )
    )
    db.flush()
    return user, role
