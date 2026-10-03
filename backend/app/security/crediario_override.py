"""Autorizacao individual para liberar vendas bloqueadas por crediario."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.audit_log import log_action
from app.models import User, UserTenant


def obter_vinculo_ativo(db: Session, tenant_id, user_id: int) -> UserTenant | None:
    return (
        db.query(UserTenant)
        .join(User, User.id == UserTenant.user_id)
        .filter(
            UserTenant.tenant_id == tenant_id,
            UserTenant.user_id == user_id,
            UserTenant.is_active.is_(True),
            User.is_active.is_(True),
            User.tenant_id == tenant_id,
        )
        .first()
    )


def definir_liberacao_crediario(
    db: Session,
    *,
    tenant_id,
    user_id: int | None,
    autorizado: bool,
    actor_user_id: int,
) -> bool:
    """Altera o acesso no tenant atual e registra quem o concedeu ou revogou."""
    if user_id is None:
        if autorizado:
            raise HTTPException(
                400, "Vincule uma conta de login antes de autorizar a liberação."
            )
        return False

    vinculo = (
        db.query(UserTenant)
        .join(User, User.id == UserTenant.user_id)
        .filter(
            UserTenant.tenant_id == tenant_id,
            UserTenant.user_id == user_id,
            User.tenant_id == tenant_id,
        )
        .first()
    )
    if vinculo is None:
        raise HTTPException(404, "Usuário não encontrado nesta loja.")

    anterior = bool(vinculo.pode_liberar_venda_crediario_atrasado)
    if anterior == autorizado:
        return False

    vinculo.pode_liberar_venda_crediario_atrasado = autorizado
    log_action(
        db,
        actor_user_id,
        action="user.overdue_credit_override_grant_changed",
        entity_type="users",
        entity_id=user_id,
        tenant_id=tenant_id,
        old_value={"autorizado": anterior},
        new_value={"autorizado": autorizado},
        commit=False,
    )
    return True
