"""Suporte de tokens e e-mails da autenticacao multi-tenant."""

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, create_refresh_token
from app.auth.core import ACCESS_TOKEN_EXPIRE_SECONDS
from app.models import Permission, RolePermission, Tenant, User, UserTenant
from app.services.email_service import send_email


RESET_TOKEN_MINUTES = 30
EMAIL_VERIFICATION_TOKEN_HOURS = int(os.getenv("EMAIL_VERIFICATION_TOKEN_HOURS", "24"))
EMAIL_VERIFICATION_REQUIRED = os.getenv(
    "EMAIL_VERIFICATION_REQUIRED", "true"
).strip().lower() not in {"0", "false", "no"}
TERMS_VERSION = os.getenv("TERMS_VERSION", "termos-2026-05-08")
PRIVACY_VERSION = os.getenv("PRIVACY_VERSION", "privacidade-2026-05-08")
STRICT_EMAIL_ENVS = {"production", "prod", "staging"}
LOCAL_REQUEST_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
ALLOWED_SIGNUP_PLANS = {"basico"}
DEFAULT_TRIAL_DAYS = 30


def _current_environment_name() -> str:
    return (
        (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or os.getenv("ENV") or "")
        .strip()
        .lower()
    )


def _is_local_signup_request(request: Request) -> bool:
    hostname = (request.url.hostname or "").strip().lower()
    if hostname in LOCAL_REQUEST_HOSTS:
        return True

    host_header = (request.headers.get("host") or "").split(":", 1)[0].strip().lower()
    return host_header in LOCAL_REQUEST_HOSTS


def _email_verification_required_for_request(request: Request) -> bool:
    if not EMAIL_VERIFICATION_REQUIRED:
        return False

    if _is_local_signup_request(request):
        return False

    if _current_environment_name() in STRICT_EMAIL_ENVS:
        return True

    return True


def grant_all_permissions_to_role(
    role_id: int, tenant_id: uuid.UUID, db: Session
) -> int:
    all_permissions = db.query(Permission).all()
    existing_permission_ids = set(
        db.query(RolePermission.permission_id)
        .filter(
            RolePermission.role_id == role_id, RolePermission.tenant_id == tenant_id
        )
        .all()
    )
    existing_permission_ids = {pid[0] for pid in existing_permission_ids}

    new_permissions_count = 0
    for permission in all_permissions:
        if permission.id not in existing_permission_ids:
            role_permission = RolePermission(
                role_id=role_id, permission_id=permission.id, tenant_id=tenant_id
            )
            db.add(role_permission)
            new_permissions_count += 1

    return new_permissions_count


def _resolve_frontend_base_url(request: Request) -> str:
    configured_url = (os.getenv("FRONTEND_URL") or "").strip()
    if configured_url:
        return configured_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _issue_numeric_code() -> str:
    return str(secrets.randbelow(900_000) + 100_000)


def _issue_password_reset_tokens() -> tuple[str, str, str]:
    numeric_code = _issue_numeric_code()
    link_token = secrets.token_urlsafe(32)
    stored_token = f"v2:{_hash_token(numeric_code)}:{_hash_token(link_token)}"
    return numeric_code, link_token, stored_token


def _password_reset_token_matches(
    stored_token: str | None, received_token: str | None
) -> bool:
    if not stored_token or not received_token:
        return False

    token = received_token.strip()
    if not token:
        return False

    if stored_token.startswith("v2:"):
        parts = stored_token.split(":", 2)
        if len(parts) != 3:
            return False
        received_hash = _hash_token(token)
        return received_hash in {parts[1], parts[2]}

    if token.isdigit() and len(token) < 6:
        token = token.zfill(6)
    return stored_token == token


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _session_expiry_utc(db_session) -> datetime:
    expires_at = db_session.expires_at
    if expires_at.tzinfo is None:
        return expires_at.replace(tzinfo=timezone.utc)
    return expires_at


def _create_token_pair(
    user_id: int, token_jti: str, expires_at: datetime, tenant_id: str | None = None
) -> tuple[str, str]:
    token_data = {
        "sub": str(user_id),
        "jti": token_jti,
        "tenant_id": str(tenant_id) if tenant_id else None,
    }
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data, expires_at=expires_at)
    return access_token, refresh_token


def _auth_payload(access_token: str, refresh_token: str) -> dict:
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
    }


def _validate_refresh_tenant(db: Session, user_id: int, tenant_id: str | None):
    if not tenant_id:
        return None

    try:
        tenant_uuid = uuid.UUID(str(tenant_id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant invalido no refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_uuid,
            UserTenant.is_active.is_(True),
        )
        .first()
    )

    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_uuid)).first()
    tenant_status = str(getattr(tenant, "status", "") or "").strip().lower()
    if not user_tenant or not tenant or tenant_status not in {"active", "ativo"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant inativo ou indisponivel",
        )

    return tenant_uuid


def _mark_user_consent(
    user: User, request: Request, terms_version: str | None, privacy_version: str | None
) -> None:
    user.consent_date = _now_utc()
    user.consent_version = terms_version or TERMS_VERSION
    user.privacy_version = privacy_version or PRIVACY_VERSION
    user.consent_ip = request.client.host if request.client else None
    user.consent_user_agent = request.headers.get("user-agent")


def _issue_email_verification_token(user: User) -> str:
    raw_token = _issue_numeric_code()
    user.email_verification_token_hash = _hash_token(raw_token)
    user.email_verification_token_expires = _now_utc() + timedelta(
        hours=EMAIL_VERIFICATION_TOKEN_HOURS
    )
    user.email_verification_sent_at = _now_utc()
    return raw_token


def _build_email_verification_email(
    user: User, raw_token: str, verification_link: str
) -> tuple[str, str, str]:
    saudacao = f", {user.nome}" if getattr(user, "nome", None) else ""
    subject = "Confirme seu e-mail - CorePet"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #1f2937; max-width: 620px; margin: 0 auto;">
        <div style="background: #2563eb; color: #ffffff; padding: 20px 24px; border-radius: 12px 12px 0 0;">
          <h1 style="margin: 0; font-size: 22px;">Confirme seu e-mail</h1>
        </div>
        <div style="border: 1px solid #bfdbfe; border-top: none; border-radius: 0 0 12px 12px; padding: 24px;">
          <p>Ola{saudacao}.</p>
          <p>Para ativar sua conta no CorePet, confirme que este e-mail pertence a voce.</p>
          <p style="margin: 18px 0;">
            <a href="{verification_link}"
               style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 18px; border-radius: 10px; font-weight: 700;">
              Confirmar e-mail
            </a>
          </p>
          <p>Se preferir, tambem pode digitar este codigo na tela de confirmacao:</p>
          <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 16px; margin: 18px 0;">
            <div style="font-size: 13px; color: #1d4ed8; margin-bottom: 6px;">Codigo de confirmacao</div>
            <div style="font-size: 28px; font-weight: 800; letter-spacing: 6px;">{raw_token}</div>
          </div>
          <p>Esse codigo expira em <strong>{EMAIL_VERIFICATION_TOKEN_HOURS} horas</strong>.</p>
          <p>Se voce nao criou esta conta, ignore este e-mail.</p>
        </div>
      </body>
    </html>
    """
    text_body = (
        "Confirme seu e-mail - CorePet\n\n"
        "Acesse o link abaixo para ativar sua conta:\n"
        f"{verification_link}\n\n"
        "Ou use este codigo manualmente na tela de confirmacao:\n"
        f"{raw_token}\n\n"
        f"Validade: {EMAIL_VERIFICATION_TOKEN_HOURS} horas.\n"
        "Se voce nao criou esta conta, ignore este e-mail."
    )
    return subject, html_body, text_body


def _send_email_verification(user: User, request: Request) -> bool:
    raw_token = _issue_email_verification_token(user)
    verification_link = (
        f"{_resolve_frontend_base_url(request)}/verificar-email"
        f"?email={quote(user.email)}&token={quote(raw_token)}"
    )
    subject, html_body, text_body = _build_email_verification_email(
        user, raw_token, verification_link
    )
    return send_email(
        to=user.email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        simulate_if_unconfigured=not EMAIL_VERIFICATION_REQUIRED,
    )


def _email_verification_block(user: User) -> bool:
    return EMAIL_VERIFICATION_REQUIRED and not bool(
        getattr(user, "email_verified", False)
    )


def _is_token_expired(expires_at: datetime | None) -> bool:
    if not expires_at:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < _now_utc()


def _build_password_reset_email(
    user: User, reset_token: str, reset_link: str
) -> tuple[str, str, str]:
    saudacao = f", {user.nome}" if getattr(user, "nome", None) else ""
    subject = "Recuperacao de senha - CorePet"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #1f2937; max-width: 620px; margin: 0 auto;">
        <div style="background: #7c3aed; color: #ffffff; padding: 20px 24px; border-radius: 12px 12px 0 0;">
          <h1 style="margin: 0; font-size: 22px;">Recuperar senha</h1>
        </div>
        <div style="border: 1px solid #ddd6fe; border-top: none; border-radius: 0 0 12px 12px; padding: 24px;">
          <p>Ola{saudacao}.</p>
          <p>Recebemos um pedido para redefinir a sua senha no sistema.</p>
          <p>Clique no botao abaixo para abrir a tela de recuperacao ja com os dados preenchidos:</p>
          <p style="margin: 18px 0;">
            <a href="{reset_link}"
               style="display: inline-block; background: #7c3aed; color: #ffffff; text-decoration: none; padding: 12px 18px; border-radius: 10px; font-weight: 700;">
              Redefinir minha senha
            </a>
          </p>
          <p>Se quiser preencher manualmente, use este codigo na tela de recuperacao:</p>
          <div style="background: #f5f3ff; border: 1px solid #ddd6fe; border-radius: 10px; padding: 16px; margin: 18px 0;">
            <div style="font-size: 13px; color: #6d28d9; margin-bottom: 6px;">Codigo de recuperacao</div>
            <div style="font-size: 28px; font-weight: 800; letter-spacing: 6px;">{reset_token}</div>
          </div>
          <p>Se o botao nao abrir, acesse a tela de recuperacao e informe o codigo acima.</p>
          <p>Esse link expira em <strong>{RESET_TOKEN_MINUTES} minutos</strong>.</p>
          <p>Se voce nao pediu essa alteracao, pode ignorar este e-mail com seguranca.</p>
        </div>
      </body>
    </html>
    """
    text_body = (
        "Recuperacao de senha - CorePet\n\n"
        "Clique no botao do e-mail para redefinir sua senha.\n\n"
        "Ou use este codigo na tela de recuperacao:\n"
        f"{reset_token}\n\n"
        f"Validade: {RESET_TOKEN_MINUTES} minutos.\n"
        "Se voce nao pediu essa alteracao, ignore este e-mail."
    )
    return subject, html_body, text_body
