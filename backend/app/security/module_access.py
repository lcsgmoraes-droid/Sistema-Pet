"""Dependencias de acesso por modulo comercial."""

from datetime import datetime, timezone
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.auth.core import ALGORITHM, get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.config import JWT_SECRET_KEY
from app.db import get_session
from app.models import AssinaturaModulo, Tenant
from app.routes.modulos_routes import MODULOS_PREMIUM, _resolver_modulos_ativos

optional_security = HTTPBearer(auto_error=False)

PUBLIC_BLING_WEBHOOK_PATHS = frozenset(
    {
        "/integracoes/bling/pedido",
        "/integracoes/bling/nf",
    }
)


def _is_ecommerce_customer_token(credentials: HTTPAuthorizationCredentials | None) -> bool:
    if not credentials:
        return False
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return False
    return payload.get("token_type") == "ecommerce_customer"


def _load_active_modules(db: Session, tenant_id: str, agora: datetime | None = None) -> list[str]:
    tenant_id_str = str(tenant_id)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id_str).first()
    if not tenant:
        return []

    assinaturas = (
        db.query(AssinaturaModulo)
        .filter(
            AssinaturaModulo.tenant_id == tenant_id_str,
            AssinaturaModulo.status == "ativo",
        )
        .all()
    )

    return _resolver_modulos_ativos(
        tenant.modulos_ativos,
        assinaturas,
        agora or datetime.now(tz=timezone.utc),
        tenant.plan,
    )


def _is_public_bling_webhook(modulo: str, request: Request | None) -> bool:
    if modulo != "bling" or request is None:
        return False

    path = str(request.url.path or "").rstrip("/") or "/"
    return request.method.upper() == "POST" and path in PUBLIC_BLING_WEBHOOK_PATHS


def require_active_module(modulo: str, *, allow_ecommerce_customer: bool = False) -> Callable:
    """Bloqueia rotas de modulo premium quando o tenant nao tem acesso."""
    if modulo not in MODULOS_PREMIUM:
        raise ValueError(f"Modulo comercial desconhecido: {modulo}")

    async def dependency(
        request: Request = None,
        credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
        db: Session = Depends(get_session),
    ) -> None:
        if allow_ecommerce_customer and _is_ecommerce_customer_token(credentials):
            return

        if not credentials:
            if _is_public_bling_webhook(modulo, request):
                return
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated")

        current_user = get_current_user(credentials=credentials, session=db)
        current_user, tenant_id = await get_current_user_and_tenant(
            credentials=credentials,
            user=current_user,
            db=db,
        )

        # Administrador da plataforma pode auditar/suportar sem virar cliente do modulo.
        # Admin do tenant nao tem bypass: o plano do tenant continua mandando.
        if getattr(current_user, "is_superadmin", False) or getattr(current_user, "is_system_admin", False):
            return

        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant obrigatorio para acessar este modulo",
            )

        if modulo in _load_active_modules(db, str(tenant_id)):
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "module_not_enabled",
                "modulo": modulo,
                "message": "Modulo nao contratado para este tenant",
            },
        )

    return dependency
