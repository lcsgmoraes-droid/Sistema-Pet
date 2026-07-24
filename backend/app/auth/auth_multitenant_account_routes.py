"""Endpoints de cadastro e login da autenticacao multi-tenant."""

import logging
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password
from app.auth.auth_multitenant_schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
)
from app.auth.auth_multitenant_support import (
    DEFAULT_TRIAL_DAYS,
    _auth_payload,
    _create_token_pair,
    _email_verification_block,
    _email_verification_required_for_request,
    _mark_user_consent,
    _now_utc,
    _send_email_verification,
    _session_expiry_utc,
    grant_all_permissions_to_role,
)
from app.auth.core import ACCESS_TOKEN_EXPIRE_DAYS
from app.db import get_session
from app.models import Role, Tenant, User, UserTenant
from app.services.auth_security import (
    get_request_ip,
    is_user_locked,
    register_account_created,
    register_failed_login,
    register_successful_login,
    remaining_lock_seconds,
)
from app.services.default_roles_service import create_default_roles_for_new_tenant
from app.services.tenant_onboarding_service import onboard_tenant_defaults
from app.services.plan_catalog import resolve_signup_selection
from app.session_manager import create_session
from app.tenancy.context import clear_tenant_context, set_tenant_context
from app.tenancy.rls import sync_rls_auth_email, sync_rls_auth_user


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=LoginResponse)
def register(
    request: Request, payload: RegisterRequest, db: Session = Depends(get_session)
):
    """
    Registra novo usuario e cria tenant automaticamente.

    - **email**: Email unico
    - **password**: Senha (min 8 caracteres)
    - **nome**: Nome do usuario (opcional)
    - **nome_loja**: Nome da loja/empresa (opcional)
    """
    email = payload.email.strip().lower()

    if not payload.accepted_terms or not payload.accepted_privacy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aceite os Termos de Uso e a Politica de Privacidade para criar a conta.",
        )

    sync_rls_auth_email(db, email)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email ja cadastrado"
        )

    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha deve ter no minimo 8 caracteres",
        )

    try:
        selected_plan, organization_type = resolve_signup_selection(
            payload.plan, payload.organization_type
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    email_verification_required = _email_verification_required_for_request(request)

    tenant_name = payload.nome_loja or f"Loja de {payload.nome or email}"
    tenant_id = uuid.uuid4()
    trial_started_at = _now_utc()
    tenant = Tenant(
        id=str(tenant_id),
        name=tenant_name,
        status="active",
        plan=selected_plan.code,
        billing_status="trial",
        trial_started_at=trial_started_at,
        trial_ends_at=trial_started_at + timedelta(days=DEFAULT_TRIAL_DAYS),
        subscription_source="manual",
        organization_type=organization_type,
    )
    db.add(tenant)
    db.flush()

    set_tenant_context(tenant_id)

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        nome=payload.nome,
        nome_loja=payload.nome_loja,
        is_active=True,
        is_admin=False,
        email_verified=not email_verification_required,
        email_verified_at=_now_utc() if not email_verification_required else None,
        tenant_id=tenant_id,
    )
    _mark_user_consent(user, request, payload.terms_version, payload.privacy_version)
    db.add(user)
    db.flush()

    admin_role = Role(
        name="Administrador",
        tenant_id=tenant_id,
    )
    db.add(admin_role)
    db.flush()

    permissions_granted = grant_all_permissions_to_role(
        role_id=admin_role.id, tenant_id=tenant_id, db=db
    )
    db.flush()

    logger.info(
        "Role 'Administrador' criada para tenant %s: %s permissoes vinculadas",
        tenant_id,
        permissions_granted,
    )

    try:
        default_roles_result = create_default_roles_for_new_tenant(db, tenant_id)
        db.flush()
        logger.info(
            "Perfis operacionais padrao criados para tenant %s: %s",
            tenant_id,
            default_roles_result,
        )

        onboarding_result = onboard_tenant_defaults(
            db=db,
            tenant_id=tenant_id,
            user_id=user.id,
            dry_run=False,
            strict_required=True,
        )
        db.flush()
        logger.info(
            "Onboarding inicial do tenant %s concluido: %s",
            tenant_id,
            onboarding_result,
        )
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
        tenant_id=tenant_id,
        role_id=admin_role.id,
        is_active=True,
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

    tenants_payload = [
        {"id": str(tenant_id), "name": tenant.name, "role_id": admin_role.id}
    ]

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

    db_session = create_session(
        db=db,
        user_id=user.id,
        ip_address=get_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        expires_in_days=ACCESS_TOKEN_EXPIRE_DAYS,
    )

    token_jti = db_session.token_jti
    access_token, refresh_token = _create_token_pair(
        user.id,
        token_jti,
        _session_expiry_utc(db_session),
    )

    return LoginResponse(
        **_auth_payload(access_token, refresh_token),
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
def login_multitenant(
    request: Request, credentials: LoginRequest, db: Session = Depends(get_session)
):
    """
    Fase 1: Autentica usuario e retorna lista de tenants disponiveis.
    Token gerado SEM tenant_id.
    """
    email = credentials.email.strip().lower()
    sync_rls_auth_email(db, email)
    user = db.query(User).filter(User.email == email).first()

    if user and is_user_locked(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Muitas tentativas de login. Aguarde {max(1, remaining_lock_seconds(user) // 60)} minuto(s) e tente novamente.",
            headers={"Retry-After": str(remaining_lock_seconds(user))},
        )

    if not user or not verify_password(
        credentials.password, user.hashed_password or ""
    ):
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
            detail="Usuario inativo",
        )

    if _email_verification_block(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email ainda nao confirmado. Verifique sua caixa de entrada ou solicite um novo link.",
        )

    register_successful_login(db, user, request)
    sync_rls_auth_user(db, user.id)

    user_tenants = db.query(UserTenant).filter(UserTenant.user_id == user.id).all()

    if not user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario nao possui acesso a nenhum tenant",
        )

    db_session = create_session(
        db=db,
        user_id=user.id,
        ip_address=get_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        expires_in_days=ACCESS_TOKEN_EXPIRE_DAYS,
    )

    token_jti = db_session.token_jti
    access_token, refresh_token = _create_token_pair(
        user.id,
        token_jti,
        _session_expiry_utc(db_session),
    )

    tenants_list = []
    for ut in user_tenants:
        tenant = db.query(Tenant).filter(Tenant.id == str(ut.tenant_id)).first()
        if tenant:
            tenants_list.append(
                {"id": str(tenant.id), "name": tenant.name, "role_id": ut.role_id}
            )

    return LoginResponse(
        **_auth_payload(access_token, refresh_token),
        user={
            "id": user.id,
            "name": user.nome,
            "email": user.email,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
        },
        tenants=tenants_list,
    )
