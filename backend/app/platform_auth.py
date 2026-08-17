"""Autenticação exclusiva dos administradores globais da plataforma CorePet."""

from __future__ import annotations

import html
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.auth_multitenant_support import (
    RESET_TOKEN_MINUTES,
    _issue_password_reset_tokens,
    _password_reset_token_matches,
    _resolve_frontend_base_url,
)
from app.auth.core import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.platform_auth_models import PlatformAdmin, PlatformAdminSession
from app.security.client_ip import get_client_ip
from app.security.jwt_compat import JWTError, jwt
from app.services.auth_security import LOGIN_LOCK_MINUTES, MAX_FAILED_LOGIN_ATTEMPTS
from app.services.email_service import send_email


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/platform-auth", tags=["Autenticação da Plataforma"])
security = HTTPBearer()
PLATFORM_SCOPE = "platform_admin"


class PlatformLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class PlatformRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class PlatformForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class PlatformResetPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    token: str = Field(min_length=6, max_length=255)
    nova_senha: str = Field(min_length=8, max_length=128)


@dataclass(frozen=True)
class PlatformAuthContext:
    admin: PlatformAdmin
    session: PlatformAdminSession
    payload: dict


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _credentials_error(detail: str = "Sessão administrativa inválida") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_platform_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise _credentials_error() from exc

    subject = str(payload.get("sub") or "")
    if (
        payload.get("scope") != PLATFORM_SCOPE
        or payload.get("typ") != expected_type
        or not subject.startswith("platform:")
        or not payload.get("jti")
    ):
        raise _credentials_error()

    try:
        payload["platform_admin_id"] = int(subject.split(":", 1)[1])
    except (TypeError, ValueError, IndexError) as exc:
        raise _credentials_error() from exc
    return payload


def _active_session(
    db: Session, payload: dict
) -> tuple[PlatformAdmin, PlatformAdminSession]:
    session = (
        db.query(PlatformAdminSession)
        .filter(PlatformAdminSession.token_jti == str(payload["jti"]))
        .first()
    )
    if (
        session is None
        or session.revoked
        or _aware(session.expires_at) <= _now_utc()
        or session.platform_admin_id != payload["platform_admin_id"]
    ):
        raise _credentials_error("Sessão administrativa expirada ou revogada")

    admin = (
        db.query(PlatformAdmin)
        .filter(PlatformAdmin.id == payload["platform_admin_id"])
        .first()
    )
    if admin is None or not admin.is_active:
        raise _credentials_error("Administrador da plataforma inativo")
    return admin, session


def get_platform_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
) -> PlatformAuthContext:
    payload = _decode_platform_token(credentials.credentials, "access")
    admin, session = _active_session(db, payload)
    return PlatformAuthContext(admin=admin, session=session, payload=payload)


def require_platform_admin(
    context: PlatformAuthContext = Depends(get_platform_auth_context),
) -> PlatformAdmin:
    return context.admin


def _token_pair(admin_id: int, session: PlatformAdminSession) -> tuple[str, str]:
    claims = {
        "sub": f"platform:{admin_id}",
        "scope": PLATFORM_SCOPE,
        "jti": session.token_jti,
    }
    return (
        create_access_token(data=claims),
        create_refresh_token(data=claims, expires_at=_aware(session.expires_at)),
    )


def _admin_payload(admin: PlatformAdmin) -> dict:
    return {
        "id": admin.id,
        "name": admin.name,
        "email": admin.email,
        "scope": PLATFORM_SCOPE,
    }


def _login_payload(admin: PlatformAdmin, session: PlatformAdminSession) -> dict:
    access_token, refresh_token = _token_pair(admin.id, session)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
        "admin": _admin_payload(admin),
    }


def _register_failed_login(admin: PlatformAdmin) -> None:
    attempts = int(admin.failed_login_attempts or 0) + 1
    admin.failed_login_attempts = attempts
    if attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
        admin.locked_until = _now_utc() + timedelta(minutes=LOGIN_LOCK_MINUTES)


def _is_locked(admin: PlatformAdmin) -> bool:
    return bool(admin.locked_until and _aware(admin.locked_until) > _now_utc())


def _build_reset_email(
    admin: PlatformAdmin, reset_code: str, reset_link: str
) -> tuple[str, str, str]:
    name = html.escape(admin.name or "administrador")
    safe_link = html.escape(reset_link, quote=True)
    subject = "Recuperação de acesso - CorePet Ops"
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#0f172a;max-width:620px;margin:0 auto">
      <div style="background:#0f172a;color:#fff;padding:20px 24px;border-radius:12px 12px 0 0">
        <h1 style="margin:0;font-size:22px">CorePet Ops</h1>
      </div>
      <div style="border:1px solid #cbd5e1;border-top:0;padding:24px;border-radius:0 0 12px 12px">
        <p>Olá, {name}.</p>
        <p>Recebemos uma solicitação para redefinir a senha administrativa da plataforma.</p>
        <p><a href="{safe_link}" style="display:inline-block;background:#0f766e;color:#fff;text-decoration:none;padding:12px 18px;border-radius:8px;font-weight:700">Redefinir senha</a></p>
        <p>Ou use este código:</p>
        <div style="font-size:28px;font-weight:800;letter-spacing:6px">{reset_code}</div>
        <p>O link expira em {RESET_TOKEN_MINUTES} minutos. Se não foi você, ignore este e-mail.</p>
      </div>
    </body></html>
    """
    text_body = (
        "Recuperação de acesso - CorePet Ops\n\n"
        f"Acesse: {reset_link}\n"
        f"Código: {reset_code}\n"
        f"Validade: {RESET_TOKEN_MINUTES} minutos."
    )
    return subject, html_body, text_body


@router.post("/login")
def login_platform_admin(
    payload: PlatformLoginRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict:
    email = payload.email.strip().lower()
    admin = db.query(PlatformAdmin).filter(PlatformAdmin.email == email).first()

    if admin and _is_locked(admin):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde alguns minutos e tente novamente.",
        )

    if admin is None or not verify_password(payload.password, admin.hashed_password):
        if admin:
            _register_failed_login(admin)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrador da plataforma inativo",
        )

    admin.failed_login_attempts = 0
    admin.locked_until = None
    admin.last_login_at = _now_utc()
    admin.last_login_ip = get_client_ip(request)
    session = PlatformAdminSession(
        platform_admin_id=admin.id,
        token_jti=str(uuid.uuid4()),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        expires_at=_now_utc() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("platform_admin_login_success admin_id=%s", admin.id)
    return _login_payload(admin, session)


@router.post("/refresh")
def refresh_platform_session(
    payload: PlatformRefreshRequest, db: Session = Depends(get_session)
) -> dict:
    token_payload = _decode_platform_token(payload.refresh_token, "refresh")
    admin, session = _active_session(db, token_payload)
    return _login_payload(admin, session)


@router.get("/me")
def get_platform_admin_me(
    admin: PlatformAdmin = Depends(require_platform_admin),
) -> dict:
    return _admin_payload(admin)


@router.post("/logout")
def logout_platform_admin(
    context: PlatformAuthContext = Depends(get_platform_auth_context),
    db: Session = Depends(get_session),
) -> dict:
    context.session.revoked = True
    context.session.revoked_at = _now_utc()
    context.session.revoke_reason = "logout"
    db.commit()
    return {"message": "Sessão administrativa encerrada"}


@router.post("/forgot-password")
def forgot_platform_password(
    payload: PlatformForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict:
    generic = {
        "message": "Se o e-mail existir, enviaremos instruções de recuperação.",
        "expires_in_minutes": RESET_TOKEN_MINUTES,
    }
    email = payload.email.strip().lower()
    admin = db.query(PlatformAdmin).filter(PlatformAdmin.email == email).first()
    if admin is None or not admin.is_active:
        return generic

    reset_code, link_token, stored_token = _issue_password_reset_tokens()
    admin.reset_token = stored_token
    admin.reset_token_expires = _now_utc() + timedelta(minutes=RESET_TOKEN_MINUTES)
    reset_link = (
        f"{_resolve_frontend_base_url(request)}/ops/recuperar-senha"
        f"?email={quote(admin.email)}&token={quote(link_token)}"
    )
    subject, html_body, text_body = _build_reset_email(admin, reset_code, reset_link)
    if not send_email(
        to=admin.email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        simulate_if_unconfigured=False,
    ):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível enviar o e-mail de recuperação agora.",
        )
    db.commit()
    return generic


@router.post("/reset-password")
def reset_platform_password(
    payload: PlatformResetPasswordRequest,
    db: Session = Depends(get_session),
) -> dict:
    email = payload.email.strip().lower()
    admin = db.query(PlatformAdmin).filter(PlatformAdmin.email == email).first()
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Código ou link de recuperação inválido",
    )
    if admin is None or not admin.reset_token or not admin.reset_token_expires:
        raise invalid
    if not _password_reset_token_matches(admin.reset_token, payload.token):
        raise invalid
    if _aware(admin.reset_token_expires) < _now_utc():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código ou link de recuperação expirado",
        )

    admin.hashed_password = hash_password(payload.nova_senha)
    admin.reset_token = None
    admin.reset_token_expires = None
    admin.failed_login_attempts = 0
    admin.locked_until = None
    admin.password_changed_at = _now_utc()
    sessions = (
        db.query(PlatformAdminSession)
        .filter(
            PlatformAdminSession.platform_admin_id == admin.id,
            PlatformAdminSession.revoked.is_(False),
        )
        .all()
    )
    for session in sessions:
        session.revoked = True
        session.revoked_at = _now_utc()
        session.revoke_reason = "password_reset"
    db.commit()
    return {"message": "Senha administrativa atualizada com sucesso"}
