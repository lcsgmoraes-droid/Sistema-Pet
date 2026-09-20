from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.tenancy.context import get_current_tenant
from app.auth.permission_dependencies import expand_permissions
from app.grupo_comercial_models import GrupoComercialMembro
from app.models import UserTenant, RolePermission, Permission, User


def _tenant_pertence_ao_grupo(db: Session, tenant_id: UUID, grupo_id: int) -> bool:
    return (
        db.query(GrupoComercialMembro.id)
        .filter(
            GrupoComercialMembro.grupo_id == grupo_id,
            GrupoComercialMembro.empresa_id == str(tenant_id),
            GrupoComercialMembro.status == "ativo",
        )
        .first()
        is not None
    )


def get_user_permissions(db: Session, user_id: int, tenant_id: UUID) -> set[str]:
    perms = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserTenant, UserTenant.role_id == RolePermission.role_id)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
            UserTenant.is_active.is_(True),
            RolePermission.tenant_id == tenant_id,
        )
        .all()
    )
    return set(expand_permissions([p[0] for p in perms]))


def check_permission(
    db: Session,
    user_id: int,
    permission: str,
    tenant_id: Optional[UUID] = None,
    current_user: Optional[User] = None,
):
    """
    Verifica se o usuário tem a permissão especificada.

    Args:
        db: Sessão do banco de dados
        user_id: ID do usuário
        permission: Código da permissão (ex: "produtos.visualizar")
        tenant_id: UUID do tenant (opcional, usa contexto se não fornecido)
    """
    # Administrador de loja e definido por role/permissao no tenant selecionado.
    # O flag global User.is_admin fica reservado para rotas operacionais do sistema.

    # Se tenant_id não foi passado, tenta pegar do contexto
    if tenant_id is None:
        tenant_id = get_current_tenant()

    if tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant não definido")

    # Usuario master do grupo comercial: acesso total e sempre atualizado
    # (inclusive a permissoes novas criadas depois do Role dele existir),
    # mas so dentro das lojas do PROPRIO grupo - nunca um bypass global.
    if current_user is not None and current_user.master_grupo_id is not None:
        if _tenant_pertence_ao_grupo(db, tenant_id, current_user.master_grupo_id):
            return

    perms = set(expand_permissions(list(get_user_permissions(db, user_id, tenant_id))))
    if permission not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permissão negada: {permission}",
        )
