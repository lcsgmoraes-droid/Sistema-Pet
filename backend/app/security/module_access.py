"""Dependencias de acesso por modulo comercial."""

from datetime import datetime, timezone
from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import AssinaturaModulo, Tenant, User
from app.routes.modulos_routes import MODULOS_PREMIUM, _resolver_modulos_ativos


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


def require_active_module(modulo: str) -> Callable:
    """Bloqueia rotas de modulo premium quando o tenant nao tem acesso."""
    if modulo not in MODULOS_PREMIUM:
        raise ValueError(f"Modulo comercial desconhecido: {modulo}")

    def dependency(
        user_and_tenant: tuple[User, object] = Depends(get_current_user_and_tenant),
        db: Session = Depends(get_session),
    ) -> None:
        current_user, tenant_id = user_and_tenant
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
