from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth.core import ALGORITHM, get_current_user_from_token
from app.auth.dependencies import security
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.models import Cliente, Tenant, User, UserTenant
from app.rotas_entrega_models import RotaEntrega
from app.security.jwt_compat import JWTError, jwt
from app.services.app_access_profile_service import get_cliente_for_app_profile_or_none
from app.session_manager import get_session_by_jti
from app.tenancy.context import set_current_tenant


@dataclass
class DeliveryActor:
    user: User
    tenant_id: UUID
    entregador: Cliente | None = None


def _tenant_status_is_active(status_value: object) -> bool:
    return str(status_value or "").strip().lower() in {"active", "ativo"}


def _credentials_exception(
    detail: str = "Could not validate credentials",
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_delivery_token(credentials: HTTPAuthorizationCredentials) -> dict:
    try:
        return jwt.decode(
            credentials.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM]
        )
    except JWTError as exc:
        raise _credentials_exception() from exc


def _has_active_user_tenant(db: Session, user: User, tenant_id: UUID) -> bool:
    return (
        db.query(UserTenant)
        .filter_by(user_id=user.id, tenant_id=tenant_id, is_active=True)
        .first()
        is not None
    )


def _tenant_is_available(db: Session, tenant_id: UUID) -> bool:
    tenant_status = db.query(Tenant.status).filter(Tenant.id == str(tenant_id)).scalar()
    return _tenant_status_is_active(tenant_status)


def _validate_admin_delivery_actor(
    credentials: HTTPAuthorizationCredentials,
    db: Session,
    payload: dict,
) -> DeliveryActor:
    tenant_id_str = payload.get("tenant_id")
    token_jti = payload.get("jti")
    if not tenant_id_str:
        raise _credentials_exception("Tenant nao selecionado. Use /auth/select-tenant.")
    if not token_jti:
        raise _credentials_exception("Sessao invalida. Faca login novamente.")

    try:
        tenant_id = UUID(str(tenant_id_str))
    except (TypeError, ValueError) as exc:
        raise _credentials_exception("Tenant invalido no token") from exc

    set_current_tenant(tenant_id)
    user = get_current_user_from_token(credentials.credentials, db)

    if not _has_active_user_tenant(db, user, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario nao tem acesso ativo ao tenant selecionado",
        )

    if not _tenant_is_available(db, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant inativo ou indisponivel",
        )

    db_session = get_session_by_jti(db, token_jti)
    if not db_session or db_session.user_id != user.id:
        raise _credentials_exception("Sessao invalida. Faca login novamente.")
    if db_session.tenant_id and str(db_session.tenant_id) != str(tenant_id):
        raise _credentials_exception(
            "Sessao pertence a outro tenant. Faca login novamente."
        )
    if db_session.tenant_id is None:
        db_session.tenant_id = tenant_id
        db.flush()

    return DeliveryActor(user=user, tenant_id=tenant_id)


def _validate_ecommerce_entregador_actor(
    credentials: HTTPAuthorizationCredentials,
    db: Session,
) -> DeliveryActor:
    from app.routes.ecommerce_auth import _get_current_ecommerce_user

    user = _get_current_ecommerce_user(credentials=credentials, db=db)
    tenant_id = UUID(str(user.tenant_id))
    set_current_tenant(tenant_id)
    cliente = get_cliente_for_app_profile_or_none(db, user, "entregador")
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a entregadores",
        )
    return DeliveryActor(user=user, tenant_id=tenant_id, entregador=cliente)


def get_delivery_actor_and_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
) -> DeliveryActor:
    payload = _decode_delivery_token(credentials)
    if payload.get("token_type") == "ecommerce_customer":
        return _validate_ecommerce_entregador_actor(credentials, db)
    return _validate_admin_delivery_actor(credentials, db, payload)


def _is_int_like(value: object) -> bool:
    return str(value).strip().isdigit()


def _activate_delivery_actor_tenant(actor: DeliveryActor) -> UUID:
    set_current_tenant(actor.tenant_id)
    return actor.tenant_id


def _rota_filters_for_actor(actor: DeliveryActor, rota_ref):
    tenant_id = _activate_delivery_actor_tenant(actor)
    filters = [RotaEntrega.tenant_id == tenant_id]
    if _is_int_like(rota_ref):
        filters.append(RotaEntrega.id == int(str(rota_ref).strip()))
    else:
        filters.append(RotaEntrega.numero == str(rota_ref).strip())
    if actor.entregador is not None:
        filters.append(RotaEntrega.entregador_id == actor.entregador.id)
    return filters
