from datetime import datetime, timedelta, timezone
from uuid import UUID
import hashlib
import os
import secrets
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.models import Cliente, Role, Tenant, User, UserTenant
from app.services.email_service import send_email
from app.session_manager import revoke_all_sessions
from app.services.auth_security import (
    is_user_locked,
    register_account_created,
    register_failed_login,
    register_password_changed,
    register_password_reset_requested,
    register_successful_login,
    remaining_lock_seconds,
)
from app.tenancy.context import set_current_tenant


router = APIRouter(prefix="/ecommerce/auth", tags=["ecommerce-auth"])
security = HTTPBearer()

RESET_TOKEN_MINUTES = 30
EMAIL_VERIFICATION_TOKEN_HOURS = int(os.getenv("EMAIL_VERIFICATION_TOKEN_HOURS", "24"))
EMAIL_VERIFICATION_REQUIRED = os.getenv("EMAIL_VERIFICATION_REQUIRED", "true").strip().lower() not in {"0", "false", "no"}
TERMS_VERSION = os.getenv("TERMS_VERSION", "termos-2026-05-08")
PRIVACY_VERSION = os.getenv("PRIVACY_VERSION", "privacidade-2026-05-08")


class EcommerceRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nome: str | None = None
    telefone: str = Field(min_length=8, max_length=20, description="Telefone obrigatorio")
    accepted_terms: bool = False
    accepted_privacy: bool = False
    terms_version: str | None = None
    privacy_version: str | None = None
    cpf: str = Field(min_length=11, max_length=14, description='CPF obrigatório (11 dígitos, com ou sem formatação)')


class EcommerceLoginRequest(BaseModel):
    email: EmailStr
    password: str


class EcommerceForgotPasswordRequest(BaseModel):
    email: EmailStr
    canal: str | None = None


class EcommerceResetPasswordRequest(BaseModel):
    token: str
    email: EmailStr | None = None
    nova_senha: str = Field(min_length=8)


class EcommerceProfileUpdateRequest(BaseModel):
    nome: str | None = None
    telefone: str | None = None
    cpf: str | None = None
    cep: str | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    estado: str | None = None
    endereco_entrega: str | None = None
    usar_endereco_entrega_diferente: bool | None = None
    entrega_nome: str | None = None
    entrega_cep: str | None = None
    entrega_endereco: str | None = None
    entrega_numero: str | None = None
    entrega_complemento: str | None = None
    entrega_bairro: str | None = None
    entrega_cidade: str | None = None
    entrega_estado: str | None = None


def _normalize_tenant_uuid(raw_tenant_id: str | None) -> UUID | None:
    if not raw_tenant_id:
        return None
    try:
        return UUID(str(raw_tenant_id).strip())
    except Exception:
        return None


def _align_reference_datetime(target_dt: datetime, reference_dt: datetime) -> datetime:
    """
    Alinha o datetime de referência ao mesmo padrão (com/sem tz) do alvo.
    Evita TypeError quando o banco retorna datetime sem timezone.
    """
    if target_dt.tzinfo is None and reference_dt.tzinfo is not None:
        return reference_dt.replace(tzinfo=None)
    if target_dt.tzinfo is not None and reference_dt.tzinfo is None:
        return reference_dt.replace(tzinfo=timezone.utc)
    return reference_dt


def _is_expired(dt: datetime | None, now_ref: datetime) -> bool:
    if not dt:
        return False
    aligned_now = _align_reference_datetime(dt, now_ref)
    return dt < aligned_now


def _is_expired_or_equal(dt: datetime | None, now_ref: datetime) -> bool:
    if not dt:
        return False
    aligned_now = _align_reference_datetime(dt, now_ref)
    return dt <= aligned_now


def _remaining_days_until(dt: datetime, now_ref: datetime) -> int:
    aligned_now = _align_reference_datetime(dt, now_ref)
    return max(0, (dt - aligned_now).days)


def _cashback_disponivel_clause(cashback_model, now_ref: datetime):
    return or_(
        cashback_model.expires_at.is_(None),
        cashback_model.expires_at > now_ref,
        cashback_model.tx_type != "credit",
    )


def _extract_tenant_id_from_request(request: Request) -> UUID:
    tenant_id = _normalize_tenant_uuid(request.headers.get("X-Tenant-ID"))
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID obrigatório e deve ser UUID válido",
        )
    set_current_tenant(tenant_id)
    return tenant_id


def _activate_user_tenant_context(user: User) -> str:
    tenant_id = _normalize_tenant_uuid(str(getattr(user, "tenant_id", "") or ""))
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    set_current_tenant(tenant_id)
    return str(tenant_id)


def _build_storefront_reset_link(tenant: Tenant | None, user_email: str, reset_token: str) -> str:
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


def _password_reset_token_matches(stored_token: str | None, received_token: str | None) -> bool:
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


def _mark_user_consent(user: User, request: Request, terms_version: str | None, privacy_version: str | None) -> None:
    user.consent_date = _now_utc()
    user.consent_version = terms_version or TERMS_VERSION
    user.privacy_version = privacy_version or PRIVACY_VERSION
    user.consent_ip = request.client.host if request.client else None
    user.consent_user_agent = request.headers.get("user-agent")


def _issue_email_verification_token(user: User) -> str:
    raw_token = _issue_numeric_code()
    user.email_verification_token_hash = _hash_token(raw_token)
    user.email_verification_token_expires = _now_utc() + timedelta(hours=EMAIL_VERIFICATION_TOKEN_HOURS)
    user.email_verification_sent_at = _now_utc()
    return raw_token


def _build_email_verification_link(user_email: str, raw_token: str) -> str:
    base_url = (os.getenv("FRONTEND_URL") or os.getenv("ECOMMERCE_BASE_URL") or "https://corepet.com.br").rstrip("/")
    return f"{base_url}/verificar-email?email={quote(user_email)}&token={quote(raw_token)}"


def _send_email_verification(user: User) -> bool:
    raw_token = _issue_email_verification_token(user)
    verification_link = _build_email_verification_link(user.email, raw_token)
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
    return EMAIL_VERIFICATION_REQUIRED and not bool(getattr(user, "email_verified", False))


def _tenant_status_is_active(status_value: object) -> bool:
    return str(status_value or "").strip().lower() in {"active", "ativo"}


def _resolve_password_recovery_channel(request: Request, payload: EcommerceForgotPasswordRequest) -> str:
    canal = (payload.canal or request.headers.get("X-Client-Channel") or "").strip().lower()
    if canal in {"app", "mobile", "site", "web", "loja"}:
        return "app" if canal in {"app", "mobile"} else "site"

    origin = (request.headers.get("origin") or "").lower()
    referer = (request.headers.get("referer") or "").lower()
    if origin or referer:
        return "site"

    user_agent = (request.headers.get("user-agent") or "").lower()
    if "okhttp" in user_agent or "expo" in user_agent or "reactnative" in user_agent:
        return "app"

    return "app"


def _build_reset_password_email_for_app(user: User, reset_token: str) -> tuple[str, str, str]:
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


def _build_reset_password_email_for_site(user: User, reset_token: str, reset_link: str) -> tuple[str, str, str]:
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


def _get_current_ecommerce_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        token_type = payload.get("token_type")
        tenant_id = _normalize_tenant_uuid(payload.get("tenant_id"))
        if token_type != "ecommerce_customer":
            raise credentials_exception
        if not tenant_id:
            raise credentials_exception
    except (JWTError, TypeError, ValueError):
        raise credentials_exception

    set_current_tenant(tenant_id)

    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == tenant_id)
        .first()
    )
    if not user or not user.is_active:
        raise credentials_exception

    user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user.id,
            UserTenant.tenant_id == tenant_id,
            UserTenant.is_active == True,
        )
        .first()
    )
    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario nao tem acesso ativo ao tenant selecionado",
        )

    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not tenant or not _tenant_status_is_active(tenant.status):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant inativo ou indisponivel",
        )

    return user


def _digits_only(value: str | None) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _is_operational_cliente(cliente: Cliente | None) -> bool:
    if not cliente or getattr(cliente, "ativo", True) is False:
        return False
    return bool(
        getattr(cliente, "tipo_cadastro", None) in {"funcionario", "veterinario"}
        or getattr(cliente, "is_entregador", False)
    )


def _identity_matches_cliente(
    cliente: Cliente,
    *,
    email: str,
    cpf_digits: str,
    telefone_digits: str,
) -> bool:
    if cpf_digits and _digits_only(getattr(cliente, "cpf", None)) == cpf_digits:
        return True
    if email and (getattr(cliente, "email", None) or "").strip().lower() == email:
        return True
    if telefone_digits and _digits_only(getattr(cliente, "telefone", None)) == telefone_digits:
        return True
    return False


def _find_operational_cliente_match(
    db: Session,
    *,
    tenant_id: str,
    user: User,
) -> Cliente | None:
    email = (getattr(user, "email", None) or "").strip().lower()
    cpf_digits = _digits_only(getattr(user, "cpf_cnpj", None))
    telefone_digits = _digits_only(getattr(user, "telefone", None))
    if not email and not cpf_digits and not telefone_digits:
        return None

    candidatos = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.ativo == True,
            or_(
                Cliente.tipo_cadastro.in_(["funcionario", "veterinario"]),
                Cliente.is_entregador == True,
            ),
        )
        .order_by(Cliente.id.asc())
        .all()
    )

    for candidato in candidatos:
        if _identity_matches_cliente(
            candidato,
            email=email,
            cpf_digits=cpf_digits,
            telefone_digits=telefone_digits,
        ):
            return candidato

    return None


def _find_cliente_match(
    db: Session,
    *,
    tenant_id: str,
    user_id: int,
    email: str | None = None,
    cpf: str | None = None,
    telefone: str | None = None,
    exclude_cliente_id: int | None = None,
) -> Cliente | None:
    linked_query = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.user_id == user_id,
    )

    base_query = db.query(Cliente).filter(Cliente.tenant_id == tenant_id)

    if exclude_cliente_id is not None:
        base_query = base_query.filter(Cliente.id != exclude_cliente_id)

    cpf_digits = _digits_only(cpf)
    if cpf_digits:
        # Busca exata pelo CPF já normalizado (como salvo no banco)
        linked_by_cpf = linked_query.filter(Cliente.cpf == cpf_digits).first()
        if linked_by_cpf:
            return linked_by_cpf

        matched_by_cpf = base_query.filter(Cliente.cpf == cpf_digits).first()
        if matched_by_cpf:
            return matched_by_cpf

        # Fallback: busca normalizada por dígitos (para registros com CPF formatado no banco)
        cpf_candidates = base_query.filter(Cliente.cpf.isnot(None)).all()
        for candidate in cpf_candidates:
            if _digits_only(candidate.cpf) == cpf_digits:
                return candidate

    email = (email or "").strip().lower()
    if email:
        linked_by_email = linked_query.filter(Cliente.email == email).first()
        if linked_by_email:
            return linked_by_email

        matched_by_email = base_query.filter(Cliente.email == email).first()
        if matched_by_email:
            return matched_by_email

    telefone_digits = _digits_only(telefone)
    if telefone_digits:
        linked_phone_candidates = linked_query.filter(Cliente.telefone.isnot(None)).all()
        for candidate in linked_phone_candidates:
            if _digits_only(candidate.telefone) == telefone_digits:
                return candidate

        phone_candidates = base_query.filter(Cliente.telefone.isnot(None)).all()
        for candidate in phone_candidates:
            if _digits_only(candidate.telefone) == telefone_digits:
                return candidate

    return None


def _extract_ecommerce_delivery_details(cliente: Cliente | None) -> dict:
    default = {
        "usar_endereco_entrega_diferente": False,
        "entrega_nome": "",
        "entrega_cep": "",
        "entrega_endereco": "",
        "entrega_numero": "",
        "entrega_complemento": "",
        "entrega_bairro": "",
        "entrega_cidade": "",
        "entrega_estado": "",
    }
    if not cliente:
        return default

    raw = cliente.enderecos_adicionais
    if isinstance(raw, dict):
        details = raw.get("ecommerce_entrega")
        if isinstance(details, dict):
            return {**default, **details, "usar_endereco_entrega_diferente": True}

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("tipo") == "ecommerce_entrega":
                return {**default, **item, "usar_endereco_entrega_diferente": True}

    return default


def _upsert_delivery_details(cliente: Cliente, details: dict, enabled: bool) -> None:
    current = cliente.enderecos_adicionais
    items = []
    if isinstance(current, list):
        items = [item for item in current if not (isinstance(item, dict) and item.get("tipo") == "ecommerce_entrega")]

    if enabled:
        items.append({"tipo": "ecommerce_entrega", **details})
        cliente.enderecos_adicionais = items
    else:
        cliente.enderecos_adicionais = items if items else None


_CLIENTE_RELATIONSHIPS_TO_TRANSFER = ("pets", "pendencias_estoque", "vendas")


def _transfer_cliente_relations_for_ecommerce_merge(
    previous_cliente: Cliente | None,
    target_cliente: Cliente | None,
) -> int:
    if not previous_cliente or not target_cliente or previous_cliente.id == target_cliente.id:
        return 0

    transferred = 0
    for relationship_name in _CLIENTE_RELATIONSHIPS_TO_TRANSFER:
        related_items = getattr(previous_cliente, relationship_name, None)
        if not related_items:
            continue

        for item in list(related_items):
            if hasattr(item, "cliente_id"):
                item.cliente_id = target_cliente.id
            if hasattr(item, "cliente"):
                item.cliente = target_cliente
            transferred += 1

    return transferred


def _get_or_create_cliente_for_user(db: Session, user: User) -> Cliente:
    tenant_id = _activate_user_tenant_context(user)
    clientes_vinculados = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.user_id == user.id)
        .order_by(Cliente.id.asc())
        .all()
    )

    cliente: Cliente | None = None
    cliente_operacional = _find_operational_cliente_match(db, tenant_id=tenant_id, user=user)
    if cliente_operacional:
        cliente = cliente_operacional

    if clientes_vinculados:
        cpf_usuario = _digits_only(user.cpf_cnpj)
        email_usuario = (user.email or "").strip().lower()

        if not cliente and cpf_usuario:
            cliente = next(
                (
                    c
                    for c in clientes_vinculados
                    if _is_operational_cliente(c) and _digits_only(c.cpf) == cpf_usuario
                ),
                None,
            )

        if not cliente and email_usuario:
            cliente = next(
                (
                    c
                    for c in clientes_vinculados
                    if _is_operational_cliente(c) and (c.email or "").strip().lower() == email_usuario
                ),
                None,
            )

        if not cliente:
            cliente = next((c for c in clientes_vinculados if _is_operational_cliente(c)), None)

        if not cliente and cpf_usuario:
            cliente = next(
                (
                    c
                    for c in clientes_vinculados
                    if _digits_only(c.cpf) == cpf_usuario
                ),
                None,
            )

        if not cliente and email_usuario:
            cliente = next(
                (
                    c
                    for c in clientes_vinculados
                    if (c.email or "").strip().lower() == email_usuario
                ),
                None,
            )

        if not cliente:
            cliente = clientes_vinculados[0]

    if not cliente:
        cliente = (
            db.query(Cliente)
            .filter(Cliente.tenant_id == tenant_id, Cliente.user_id == user.id)
        .first()
        )

    if not cliente:
        cliente = _find_cliente_match(
            db,
            tenant_id=tenant_id,
            user_id=user.id,
            email=user.email,
            cpf=user.cpf_cnpj,
            telefone=user.telefone,
        )

    if not cliente:
        cliente = Cliente(
            tenant_id=tenant_id,
            user_id=user.id,
            nome=user.nome or user.email,
            email=user.email,
            telefone=user.telefone,
            cpf=user.cpf_cnpj,
            tipo_cadastro="cliente",
            tipo_pessoa="PF",
            ativo=True,
        )
        db.add(cliente)
        db.flush()
    else:
        cliente.user_id = user.id
        if not cliente.nome:
            cliente.nome = user.nome or user.email
        if not cliente.email:
            cliente.email = user.email
        if not cliente.telefone and user.telefone:
            cliente.telefone = user.telefone
        if not cliente.cpf and user.cpf_cnpj:
            cliente.cpf = user.cpf_cnpj

    return cliente


def _get_or_create_customer_role(db: Session, tenant_id: str) -> Role:
    role = (
        db.query(Role)
        .filter(Role.tenant_id == tenant_id, Role.name == "Cliente")
        .first()
    )
    if role:
        return role

    role = Role(name="Cliente", tenant_id=tenant_id)
    db.add(role)
    db.flush()
    return role


def _ensure_active_store_access(db: Session, user: User, tenant_id: str) -> UserTenant:
    vinculo = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user.id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )

    if vinculo and vinculo.is_active:
        return vinculo

    role = _get_or_create_customer_role(db, tenant_id)

    if vinculo:
        vinculo.role_id = role.id
        vinculo.is_active = True
        return vinculo

    vinculo = UserTenant(
        user_id=user.id,
        tenant_id=tenant_id,
        role_id=role.id,
        is_active=True,
    )
    db.add(vinculo)
    db.flush()
    return vinculo


def _serialize_profile(user: User, cliente: Cliente | None) -> dict:
    delivery = _extract_ecommerce_delivery_details(cliente)
    is_entregador = bool(getattr(cliente, "is_entregador", False)) if cliente else False
    is_veterinario = bool(
        cliente
        and getattr(cliente, "tipo_cadastro", None) == "veterinario"
        and getattr(cliente, "ativo", True) is not False
    )
    is_funcionario = bool(
        cliente
        and getattr(cliente, "tipo_cadastro", None) == "funcionario"
        and getattr(cliente, "ativo", True) is not False
    )
    if is_veterinario:
        perfil_operacional = "veterinario"
    elif is_entregador:
        perfil_operacional = "entregador"
    elif is_funcionario:
        perfil_operacional = "funcionario"
    else:
        perfil_operacional = "cliente"
    return {
        "id": user.id,
        "email": user.email,
        "email_verified": user.email_verified,
        "nome": user.nome,
        "telefone": (cliente.telefone if cliente else None) or user.telefone,
        "cpf": (cliente.cpf if cliente else None) or user.cpf_cnpj,
        "cep": cliente.cep if cliente else None,
        "endereco": cliente.endereco if cliente else None,
        "numero": cliente.numero if cliente else None,
        "complemento": cliente.complemento if cliente else None,
        "bairro": cliente.bairro if cliente else None,
        "cidade": cliente.cidade if cliente else None,
        "estado": cliente.estado if cliente else None,
        "endereco_entrega": cliente.endereco_entrega if cliente else None,
        "usar_endereco_entrega_diferente": delivery.get("usar_endereco_entrega_diferente", False),
        "endereco_entrega_detalhado": {
            "entrega_nome": delivery.get("entrega_nome", ""),
            "entrega_cep": delivery.get("entrega_cep", ""),
            "entrega_endereco": delivery.get("entrega_endereco", ""),
            "entrega_numero": delivery.get("entrega_numero", ""),
            "entrega_complemento": delivery.get("entrega_complemento", ""),
            "entrega_bairro": delivery.get("entrega_bairro", ""),
            "entrega_cidade": delivery.get("entrega_cidade", ""),
            "entrega_estado": delivery.get("entrega_estado", ""),
        },
        "cliente_id": cliente.id if cliente else None,
        # Perfil entregador — usado pelo app mobile para mostrar interface correta
        "is_entregador": is_entregador,
        "is_funcionario": is_funcionario,
        "funcionario_id": cliente.id if (cliente and (is_entregador or is_funcionario)) else None,
        "is_veterinario": is_veterinario,
        "veterinario_id": cliente.id if (cliente and is_veterinario) else None,
        "perfil_operacional": perfil_operacional,
    }


@router.post("/registrar")
def registrar_cliente(payload: EcommerceRegisterRequest, request: Request, db: Session = Depends(get_session)):
    tenant_id = _extract_tenant_id_from_request(request)
    email = payload.email.strip().lower()

    if not payload.accepted_terms or not payload.accepted_privacy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aceite os Termos de Uso e a Politica de Privacidade para criar a conta.",
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")

    # Normaliza CPF para apenas dígitos antes de salvar e de buscar o Cliente
    cpf_normalizado = re.sub(r"\D+", "", str(payload.cpf or "")).strip() or None
    telefone = (payload.telefone or "").strip()
    if len(_digits_only(telefone)) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone obrigatorio")

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        nome=payload.nome,
        telefone=telefone,
        is_active=True,
        is_admin=False,
        email_verified=not EMAIL_VERIFICATION_REQUIRED,
        email_verified_at=_now_utc() if not EMAIL_VERIFICATION_REQUIRED else None,
        tenant_id=tenant_id,
        cpf_cnpj=cpf_normalizado,  # Salva o CPF antes para que _get_or_create_cliente_for_user possa encontrar o Cliente por CPF
    )
    _mark_user_consent(user, request, payload.terms_version, payload.privacy_version)
    db.add(user)
    if EMAIL_VERIFICATION_REQUIRED:
        enviado = _send_email_verification(user)
        if not enviado:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Nao foi possivel enviar o e-mail de confirmacao agora. Tente novamente em instantes.",
            )
    db.commit()
    db.refresh(user)

    cliente = _get_or_create_cliente_for_user(db, user)
    if payload.nome:
        cliente.nome = payload.nome
    if cpf_normalizado and not cliente.cpf:
        cliente.cpf = cpf_normalizado
    cliente.telefone = telefone
    _ensure_active_store_access(db, user, str(tenant_id))
    register_account_created(db, user, request, "ecommerce")
    db.commit()
    db.refresh(cliente)

    # 🎯 CAMPANHAS — Publicar evento customer_registered na fila
    # Disparado tanto pelo app-mobile quanto pelo ecommerce (mesmo endpoint)
    # Ativa WelcomeHandler (cupom de boas-vindas) se houver campanha ativa
    try:
        from app.campaigns.models import CampaignEventQueue, EventOriginEnum
        evento_campanha = CampaignEventQueue(
            tenant_id=tenant_id,
            event_type="customer_registered",
            event_origin=EventOriginEnum.user_action,
            event_depth=0,
            payload={
                "customer_id": cliente.id,
                "canal": "app",
                "email": user.email,
            },
        )
        db.add(evento_campanha)
        db.commit()
    except Exception as e_camp:
        import logging
        logging.getLogger(__name__).error("[Campanhas] Erro ao publicar customer_registered: %s", e_camp)

    if EMAIL_VERIFICATION_REQUIRED:
        return {
            "access_token": None,
            "token_type": "bearer",
            "requires_email_verification": True,
            "email_verification_sent": True,
            "user": _serialize_profile(user, cliente),
        }

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "token_type": "ecommerce_customer",
        },
        tenant_id=str(tenant_id),
        role="customer",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _serialize_profile(user, cliente),
    }


@router.post("/login")
def login_cliente(payload: EcommerceLoginRequest, request: Request, db: Session = Depends(get_session)):
    tenant_id = _extract_tenant_id_from_request(request)
    email = payload.email.strip().lower()

    user = (
        db.query(User)
        .filter(User.email == email, User.tenant_id == tenant_id)
        .first()
    )

    if user and is_user_locked(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas de login. Aguarde {max(1, remaining_lock_seconds(user) // 60)} minuto(s) e tente novamente.",
            headers={"Retry-After": str(remaining_lock_seconds(user))},
        )

    if not user or not verify_password(payload.password, user.hashed_password or ""):
        if user:
            register_failed_login(db, user, request)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta inativa")

    if _email_verification_block(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email ainda nao confirmado. Verifique sua caixa de entrada ou solicite um novo link.",
        )

    _ensure_active_store_access(db, user, str(tenant_id))
    register_successful_login(db, user, request)
    db.commit()

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "token_type": "ecommerce_customer",
        },
        tenant_id=str(tenant_id),
        role="customer",
    )

    cliente = _get_or_create_cliente_for_user(db, user)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _serialize_profile(user, cliente),
    }


@router.post("/esqueci-senha")
def esqueci_senha(payload: EcommerceForgotPasswordRequest, request: Request, db: Session = Depends(get_session)):
    tenant_id = _extract_tenant_id_from_request(request)
    email = payload.email.strip().lower()
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()

    user = (
        db.query(User)
        .filter(User.email == email, User.tenant_id == tenant_id)
        .first()
    )

    if user and user.is_active:
        reset_code, reset_link_token, stored_reset_token = _issue_password_reset_tokens()
        user.reset_token = stored_reset_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_MINUTES)
        reset_link = _build_storefront_reset_link(tenant, user.email, reset_link_token)
        canal = _resolve_password_recovery_channel(request, payload)
        if canal == "site":
            subject, html_body, text_body = _build_reset_password_email_for_site(user, reset_code, reset_link)
        else:
            subject, html_body, text_body = _build_reset_password_email_for_app(user, reset_code)
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
def resetar_senha(payload: EcommerceResetPasswordRequest, request: Request, db: Session = Depends(get_session)):
    tenant_id = _extract_tenant_id_from_request(request)
    email = (payload.email or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o e-mail para redefinir a senha",
        )

    user = (
        db.query(User)
        .filter(User.email == email, User.tenant_id == tenant_id)
        .first()
    )

    if not user or not user.reset_token_expires:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Codigo ou link de recuperacao invalido")

    if not _password_reset_token_matches(user.reset_token, payload.token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Codigo ou link de recuperacao invalido")

    if _is_expired(user.reset_token_expires, datetime.now(timezone.utc)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Codigo ou link de recuperacao expirado")

    user.hashed_password = hash_password(payload.nova_senha)
    user.reset_token = None
    user.reset_token_expires = None
    _ensure_active_store_access(db, user, str(user.tenant_id))
    register_password_changed(db, user, request, "password_reset")
    revoke_all_sessions(db, user.id, reason="password_reset")
    db.commit()

    return {"message": "Senha atualizada com sucesso"}


@router.get("/me")
def me(current_user: User = Depends(_get_current_ecommerce_user), db: Session = Depends(get_session)):
    tenant_id = _activate_user_tenant_context(current_user)
    cliente = (
        db.query(Cliente)
        .filter(Cliente.tenant_id == tenant_id, Cliente.user_id == current_user.id)
        .first()
    )
    data = _serialize_profile(current_user, cliente)
    data["is_active"] = current_user.is_active
    return data


@router.get("/perfil")
def obter_perfil(current_user: User = Depends(_get_current_ecommerce_user), db: Session = Depends(get_session)):
    cliente = _get_or_create_cliente_for_user(db, current_user)
    db.commit()
    return _serialize_profile(current_user, cliente)


@router.put("/perfil")
def atualizar_perfil(
    payload: EcommerceProfileUpdateRequest,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    cliente = _get_or_create_cliente_for_user(db, current_user)

    nome_informado = (payload.nome or "").strip()
    nome_atual = (current_user.nome or "").strip()
    nome_final = nome_informado or nome_atual
    if not nome_final:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome completo obrigatório")
    if nome_informado and nome_informado != nome_atual and " " not in nome_final:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe nome completo (nome e sobrenome)")

    current_user.nome = nome_final
    cliente.nome = nome_final

    if payload.telefone is not None:
        telefone = payload.telefone.strip()
        if len(_digits_only(telefone)) < 10:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone obrigatorio")
        current_user.telefone = telefone or None
        cliente.telefone = telefone or None
    elif len(_digits_only(current_user.telefone or cliente.telefone)) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone obrigatorio")

    if payload.cpf is not None:
        cpf = payload.cpf.strip()
        current_user.cpf_cnpj = cpf or None
        cliente.cpf = cpf or None

    potential_match = _find_cliente_match(
        db,
        tenant_id=str(current_user.tenant_id),
        user_id=current_user.id,
        email=current_user.email,
        cpf=current_user.cpf_cnpj,
        telefone=current_user.telefone,
        exclude_cliente_id=cliente.id,
    )

    if potential_match and potential_match.id != cliente.id:
        previous_cliente = cliente
        if not potential_match.nome and cliente.nome:
            potential_match.nome = cliente.nome
        if not potential_match.email and cliente.email:
            potential_match.email = cliente.email
        if not potential_match.telefone and cliente.telefone:
            potential_match.telefone = cliente.telefone
        if not potential_match.cpf and cliente.cpf:
            potential_match.cpf = cliente.cpf
        if not potential_match.endereco and cliente.endereco:
            potential_match.endereco = cliente.endereco
        if not potential_match.cep and cliente.cep:
            potential_match.cep = cliente.cep
        if not potential_match.numero and cliente.numero:
            potential_match.numero = cliente.numero
        if not potential_match.complemento and cliente.complemento:
            potential_match.complemento = cliente.complemento
        if not potential_match.bairro and cliente.bairro:
            potential_match.bairro = cliente.bairro
        if not potential_match.cidade and cliente.cidade:
            potential_match.cidade = cliente.cidade
        if not potential_match.estado and cliente.estado:
            potential_match.estado = cliente.estado
        if not potential_match.endereco_entrega and cliente.endereco_entrega:
            potential_match.endereco_entrega = cliente.endereco_entrega

        potential_match.user_id = current_user.id
        _transfer_cliente_relations_for_ecommerce_merge(previous_cliente, potential_match)
        cliente = potential_match
        db.delete(previous_cliente)

    if payload.endereco is not None:
        cliente.endereco = payload.endereco.strip() or None
    if payload.cep is not None:
        cliente.cep = payload.cep.strip() or None
    if payload.numero is not None:
        cliente.numero = payload.numero.strip() or None
    if payload.complemento is not None:
        cliente.complemento = payload.complemento.strip() or None
    if payload.bairro is not None:
        cliente.bairro = payload.bairro.strip() or None
    if payload.cidade is not None:
        cliente.cidade = payload.cidade.strip() or None
    if payload.estado is not None:
        cliente.estado = payload.estado.strip() or None
    if payload.endereco_entrega is not None:
        cliente.endereco_entrega = payload.endereco_entrega.strip() or None

    if payload.usar_endereco_entrega_diferente is not None:
        enabled = bool(payload.usar_endereco_entrega_diferente)

        if enabled:
            entrega_nome = (payload.entrega_nome or "").strip()
            entrega_endereco = (payload.entrega_endereco or "").strip()
            entrega_numero = (payload.entrega_numero or "").strip()
            entrega_bairro = (payload.entrega_bairro or "").strip()
            entrega_cidade = (payload.entrega_cidade or "").strip()
            entrega_estado = (payload.entrega_estado or "").strip()
            entrega_cep = (payload.entrega_cep or "").strip()
            entrega_complemento = (payload.entrega_complemento or "").strip()

            if not entrega_nome:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o nome completo para entrega")
            if not entrega_endereco or not entrega_numero or not entrega_bairro or not entrega_cidade or not entrega_estado:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preencha o endereço de entrega completo")

            address_line = f"{entrega_endereco}, {entrega_numero}"
            tail = " | ".join(
                [
                    f"Bairro: {entrega_bairro}",
                    f"Cidade: {entrega_cidade}/{entrega_estado}",
                    f"CEP: {entrega_cep}" if entrega_cep else "",
                    f"Compl.: {entrega_complemento}" if entrega_complemento else "",
                    f"Destinatário: {entrega_nome}",
                ]
            )
            cliente.endereco_entrega = " | ".join([address_line, *[part for part in tail.split(" | ") if part]])

            _upsert_delivery_details(
                cliente,
                {
                    "entrega_nome": entrega_nome,
                    "entrega_cep": entrega_cep,
                    "entrega_endereco": entrega_endereco,
                    "entrega_numero": entrega_numero,
                    "entrega_complemento": entrega_complemento,
                    "entrega_bairro": entrega_bairro,
                    "entrega_cidade": entrega_cidade,
                    "entrega_estado": entrega_estado,
                },
                True,
            )
        else:
            _upsert_delivery_details(cliente, {}, False)

    db.commit()
    db.refresh(current_user)
    db.refresh(cliente)
    return _serialize_profile(current_user, cliente)


@router.get("/meus-cupons")
def meus_cupons(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna os cupons ativos do cliente autenticado no app.
    """
    from app.campaigns.models import Coupon, CouponStatusEnum

    cliente = _get_or_create_cliente_for_user(db, current_user)

    cupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == current_user.tenant_id,
            Coupon.customer_id == cliente.id,
            Coupon.status == CouponStatusEnum.active,
        )
        .order_by(Coupon.created_at.desc())
        .all()
    )

    now = datetime.now(timezone.utc)
    resultado = []
    for c in cupons:
        expirado = _is_expired(c.valid_until, now)
        resultado.append({
            "id": c.id,
            "code": c.code,
            "coupon_type": c.coupon_type.value,
            "discount_value": float(c.discount_value) if c.discount_value else None,
            "discount_percent": float(c.discount_percent) if c.discount_percent else None,
            "valid_until": c.valid_until.isoformat() if c.valid_until else None,
            "expirado": expirado,
            "min_purchase_value": float(c.min_purchase_value) if c.min_purchase_value else None,
        })

    return resultado


@router.get("/meus-beneficios")
def meus_beneficios(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna em uma única chamada tudo que o app precisa para montar
    a tela 'Meus Benefícios': ranking, carimbos, cashback e cupons ativos.
    """
    from sqlalchemy import func as sqlfunc
    from app.campaigns.models import (
        CashbackTransaction,
        Campaign,
        CampaignTypeEnum,
        Coupon,
        CouponStatusEnum,
        CustomerRankHistory,
    )
    from app.campaigns.loyalty_service import summarize_loyalty_balances_for_customer

    cliente = _get_or_create_cliente_for_user(db, current_user)
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    # --- Cashback ---
    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            _cashback_disponivel_clause(CashbackTransaction, now),
        )
        .scalar()
    )
    saldo_cashback = float(saldo_raw or 0)

    # --- Carimbos ---
    loyalty_summary = summarize_loyalty_balances_for_customer(
        db,
        tenant_id=tenant_id,
        customer_id=cliente.id,
    )
    loyalty_campaign = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.loyalty_stamp,
        )
        .first()
    )
    stamps_to_complete = int((loyalty_campaign.params or {}).get("stamps_to_complete", 10)) if loyalty_campaign else 10
    min_purchase_value = float((loyalty_campaign.params or {}).get("min_purchase_value", 0) or 0) if loyalty_campaign else 0.0
    saldo_total_carimbos = int(loyalty_summary.get("total_carimbos") or 0)
    carimbos_no_cartao = max(saldo_total_carimbos, 0)

    # --- Ranking ---
    rank_atual = (
        db.query(CustomerRankHistory)
        .filter(
            CustomerRankHistory.tenant_id == tenant_id,
            CustomerRankHistory.customer_id == cliente.id,
        )
        .order_by(CustomerRankHistory.period.desc())
        .first()
    )
    rank_level = rank_atual.rank_level.value if rank_atual else "bronze"
    rank_total_spent = float(rank_atual.total_spent) if rank_atual else 0.0
    rank_total_purchases = rank_atual.total_purchases if rank_atual else 0

    ranking_campaign = (
        db.query(Campaign)
        .filter(
            Campaign.tenant_id == tenant_id,
            Campaign.campaign_type == CampaignTypeEnum.ranking_monthly,
        )
        .first()
    )
    rp = ranking_campaign.params if ranking_campaign else {}
    ranking_thresholds = {
        "silver_min_spent": float(rp.get("silver_min_spent", 300)),
        "silver_min_purchases": int(rp.get("silver_min_purchases", 4)),
        "silver_min_months": int(rp.get("silver_min_months", 2)),
        "gold_min_spent": float(rp.get("gold_min_spent", 1000)),
        "gold_min_purchases": int(rp.get("gold_min_purchases", 10)),
        "gold_min_months": int(rp.get("gold_min_months", 4)),
        "diamond_min_spent": float(rp.get("diamond_min_spent", 3000)),
        "diamond_min_purchases": int(rp.get("diamond_min_purchases", 20)),
        "diamond_min_months": int(rp.get("diamond_min_months", 6)),
        "platinum_min_spent": float(rp.get("platinum_min_spent", 8000)),
        "platinum_min_purchases": int(rp.get("platinum_min_purchases", 40)),
        "platinum_min_months": int(rp.get("platinum_min_months", 10)),
    }

    # --- Cupons ativos ---
    cupons = (
        db.query(Coupon)
        .filter(
            Coupon.tenant_id == tenant_id,
            Coupon.customer_id == cliente.id,
            Coupon.status == CouponStatusEnum.active,
        )
        .order_by(Coupon.created_at.desc())
        .all()
    )
    cupons_lista = []
    for c in cupons:
        expirado = _is_expired(c.valid_until, now)
        cupons_lista.append({
            "id": c.id,
            "code": c.code,
            "coupon_type": c.coupon_type.value,
            "discount_value": float(c.discount_value) if c.discount_value else None,
            "discount_percent": float(c.discount_percent) if c.discount_percent else None,
            "valid_until": c.valid_until.isoformat() if c.valid_until else None,
            "expirado": expirado,
            "min_purchase_value": float(c.min_purchase_value) if c.min_purchase_value else None,
        })

    return {
        "cashback": {
            "saldo": saldo_cashback,
        },
        "carimbos": {
            "total_geral": saldo_total_carimbos,
            "carimbos_no_cartao": carimbos_no_cartao,
            "carimbos_ativos_brutos": int(loyalty_summary.get("total_carimbos_brutos") or 0),
            "carimbos_comprometidos_total": int(loyalty_summary.get("carimbos_comprometidos_total") or 0),
            "carimbos_convertidos": int(loyalty_summary.get("carimbos_convertidos") or 0),
            "carimbos_em_debito": int(loyalty_summary.get("carimbos_em_debito") or 0),
            "meta": stamps_to_complete,
            "min_purchase_value": min_purchase_value,
        },
        "ranking": {
            "nivel": rank_level,
            "total_spent": rank_total_spent,
            "total_purchases": rank_total_purchases,
            "thresholds": ranking_thresholds,
        },
        "cupons": cupons_lista,
    }


# ---------------------------------------------------------------------------
# Cashback — extrato (app mobile)
# ---------------------------------------------------------------------------

@router.get("/cashback/extrato")
def meu_extrato_cashback(
    limit: int = 50,
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna o extrato de cashback do cliente autenticado no app.
    """
    from sqlalchemy import func as sqlfunc
    from app.campaigns.models import CashbackTransaction, CashbackSourceTypeEnum

    cliente = _get_or_create_cliente_for_user(db, current_user)
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    txs = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
        )
        .order_by(CashbackTransaction.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )

    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            _cashback_disponivel_clause(CashbackTransaction, now),
        )
        .scalar()
    )
    saldo_atual = float(saldo_raw or 0)

    items = []
    for t in txs:
        is_expired_credit = (
            getattr(t, "tx_type", "credit") == "credit"
            and t.expires_at is not None
            and _is_expired_or_equal(t.expires_at, now)
        )
        items.append({
            "id": t.id,
            "amount": float(t.amount),
            "tx_type": getattr(t, "tx_type", "credit"),
            "source_type": t.source_type.value,
            "description": t.description,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            "expired": is_expired_credit,
        })

    return {"saldo_atual": saldo_atual, "transacoes": items}


# ---------------------------------------------------------------------------
# Cashback — sugestão inteligente de pedido (app mobile)
# ---------------------------------------------------------------------------

@router.get("/cashback/sugestao")
def minha_sugestao_cashback(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    """
    Retorna sugestão de compra baseada no padrão do cliente + saldo de cashback.
    """
    from sqlalchemy import func as sqlfunc
    from app.campaigns.models import CashbackTransaction, CashbackSourceTypeEnum

    cliente = _get_or_create_cliente_for_user(db, current_user)
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    saldo_raw = (
        db.query(sqlfunc.sum(CashbackTransaction.amount))
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            _cashback_disponivel_clause(CashbackTransaction, now),
        )
        .scalar()
    )
    saldo = float(saldo_raw or 0)

    # Ticket médio estimado pelas últimas compras com cashback
    ultimas = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            CashbackTransaction.tx_type == "credit" if hasattr(CashbackTransaction, "tx_type") else True,
            CashbackTransaction.source_type == CashbackSourceTypeEnum.campaign,
        )
        .order_by(CashbackTransaction.created_at.desc())
        .limit(10)
        .all()
    )
    ticket_sugerido = round(
        sum(float(t.amount) for t in ultimas) / len(ultimas) * 50, 2
    ) if ultimas else 100.0

    valor_com_cashback = max(0.0, round(ticket_sugerido - saldo, 2))

    proximo_expirando = (
        db.query(CashbackTransaction)
        .filter(
            CashbackTransaction.tenant_id == tenant_id,
            CashbackTransaction.customer_id == cliente.id,
            CashbackTransaction.tx_type == "credit" if hasattr(CashbackTransaction, "tx_type") else True,
            CashbackTransaction.expires_at.isnot(None),
            CashbackTransaction.expires_at > now,
        )
        .order_by(CashbackTransaction.expires_at.asc())
        .first()
    )

    return {
        "saldo_disponivel": saldo,
        "ticket_sugerido": ticket_sugerido,
        "valor_com_cashback": valor_com_cashback,
        "economia": min(saldo, ticket_sugerido),
        "proximo_expirando": {
            "amount": float(proximo_expirando.amount),
            "expires_at": proximo_expirando.expires_at.isoformat(),
            "dias_restantes": _remaining_days_until(proximo_expirando.expires_at, now),
        } if proximo_expirando else None,
    }

