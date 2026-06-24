from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.security.jwt_compat import JWTError, jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.models import Role, Tenant, User, UserTenant
from app.services.app_access_profile_service import normalize_profile_type
from app.tenancy.context import set_current_tenant
from app.tenancy.rls import sync_rls_auth_user


security = HTTPBearer()


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


def _tenant_status_is_active(status_value: object) -> bool:
    return str(status_value or "").strip().lower() in {"active", "ativo"}


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
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM]
        )
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
    sync_rls_auth_user(db, user_id)

    user = (
        db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
    )
    if not user or not user.is_active:
        raise credentials_exception

    user_tenant = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user.id,
            UserTenant.tenant_id == tenant_id,
            UserTenant.is_active.is_(True),
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

    active_profile = normalize_profile_type(payload.get("active_profile"))
    if active_profile:
        setattr(user, "_active_app_profile", active_profile)

    return user


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
