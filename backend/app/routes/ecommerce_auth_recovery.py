from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.db import get_session
from app.models import Tenant, User
from app.routes.ecommerce_auth_common import (
    _ensure_active_store_access,
    _extract_tenant_id_from_request,
    _is_expired,
)
from app.routes.ecommerce_auth_schemas import (
    EcommerceForgotPasswordRequest,
    EcommerceResetPasswordRequest,
)
from app.routes.ecommerce_auth_settings import (
    EMAIL_VERIFICATION_REQUIRED,
    EMAIL_VERIFICATION_TOKEN_HOURS,
    PRIVACY_VERSION,
    RESET_TOKEN_MINUTES,
    TERMS_VERSION,
)
from app.services.auth_security import (
    register_password_changed,
    register_password_reset_requested,
)
from app.services.email_service import send_email
from app.services.sales_channel import normalize_online_sales_channel
from app.session_manager import revoke_all_sessions


router = APIRouter()


def _build_storefront_reset_link(
    tenant: Tenant | None, user_email: str, reset_token: str
) -> str:
    base_url = (os.getenv("ECOMMERCE_BASE_URL") or "https://corepet.com.br").rstrip("/")
    store_ref = None
    if tenant:
        store_ref = tenant.ecommerce_slug or tenant.id

    if store_ref:
        return (
            f"{base_url}/ecommerce?tenant={quote(str(store_ref))}"
            f"&recovery=1&email={quote(user_email)}&token={quote(reset_token)}"
        )

    return (
        f"{base_url}/ecommerce"
        f"?recovery=1&email={quote(user_email)}&token={quote(reset_token)}"
    )


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


def _build_email_verification_link(
    user_email: str, raw_token: str, canal: str | None = None
) -> str:
    base_url = (
        os.getenv("FRONTEND_URL")
        or os.getenv("ECOMMERCE_BASE_URL")
        or "https://corepet.com.br"
    ).rstrip("/")
    canal_query = f"&canal={quote(canal)}" if canal else ""
    return f"{base_url}/verificar-email?email={quote(user_email)}&token={quote(raw_token)}{canal_query}"


def _send_email_verification(user: User, canal: str | None = None) -> bool:
    raw_token = _issue_email_verification_token(user)
    verification_link = _build_email_verification_link(user.email, raw_token, canal)
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
          <p>Confirme seu e-mail para ativar sua conta e acessar a loja.</p>
          <p style="margin: 18px 0;">
            <a href="{verification_link}" style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 18px; border-radius: 10px; font-weight: 700;">
              Confirmar e-mail
            </a>
          </p>
          <p>Se preferir, digite este codigo na tela de confirmacao:</p>
          <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 16px; margin: 18px 0;">
            <div style="font-size: 13px; color: #1d4ed8; margin-bottom: 6px;">Codigo de confirmacao</div>
            <div style="font-size: 28px; font-weight: 800; letter-spacing: 6px;">{raw_token}</div>
          </div>
          <p>Esse codigo expira em <strong>{EMAIL_VERIFICATION_TOKEN_HOURS} horas</strong>.</p>
        </div>
      </body>
    </html>
    """
    text_body = (
        "Confirme seu e-mail - CorePet\n\n"
        f"Acesse: {verification_link}\n\n"
        f"Codigo manual: {raw_token}\n"
        f"Validade: {EMAIL_VERIFICATION_TOKEN_HOURS} horas."
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


def _resolve_password_recovery_channel(
    request: Request, payload: EcommerceForgotPasswordRequest
) -> str:
    raw_canal = payload.canal or request.headers.get("X-Client-Channel") or ""
    if str(raw_canal or "").strip():
        canal = normalize_online_sales_channel(raw_canal)
        return "app" if canal == "app" else "site"

    origin = (request.headers.get("origin") or "").lower()
    referer = (request.headers.get("referer") or "").lower()
    if origin or referer:
        return "site"

    user_agent = (request.headers.get("user-agent") or "").lower()
    if "okhttp" in user_agent or "expo" in user_agent or "reactnative" in user_agent:
        return "app"

    return "app"


def _build_reset_password_email_for_app(
    user: User, reset_token: str
) -> tuple[str, str, str]:
    saudacao = f", {user.nome}" if getattr(user, "nome", None) else ""
    subject = "Recuperacao de senha do app - CorePet"
    html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #1f2937; max-width: 620px; margin: 0 auto;">
                <div style="background: #2563eb; color: #ffffff; padding: 20px 24px; border-radius: 12px 12px 0 0;">
                    <h1 style="margin: 0; font-size: 22px;">Recuperar senha no app</h1>
                </div>
                <div style="border: 1px solid #dbeafe; border-top: none; border-radius: 0 0 12px 12px; padding: 24px;">
                    <p>Ola{saudacao}.</p>
                    <p>Recebemos um pedido para redefinir a sua senha no aplicativo.</p>
                    <p>Abra o app, entre na tela <strong>Recuperar senha</strong> e use o codigo abaixo:</p>
                    <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 16px; margin: 18px 0;">
                        <div style="font-size: 13px; color: #1d4ed8; margin-bottom: 6px;">Codigo de recuperacao</div>
                        <div style="font-size: 28px; font-weight: 800; letter-spacing: 6px;">{reset_token}</div>
                    </div>
                    <p>Esse codigo expira em <strong>{RESET_TOKEN_MINUTES} minutos</strong>.</p>
                    <p>Este e-mail e valido apenas para a recuperacao dentro do app.</p>
                    <p>Se voce nao pediu essa alteracao, pode ignorar este e-mail com seguranca.</p>
                </div>
            </body>
        </html>
        """
    text_body = (
        "Recuperacao de senha do app - CorePet\n\n"
        "Abra o app e use este codigo na tela Recuperar senha:\n"
        f"{reset_token}\n\n"
        f"Validade: {RESET_TOKEN_MINUTES} minutos.\n"
        "Se voce nao pediu essa alteracao, ignore este e-mail."
    )
    return subject, html_body, text_body


def _build_reset_password_email_for_site(
    user: User, reset_token: str, reset_link: str
) -> tuple[str, str, str]:
    saudacao = f", {user.nome}" if getattr(user, "nome", None) else ""
    subject = "Recuperacao de senha da loja - CorePet"
    html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #1f2937; max-width: 620px; margin: 0 auto;">
                <div style="background: #2563eb; color: #ffffff; padding: 20px 24px; border-radius: 12px 12px 0 0;">
                    <h1 style="margin: 0; font-size: 22px;">Recuperar senha na loja online</h1>
                </div>
                <div style="border: 1px solid #dbeafe; border-top: none; border-radius: 0 0 12px 12px; padding: 24px;">
                    <p>Ola{saudacao}.</p>
                    <p>Recebemos um pedido para redefinir a sua senha na loja online.</p>
                    <p>Abra a recuperacao direto pela loja:</p>
                    <p style="margin: 18px 0;">
                        <a href="{reset_link}"
                             style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 18px; border-radius: 10px; font-weight: 700;">
                            Recuperar senha agora
                        </a>
                    </p>
                    <p>Se quiser preencher manualmente, use este codigo na tela de recuperacao:</p>
                    <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 16px; margin: 18px 0;">
                        <div style="font-size: 13px; color: #1d4ed8; margin-bottom: 6px;">Codigo de recuperacao</div>
                        <div style="font-size: 28px; font-weight: 800; letter-spacing: 6px;">{reset_token}</div>
                    </div>
                    <p>Se o botao nao abrir, acesse a recuperacao da loja e informe o codigo acima.</p>
                    <p>Esse link expira em <strong>{RESET_TOKEN_MINUTES} minutos</strong>.</p>
                    <p>Este e-mail e valido apenas para a recuperacao pela loja online.</p>
                    <p>Se voce nao pediu essa alteracao, pode ignorar este e-mail com seguranca.</p>
                </div>
            </body>
        </html>
        """
    text_body = (
        "Recuperacao de senha da loja - CorePet\n\n"
        "Clique no botao do e-mail para redefinir sua senha.\n\n"
        "Ou use este codigo na tela de recuperacao da loja online:\n"
        f"{reset_token}\n\n"
        f"Validade: {RESET_TOKEN_MINUTES} minutos.\n"
        "Se voce nao pediu essa alteracao, ignore este e-mail."
    )
    return subject, html_body, text_body


@router.post("/esqueci-senha")
def esqueci_senha(
    payload: EcommerceForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_session),
):
    tenant_id = _extract_tenant_id_from_request(request)
    email = payload.email.strip().lower()
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()

    user = (
        db.query(User).filter(User.email == email, User.tenant_id == tenant_id).first()
    )

    if user and user.is_active:
        reset_code, reset_link_token, stored_reset_token = (
            _issue_password_reset_tokens()
        )
        user.reset_token = stored_reset_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(
            minutes=RESET_TOKEN_MINUTES
        )
        reset_link = _build_storefront_reset_link(tenant, user.email, reset_link_token)
        canal = _resolve_password_recovery_channel(request, payload)
        if canal == "site":
            subject, html_body, text_body = _build_reset_password_email_for_site(
                user, reset_code, reset_link
            )
        else:
            subject, html_body, text_body = _build_reset_password_email_for_app(
                user, reset_code
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
                detail="Não foi possível enviar o e-mail de recuperação agora. Tente novamente em instantes.",
            )
        register_password_reset_requested(db, user, request)
        db.commit()
        return {
            "message": "Se o email existir, enviaremos instruções de recuperação.",
            "expires_in_minutes": RESET_TOKEN_MINUTES,
        }

    return {"message": "Se o email existir, enviaremos instruções de recuperação."}


@router.post("/resetar-senha")
def resetar_senha(
    payload: EcommerceResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_session),
):
    tenant_id = _extract_tenant_id_from_request(request)
    email = (payload.email or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o e-mail para redefinir a senha",
        )

    user = (
        db.query(User).filter(User.email == email, User.tenant_id == tenant_id).first()
    )

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

    if _is_expired(user.reset_token_expires, datetime.now(timezone.utc)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codigo ou link de recuperacao expirado",
        )

    user.hashed_password = hash_password(payload.nova_senha)
    user.reset_token = None
    user.reset_token_expires = None
    _ensure_active_store_access(db, user, str(user.tenant_id))
    register_password_changed(db, user, request, "password_reset")
    revoke_all_sessions(db, user.id, reason="password_reset")
    db.commit()

    return {"message": "Senha atualizada com sucesso"}
