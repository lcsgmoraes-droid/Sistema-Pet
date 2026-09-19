"""Endpoints de cadastro e login da autenticacao multi-tenant."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import verify_password
from app.auth.auth_multitenant_schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
)
from app.auth.auth_multitenant_support import (
    _auth_payload,
    _create_token_pair,
    _email_verification_block,
    _email_verification_required_for_request,
    _mark_user_consent,
    _send_email_verification,
    _session_expiry_utc,
)
from app.auth.core import ACCESS_TOKEN_EXPIRE_DAYS
from app.db import get_session
from app.grupo_comercial_service import GrupoComercialService
from app.models import Tenant, User, UserTenant
from app.services.auth_security import (
    get_request_ip,
    is_user_locked,
    register_account_created,
    register_failed_login,
    register_successful_login,
    remaining_lock_seconds,
)
from app.services.plan_catalog import resolve_signup_selection
from app.services.tenant_provisioning_service import (
    TenantOnboardingError,
    provision_tenant,
)
from app.services.user_account_service import (
    UserAccountError,
    looks_like_login_phone,
    normalize_login_phone,
)
from app.services.tenant_login_name_service import (
    TenantLoginNameError,
    get_primary_tenant_login_name_value,
    resolve_tenant_id_by_login_name,
)
from app.session_manager import create_session
from app.tenancy.context import clear_tenant_context, set_tenant_context
from app.tenancy.rls import (
    sync_rls_auth_email,
    sync_rls_auth_phone,
    sync_rls_auth_user,
    sync_rls_tenant,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def _tenant_reference_filters(tenant_reference: str):
    """Build a safe tenant lookup for slugs and UUID identifiers."""
    reference = str(tenant_reference or "").strip()
    filters = [func.lower(Tenant.ecommerce_slug) == reference.lower()]

    try:
        uuid.UUID(reference)
    except (TypeError, ValueError, AttributeError):
        return filters

    filters.append(Tenant.id == reference)
    return filters


def _resolve_tenant_reference(db: Session, tenant_reference: str) -> Tenant | None:
    tenant_id = resolve_tenant_id_by_login_name(db, tenant_reference)
    if tenant_id:
        return db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()

    return (
        db.query(Tenant)
        .filter(or_(*_tenant_reference_filters(tenant_reference)))
        .first()
    )


def _tenant_payload(db: Session, tenant: Tenant, role_id: int) -> dict:
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "login_name": get_primary_tenant_login_name_value(
            db, tenant.id, fallback=tenant.name
        ),
        "role_id": role_id,
    }


@router.post("/register", response_model=LoginResponse)
def register(
    request: Request, payload: RegisterRequest, db: Session = Depends(get_session)
):
    """
    Registra novo usuario e cria tenant automaticamente.

    - **email**: Email unico
    - **password**: Senha (min 8 caracteres)
    - **nome**: Nome do usuario (opcional)
    - **nome_loja**: Nome fantasia da loja/empresa (opcional)
    - **nome_acesso**: Nome unico usado no login dos colaboradores (opcional para clientes antigos)
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
    tenant_name = tenant_name.strip()
    tenant_login_name = payload.nome_acesso or tenant_name

    try:
        provisioning = provision_tenant(
            db,
            tenant_name=tenant_name,
            login_name=tenant_login_name,
            plan_code=selected_plan.code,
            organization_type=organization_type,
            new_user_email=email,
            new_user_password=payload.password,
            new_user_nome=payload.nome,
            new_user_email_verified=not email_verification_required,
        )
    except TenantLoginNameError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este nome de acesso ja esta em uso por outra empresa.",
        ) from exc
    except TenantOnboardingError:
        logger.warning(
            "Nao foi possivel criar os dados padrao de onboarding para o novo tenant",
            exc_info=True,
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nao foi possivel criar os dados padrao da empresa. Tente novamente em instantes.",
        )

    tenant_id = provisioning.tenant_id
    tenant = provisioning.tenant
    user = provisioning.user
    admin_role = provisioning.admin_role

    _mark_user_consent(user, request, payload.terms_version, payload.privacy_version)

    # Todo tenant novo nasce dentro de um grupo comercial — grupo-de-1 quando
    # e autocadastro, ver GrupoComercialService.criar_grupo (commit=False:
    # esta rota e quem decide quando commitar a transacao inteira).
    GrupoComercialService(db).criar_grupo(
        empresa_id=str(tenant_id), usuario_id=user.id, nome=tenant_name, commit=False
    )

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
        {
            "id": str(tenant_id),
            "name": tenant.name,
            "login_name": provisioning.login_name,
            "role_id": admin_role.id,
        }
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
    identifier = str(credentials.identifier or "").strip().lower()
    login_por_email = "@" in identifier
    login_por_telefone = looks_like_login_phone(identifier)
    if login_por_email:
        sync_rls_auth_email(db, identifier)
        user = db.query(User).filter(func.lower(User.email) == identifier).first()
    elif login_por_telefone:
        try:
            login_phone = normalize_login_phone(identifier)
        except UserAccountError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Celular ou senha incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        sync_rls_auth_phone(db, login_phone)
        user = db.query(User).filter(User.login_phone == login_phone).first()
    else:
        tenant_reference = str(credentials.tenant or "").strip()
        if not tenant_reference:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Para entrar com nome de usuario, informe a loja.",
            )
        tenant = _resolve_tenant_reference(db, tenant_reference)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Loja, usuario ou senha incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        tenant_id = uuid.UUID(str(tenant.id))
        set_tenant_context(tenant_id)
        sync_rls_tenant(db, tenant_id)
        user = (
            db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.username == identifier,
            )
            .first()
        )

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
            detail="E-mail, celular, usuario ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inativo",
        )

    if user.email and _email_verification_block(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email ainda nao confirmado. Verifique sua caixa de entrada ou solicite um novo link.",
        )

    register_successful_login(db, user, request)
    sync_rls_auth_user(db, user.id)

    user_tenants = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user.id,
            UserTenant.is_active.is_(True),
        )
        .all()
    )

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
            tenants_list.append(_tenant_payload(db, tenant, ut.role_id))

    return LoginResponse(
        **_auth_payload(access_token, refresh_token),
        user={
            "id": user.id,
            "name": user.nome,
            "email": user.email,
            "username": user.username,
            "login_phone": user.login_phone,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
        },
        tenants=tenants_list,
    )
