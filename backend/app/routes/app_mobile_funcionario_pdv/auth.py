"""Autorizacao operacional do PDV mobile."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Cliente, User
from app.routes.ecommerce_auth import _activate_user_tenant_context
from app.services.app_access_profile_service import get_cliente_for_app_profile_or_none


def _get_funcionario_operacional_or_403(db: Session, user: User) -> tuple[Cliente, str]:
    tenant_id = _activate_user_tenant_context(user)
    funcionario = get_cliente_for_app_profile_or_none(db, user, "funcionario")
    if not funcionario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso exclusivo para funcionario operacional.",
        )
    return funcionario, tenant_id
