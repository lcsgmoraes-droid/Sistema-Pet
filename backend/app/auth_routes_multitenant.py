"""
Rotas de Autenticação Multi-Tenant
"""
import logging
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User, Tenant, Role, Permission, RolePermission, UserTenant
from app.auth import (
    verify_password, 
    create_access_token, 
    get_current_user,
    hash_password
)
from app.auth.permission_dependencies import expand_permissions
from app.config import JWT_SECRET_KEY as SECRET_KEY
from app.auth.core import ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS
from app.session_manager import create_session, validate_session, revoke_session, revoke_all_sessions, get_active_sessions, get_session_by_jti
from app.auth.dependencies import get_current_user_and_tenant
from app.services.email_service import send_email
from app.services.auth_security import (
    get_request_ip,
    is_user_locked,
    register_account_created,
    register_email_verification_resent,
    register_email_verified,
    register_failed_login,
    register_logout,
    register_password_changed,
    register_password_reset_requested,
    register_successful_login,
    remaining_lock_seconds,
)
from app.services.tenant_onboarding_service import onboard_tenant_defaults
from app.tenancy.context import clear_tenant_context, set_tenant_context
# from app.audit import log_audit  # TODO: Fix audit import conflict

logger = logging.getLogger(__name__)
security = HTTPBearer()
router = APIRouter(prefix="/auth", tags=["auth-multitenant"])
RESET_TOKEN_MINUTES = 30
EMAIL_VERIFICATION_TOKEN_HOURS = int(os.getenv("EMAIL_VERIFICATION_TOKEN_HOURS", "24"))
EMAIL_VERIFICATION_REQUIRED = os.getenv("EMAIL_VERIFICATION_REQUIRED", "true").strip().lower() not in {"0", "false", "no"}
TERMS_VERSION = os.getenv("TERMS_VERSION", "termos-2026-05-08")
PRIVACY_VERSION = os.getenv("PRIVACY_VERSION", "privacidade-2026-05-08")
STRICT_EMAIL_ENVS = {"production", "prod", "staging"}
LOCAL_REQUEST_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
ALLOWED_SIGNUP_PLANS = {"basico"}
DEFAULT_TRIAL_DAYS = 30


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _current_environment_name() -> str:
    return (
        os.getenv("ENVIRONMENT")
        or os.getenv("APP_ENV")
        or os.getenv("ENV")
        or ""
    ).strip().lower()


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

def grant_all_permissions_to_role(role_id: int, tenant_id: uuid.UUID, db: Session) -> int:
    """
    Vincula TODAS as permissões existentes no sistema a uma role.
    
    Esta função garante que:
    - Todas as permissões da tabela Permission sejam vinculadas à role
    - Não haja duplicatas (verifica antes de inserir)
    - Funcione tanto para roles novas quanto para atualizar roles existentes
    
    Args:
        role_id: ID da role que receberá as permissões
        tenant_id: ID do tenant (para RolePermission)
        db: Sessão do banco de dados
    
    Returns:
        Número de permissões vinculadas (novas)
    """
    # Buscar todas as permissões do sistema
    all_permissions = db.query(Permission).all()
    
    # Buscar permissões JÁ vinculadas a esta role
    existing_permission_ids = set(
        db.query(RolePermission.permission_id)
        .filter(
            RolePermission.role_id == role_id,
            RolePermission.tenant_id == tenant_id
        )
        .all()
    )
    existing_permission_ids = {pid[0] for pid in existing_permission_ids}
    
    # Adicionar apenas as que ainda NÃO estão vinculadas
    new_permissions_count = 0
    for permission in all_permissions:
        if permission.id not in existing_permission_ids:
            role_permission = RolePermission(
                role_id=role_id,
                permission_id=permission.id,
                tenant_id=tenant_id
            )
            db.add(role_permission)
            new_permissions_count += 1
    
    return new_permissions_count


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    nome: Optional[str] = None
    nome_loja: Optional[str] = None
    plan: Optional[str] = "basico"
    organization_type: Optional[str] = "petshop"
    accepted_terms: bool = False
    accepted_privacy: bool = False
    terms_version: Optional[str] = None
    privacy_version: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str
    user: dict
    tenants: List[dict]
    requires_email_verification: bool = False
    email_verification_sent: bool = False


class SelectTenantRequest(BaseModel):
    tenant_id: str


class SelectTenantResponse(BaseModel):
    access_token: str
    token_type: str
    tenant: dict


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    email: EmailStr | None = None
    nova_senha: str = Field(min_length=8)


class VerifyEmailRequest(BaseModel):
    token: str
    email: EmailStr | None = None


class ResendVerificationRequest(BaseModel):
    email: EmailStr


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


def _build_email_verification_email(user: User, raw_token: str, verification_link: str) -> tuple[str, str, str]:
    saudacao = f", {user.nome}" if getattr(user, "nome", None) else ""
    subject = "Confirme seu e-mail - Pet Shop Pro"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #1f2937; max-width: 620px; margin: 0 auto;">
        <div style="background: #2563eb; color: #ffffff; padding: 20px 24px; border-radius: 12px 12px 0 0;">
          <h1 style="margin: 0; font-size: 22px;">Confirme seu e-mail</h1>
        </div>
        <div style="border: 1px solid #bfdbfe; border-top: none; border-radius: 0 0 12px 12px; padding: 24px;">
          <p>Ola{saudacao}.</p>
          <p>Para ativar sua conta no Pet Shop Pro, confirme que este e-mail pertence a voce.</p>
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
        "Confirme seu e-mail - Pet Shop Pro\n\n"
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
    subject, html_body, text_body = _build_email_verification_email(user, raw_token, verification_link)
    return send_email(
        to=user.email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        simulate_if_unconfigured=not EMAIL_VERIFICATION_REQUIRED,
    )


def _email_verification_block(user: User) -> bool:
    return EMAIL_VERIFICATION_REQUIRED and not bool(getattr(user, "email_verified", False))


def _is_token_expired(expires_at: datetime | None) -> bool:
    if not expires_at:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < _now_utc()


def _build_password_reset_email(user: User, reset_token: str, reset_link: str) -> tuple[str, str, str]:
    saudacao = f", {user.nome}" if getattr(user, "nome", None) else ""
    subject = "Recuperacao de senha - Pet Shop Pro"
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
        "Recuperacao de senha - Pet Shop Pro\n\n"
        "Clique no botao do e-mail para redefinir sua senha.\n\n"
        "Ou use este codigo na tela de recuperacao:\n"
        f"{reset_token}\n\n"
        f"Validade: {RESET_TOKEN_MINUTES} minutos.\n"
        "Se voce nao pediu essa alteracao, ignore este e-mail."
    )
    return subject, html_body, text_body


@router.post("/register", response_model=LoginResponse)
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_session)):
    """
    Registra novo usuário e cria tenant automaticamente.
    
    - **email**: Email único
    - **password**: Senha (min 8 caracteres)
    - **nome**: Nome do usuário (opcional)
    - **nome_loja**: Nome da loja/empresa (opcional)
    """
    # Verificar se email já existe
    email = payload.email.strip().lower()

    if not payload.accepted_terms or not payload.accepted_privacy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aceite os Termos de Uso e a Politica de Privacidade para criar a conta.",
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ja cadastrado"
        )
    
    # Validar senha
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter no minimo 8 caracteres"
        )

    selected_plan = (payload.plan or "basico").strip().lower()
    if selected_plan not in ALLOWED_SIGNUP_PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plano selecionado indisponivel. Escolha o Plano Basico ou fale com vendas.",
        )

    email_verification_required = _email_verification_required_for_request(request)
    
    # Criar tenant primeiro
    tenant_name = payload.nome_loja or f"Loja de {payload.nome or email}"
    tenant_id = uuid.uuid4()  # Gerar UUID
    trial_started_at = _now_utc()
    tenant = Tenant(
        id=str(tenant_id),
        name=tenant_name,
        status='active',
        plan=selected_plan,
        billing_status='trial',
        trial_started_at=trial_started_at,
        trial_ends_at=trial_started_at + timedelta(days=DEFAULT_TRIAL_DAYS),
        subscription_source='manual',
        organization_type=payload.organization_type or 'petshop'
    )
    db.add(tenant)
    db.flush()  # Para garantir que o tenant existe
    
    # Definir contexto de tenant
    set_tenant_context(tenant_id)
    
    # Criar usuário (definir tenant_id explicitamente)
    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        nome=payload.nome,
        nome_loja=payload.nome_loja,
        is_active=True,
        is_admin=True,  # ✅ SUPER ADMIN - primeiro usuário do tenant
        email_verified=not email_verification_required,
        email_verified_at=_now_utc() if not email_verification_required else None,
        tenant_id=tenant_id  # ✅ Definir tenant_id explicitamente
    )
    _mark_user_consent(user, request, payload.terms_version, payload.privacy_version)
    db.add(user)
    db.flush()  # Para obter user.id
    
    # Criar role de Admin para este tenant
    admin_role = Role(
        name='Administrador',
        tenant_id=tenant_id  # ✅ Definir tenant_id explicitamente
    )
    db.add(admin_role)
    db.flush()
    
    # ✅ VINCULAR TODAS AS PERMISSÕES À ROLE DE ADMINISTRADOR
    # Garante que TODAS as permissões (existentes e futuras) sejam vinculadas
    permissions_granted = grant_all_permissions_to_role(
        role_id=admin_role.id,
        tenant_id=tenant_id,
        db=db
    )
    db.flush()
    
    # Log: quantas permissões foram vinculadas
    logger.info(
        f"Role 'Administrador' criada para tenant {tenant_id}: "
        f"{permissions_granted} permissões vinculadas"
    )
    
    # Vincular usuário ao tenant com role de admin
    try:
        onboarding_result = onboard_tenant_defaults(
            db=db,
            tenant_id=tenant_id,
            user_id=user.id,
            dry_run=False,
            strict_required=True,
        )
        db.flush()
        logger.info("Onboarding inicial do tenant %s concluido: %s", tenant_id, onboarding_result)
    except Exception:
        logger.warning(
            "Nao foi possivel criar os dados padrao de onboarding para o tenant %s",
            tenant_id,
            exc_info=True,
        )
        clear_tenant_context()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nao foi possivel criar os dados padrao da empresa. Tente novamente em instantes.",
        )

    user_tenant = UserTenant(
        user_id=user.id,
        tenant_id=tenant_id,  # ✅ Definir tenant_id explicitamente
        role_id=admin_role.id,
        is_active=True
    )
    db.add(user_tenant)

    email_verification_sent = False
    if email_verification_required:
        email_verification_sent = _send_email_verification(user, request)
        if not email_verification_sent:
            clear_tenant_context()
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Nao foi possivel enviar o e-mail de confirmacao agora. Confira o SMTP e tente novamente.",
            )

    register_account_created(db, user, request, "erp")
    db.commit()
    clear_tenant_context()

    tenants_payload = [{
        "id": str(tenant_id),
        "name": tenant.name,
        "role_id": admin_role.id
    }]

    if email_verification_required:
        return LoginResponse(
            access_token=None,
            token_type="bearer",
            user={
                "id": user.id,
                "name": user.nome,
                "email": user.email,
                "is_active": user.is_active,
                "email_verified": False,
            },
            tenants=tenants_payload,
            requires_email_verification=True,
            email_verification_sent=email_verification_sent,
        )
    
    # Criar sessão
    db_session = create_session(
        db=db,
        user_id=user.id,
        ip_address=get_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        expires_in_days=ACCESS_TOKEN_EXPIRE_DAYS
    )
    
    # Criar token inicial (sem tenant_id - usuário precisa selecionar)
    token_jti = db_session.token_jti
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "jti": token_jti,
            "tenant_id": None
        }
    )
    
    # Retornar dados do usuário e tenant
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "name": user.nome,
            "email": user.email,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
        },
        tenants=tenants_payload,
    )


@router.post("/login-multitenant", response_model=LoginResponse)
def login_multitenant(request: Request, credentials: LoginRequest, db: Session = Depends(get_session)):
    """
    Fase 1: Autentica usuário e retorna lista de tenants disponíveis.
    Token gerado SEM tenant_id.
    """
    email = credentials.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if user and is_user_locked(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas de login. Aguarde {max(1, remaining_lock_seconds(user) // 60)} minuto(s) e tente novamente.",
            headers={"Retry-After": str(remaining_lock_seconds(user))},
        )

    if not user or not verify_password(credentials.password, user.hashed_password or ""):
        if user:
            register_failed_login(db, user, request)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )
    
    if _email_verification_block(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email ainda nao confirmado. Verifique sua caixa de entrada ou solicite um novo link.",
        )

    register_successful_login(db, user, request)

    user_tenants = db.query(UserTenant).filter(
        UserTenant.user_id == user.id
    ).all()
    
    if not user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não possui acesso a nenhum tenant",
        )
    
    # Criar sessão (gera o JTI internamente)
    db_session = create_session(
        db=db,
        user_id=user.id,
        ip_address=get_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        expires_in_days=ACCESS_TOKEN_EXPIRE_DAYS
    )
    
    # Usar o JTI gerado pela sessão
    token_jti = db_session.token_jti
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "jti": token_jti,
            "tenant_id": None
        }
    )
    
    tenants_list = []
    for ut in user_tenants:
        tenant = db.query(Tenant).filter(Tenant.id == str(ut.tenant_id)).first()
        if tenant:
            tenants_list.append({
                "id": str(tenant.id),
                "name": tenant.name,
                "role_id": ut.role_id
            })
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "name": user.nome,
            "email": user.email,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
        },
        tenants=tenants_list
    )


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, request: Request, db: Session = Depends(get_session)):
    email = (payload.email or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o e-mail para confirmar a conta",
        )

    token_hash = _hash_token(payload.token.strip())
    query = db.query(User).filter(
        User.email == email,
        User.email_verification_token_hash == token_hash,
    )
    user = query.first()

    if not user or _is_token_expired(user.email_verification_token_expires):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Codigo de confirmacao invalido ou expirado")

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
    generic_response = {"message": "Se o email precisar de confirmacao, enviaremos um novo link."}
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()

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
    generic_response = {"message": "Se o email existir, enviaremos instrucoes de recuperacao."}
    email = payload.email.strip().lower()

    user = db.query(User).filter(User.email == email).first()

    if not user or not user.is_active:
        return generic_response

    reset_code, reset_link_token, stored_reset_token = _issue_password_reset_tokens()
    user.reset_token = stored_reset_token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_MINUTES)

    reset_link = (
        f"{_resolve_frontend_base_url(request)}/recuperar-senha"
        f"?email={quote(user.email)}&token={quote(reset_link_token)}"
    )
    subject, html_body, text_body = _build_password_reset_email(user, reset_code, reset_link)
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

    user = db.query(User).filter(User.email == email).first()

    if not user or not user.reset_token_expires:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Codigo ou link de recuperacao invalido")

    if not _password_reset_token_matches(user.reset_token, payload.token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Codigo ou link de recuperacao invalido")

    expires_at = user.reset_token_expires
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Codigo ou link de recuperacao expirado")

    user.hashed_password = hash_password(payload.nova_senha)
    user.reset_token = None
    user.reset_token_expires = None
    register_password_changed(db, user, request, "password_reset")
    revoke_all_sessions(db, user.id, reason="password_reset")
    db.commit()

    return {"message": "Senha atualizada com sucesso"}


@router.post("/select-tenant", response_model=SelectTenantResponse)
def select_tenant(
    request: Request,
    body: SelectTenantRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Fase 2: Seleciona tenant e gera token COM tenant_id.
    REUTILIZA a sessão criada no login.
    """
    from uuid import UUID
    
    try:
        tenant_uuid = UUID(body.tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id inválido"
        )
    
    user_tenant = db.query(UserTenant).filter(
        UserTenant.user_id == current_user.id,
        UserTenant.tenant_id == tenant_uuid,
        UserTenant.is_active == True,
    ).first()
    
    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a este tenant"
        )
    
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_uuid)).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant não encontrado"
        )
    
    tenant_status = str(tenant.status or "").strip().lower()
    if tenant_status not in {"active", "ativo"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant inativo ou indisponivel"
        )

    # Extrair JTI do token atual
    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    token_jti = payload.get("jti")
    
    if not token_jti:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido - JTI não encontrado"
        )
    
    # Buscar sessão EXISTENTE
    db_session = get_session_by_jti(db, token_jti)
    
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão não encontrada. Faça login novamente."
        )
    
    # Atualizar tenant_id na sessão EXISTENTE
    if db_session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao invalida. Faca login novamente."
        )

    db_session.tenant_id = tenant_uuid
    db.commit()
    
    # Gerar NOVO token COM tenant_id (MESMO JTI)
    access_token = create_access_token(
        data={
            "sub": str(current_user.id),
            "jti": token_jti,
            "tenant_id": str(tenant_uuid)
        }
    )
    
    # log_audit(
    #     db=db,
    #     user_id=current_user.id,
    #     action="tenant_selected",
    #     entity_type="tenant",
    #     entity_id=str(tenant_uuid),
    #     ip_address=request.client.host if request.client else None,
    #     user_agent=request.headers.get("user-agent"),
    #     tenant_id=tenant_uuid
    # )
    
    return SelectTenantResponse(
        access_token=access_token,
        token_type="bearer",
        tenant={
            "id": str(tenant.id),
            "name": tenant.name,
            "role_id": user_tenant.role_id
        }
    )


@router.get("/me-multitenant")
def get_me_multitenant(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Retorna dados do usuário no contexto multi-tenant.
    
    ORDEM GARANTIDA:
    1. get_current_user valida token + seta tenant no contexto
    2. get_current_user_and_tenant valida tenant no contexto
    3. Endpoint usa current_user + tenant_id
    """
    current_user, tenant_id = user_and_tenant

    user_tenant_info = (
        db.query(UserTenant, Role)
        .outerjoin(Role, Role.id == UserTenant.role_id)
        .filter(
            UserTenant.user_id == current_user.id,
            UserTenant.tenant_id == tenant_id,
            UserTenant.is_active == True,
        )
        .first()
    )

    if not user_tenant_info:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não tem acesso ao tenant selecionado"
        )

    _user_tenant, role = user_tenant_info
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()

    permissions = []
    if role:
        permissions = [
            codigo
            for codigo, in (
                db.query(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .filter(
                    RolePermission.role_id == role.id,
                    RolePermission.tenant_id == tenant_id,
                )
                .all()
            )
        ]
    
    # 🔑 EXPANSÃO AUTOMÁTICA: Adicionar dependências implícitas
    permissions = expand_permissions(permissions)
    
    return {
        "id": current_user.id,
        "name": current_user.nome,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "email_verified": current_user.email_verified,
        "consent_version": current_user.consent_version,
        "privacy_version": current_user.privacy_version,
        "tenant": {
            "id": str(tenant.id),
            "name": tenant.name
        } if tenant else None,
        "role": {
            "id": role.id,
            "name": role.name
        } if role else None,
        "permissions": permissions
    }


@router.post("/logout-multitenant")
def logout_multitenant(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Revoga todas as sessões do usuário.
    """
    sessions = get_active_sessions(db, current_user.id)
    
    for session in sessions:
        revoke_session(db, session.id, current_user.id, "user_logout")

    register_logout(db, current_user, request, len(sessions))
    db.commit()

    return {"message": "Logout realizado com sucesso"}
