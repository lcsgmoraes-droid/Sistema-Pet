"""Endpoints de confirmacao de e-mail e recuperacao de senha."""

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.auth.auth_multitenant_schemas import (
    ForgotPasswordRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.auth.auth_multitenant_support import (
    EMAIL_VERIFICATION_TOKEN_HOURS,
    RESET_TOKEN_MINUTES,
    _build_password_reset_email,
    _hash_token,
    _is_token_expired,
    _issue_password_reset_tokens,
    _now_utc,
    _password_reset_token_matches,
    _resolve_frontend_base_url,
    _send_email_verification,
)
from app.db import get_session
from app.models import User
from app.services.auth_security import (
    register_email_verification_resent,
    register_email_verified,
    register_password_changed,
    register_password_reset_requested,
)
from app.services.email_service import send_email
from app.session_manager import revoke_all_sessions
from app.tenancy.rls import sync_rls_auth_email


router = APIRouter()


@router.post("/verify-email")
def verify_email(
    payload: VerifyEmailRequest, request: Request, db: Session = Depends(get_session)
):
    email = (payload.email or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o e-mail para confirmar a conta",
        )

    sync_rls_auth_email(db, email)
    token_hash = _hash_token(payload.token.strip())
    query = db.query(User).filter(
        User.email == email,
        User.email_verification_token_hash == token_hash,
    )
    user = query.first()

    if not user or _is_token_expired(user.email_verification_token_expires):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codigo de confirmacao invalido ou expirado",
        )

    user.email_verified = True
    user.email_verified_at = _now_utc()
    user.email_verification_token_hash = None
    user.email_verification_token_expires = None
    user.email_verification_sent_at = None
    register_email_verified(db, user, request)
    db.commit()

    return {"message": "Email confirmado com sucesso. Voce ja pode entrar no sistema."}


@router.post("/resend-verification")
def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_session),
):
    generic_response = {
        "message": "Se o email precisar de confirmacao, enviaremos um novo link."
    }
    email = payload.email.strip().lower()
    sync_rls_auth_email(db, email)
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.is_active or user.email_verified:
        return generic_response

    enviado = _send_email_verification(user, request)
    if not enviado:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nao foi possivel enviar o e-mail de confirmacao agora. Tente novamente em instantes.",
        )

    register_email_verification_resent(db, user, request)
    db.commit()
    return {**generic_response, "expires_in_hours": EMAIL_VERIFICATION_TOKEN_HOURS}


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_session),
):
    generic_response = {
        "message": "Se o email existir, enviaremos instrucoes de recuperacao."
    }
    email = payload.email.strip().lower()

    sync_rls_auth_email(db, email)
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.is_active:
        return generic_response

    reset_code, reset_link_token, stored_reset_token = _issue_password_reset_tokens()
    user.reset_token = stored_reset_token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(
        minutes=RESET_TOKEN_MINUTES
    )

    reset_link = (
        f"{_resolve_frontend_base_url(request)}/recuperar-senha"
        f"?email={quote(user.email)}&token={quote(reset_link_token)}"
    )
    subject, html_body, text_body = _build_password_reset_email(
        user, reset_code, reset_link
    )
    enviado = send_email(
        to=user.email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        simulate_if_unconfigured=False,
    )

    if not enviado:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nao foi possivel enviar o e-mail de recuperacao agora. Tente novamente em instantes.",
        )

    register_password_reset_requested(db, user, request)
    db.commit()

    return {
        **generic_response,
        "expires_in_minutes": RESET_TOKEN_MINUTES,
    }


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_session),
):
    email = (payload.email or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o e-mail para redefinir a senha",
        )

    sync_rls_auth_email(db, email)
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.reset_token_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codigo ou link de recuperacao invalido",
        )

    if not _password_reset_token_matches(user.reset_token, payload.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codigo ou link de recuperacao invalido",
        )

    expires_at = user.reset_token_expires
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codigo ou link de recuperacao expirado",
        )

    user.hashed_password = hash_password(payload.nova_senha)
    user.reset_token = None
    user.reset_token_expires = None
    register_password_changed(db, user, request, "password_reset")
    revoke_all_sessions(db, user.id, reason="password_reset")
    db.commit()

    return {"message": "Senha atualizada com sucesso"}
