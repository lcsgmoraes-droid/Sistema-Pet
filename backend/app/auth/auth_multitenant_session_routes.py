"""Endpoints de tokens, tenant ativo e sessoes multi-tenant."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.auth.auth_multitenant_schemas import (
    RefreshTokenRequest,
    RefreshTokenResponse,
    SelectTenantRequest,
    SelectTenantResponse,
)
from app.auth.auth_multitenant_support import (
    _auth_payload,
    _create_token_pair,
    _session_expiry_utc,
    _validate_refresh_tenant,
)
from app.auth.core import ALGORITHM
from app.auth.dependencies import get_current_user_and_tenant
from app.auth.permission_dependencies import expand_permissions
from app.config import JWT_SECRET_KEY as SECRET_KEY
from app.db import get_session
from app.models import Permission, Role, RolePermission, Tenant, User, UserTenant
from app.security.jwt_compat import JWTError, jwt
from app.services.auth_security import register_logout
from app.session_manager import (
    get_active_sessions,
    get_session_by_jti,
    revoke_session,
    validate_session,
)
from app.tenancy.rls import sync_rls_auth_user


security = HTTPBearer()
router = APIRouter()


@router.post("/refresh", response_model=RefreshTokenResponse)
def refresh_access_token(
    payload: RefreshTokenRequest, db: Session = Depends(get_session)
):
    """
    Renova o access token curto usando um refresh token atrelado a sessao ativa.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token invalido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_payload = jwt.decode(
            payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM]
        )
    except JWTError:
        raise credentials_exception

    if token_payload.get("typ") != "refresh":
        raise credentials_exception

    user_id = token_payload.get("sub")
    token_jti = token_payload.get("jti")
    tenant_id = token_payload.get("tenant_id")

    if not user_id or not token_jti:
        raise credentials_exception

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise credentials_exception

    if not validate_session(db, token_jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db_session = get_session_by_jti(db, token_jti)
    if not db_session or db_session.user_id != user_id_int:
        raise credentials_exception

    sync_rls_auth_user(db, user_id_int)
    user = db.query(User).filter(User.id == user_id_int).first()
    if not user or not user.is_active:
        raise credentials_exception

    tenant_uuid = _validate_refresh_tenant(db, user_id_int, tenant_id)
    if (
        tenant_uuid
        and db_session.tenant_id
        and str(db_session.tenant_id) != str(tenant_uuid)
    ):
        raise credentials_exception

    access_token, refresh_token = _create_token_pair(
        user_id_int,
        token_jti,
        _session_expiry_utc(db_session),
        str(tenant_uuid) if tenant_uuid else None,
    )

    return RefreshTokenResponse(**_auth_payload(access_token, refresh_token))


@router.post("/select-tenant", response_model=SelectTenantResponse)
def select_tenant(
    request: Request,
    body: SelectTenantRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Fase 2: Seleciona tenant e gera token COM tenant_id.
    REUTILIZA a sessao criada no login.
    """
    sync_rls_auth_user(db, current_user.id)

    try:
        tenant_uuid = UUID(body.tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id invalido"
        )

    user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == current_user.id,
            UserTenant.tenant_id == tenant_uuid,
            UserTenant.is_active.is_(True),
        )
        .first()
    )

    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voce nao tem acesso a este tenant",
        )

    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_uuid)).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant nao encontrado"
        )

    tenant_status = str(tenant.status or "").strip().lower()
    if tenant_status not in {"active", "ativo"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant inativo ou indisponivel",
        )

    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    token_jti = payload.get("jti")

    if not token_jti:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalido - JTI nao encontrado",
        )

    db_session = get_session_by_jti(db, token_jti)

    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao nao encontrada. Faca login novamente.",
        )

    if db_session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao invalida. Faca login novamente.",
        )

    db_session.tenant_id = tenant_uuid
    db.commit()

    access_token, refresh_token = _create_token_pair(
        current_user.id,
        token_jti,
        _session_expiry_utc(db_session),
        str(tenant_uuid),
    )

    return SelectTenantResponse(
        **_auth_payload(access_token, refresh_token),
        tenant={
            "id": str(tenant.id),
            "name": tenant.name,
            "role_id": user_tenant.role_id,
        },
    )


@router.get("/me-multitenant")
def get_me_multitenant(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna dados do usuario no contexto multi-tenant.

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
            UserTenant.is_active.is_(True),
        )
        .first()
    )

    if not user_tenant_info:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario nao tem acesso ao tenant selecionado",
        )

    _user_tenant, role = user_tenant_info
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()

    permissions = []
    if role:
        permissions = [
            codigo
            for (codigo,) in (
                db.query(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .filter(
                    RolePermission.role_id == role.id,
                    RolePermission.tenant_id == tenant_id,
                )
                .all()
            )
        ]

    permissions = expand_permissions(permissions)

    return {
        "id": current_user.id,
        "name": current_user.nome,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "email_verified": current_user.email_verified,
        "consent_version": current_user.consent_version,
        "privacy_version": current_user.privacy_version,
        "tenant": {"id": str(tenant.id), "name": tenant.name} if tenant else None,
        "role": {"id": role.id, "name": role.name} if role else None,
        "permissions": permissions,
    }


@router.post("/logout-multitenant")
def logout_multitenant(
    request: Request,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Revoga todas as sessoes do usuario.
    """
    sessions = get_active_sessions(db, current_user.id)

    for session in sessions:
        revoke_session(db, session.id, current_user.id, "user_logout")

    register_logout(db, current_user, request, len(sessions))
    db.commit()

    return {"message": "Logout realizado com sucesso"}
