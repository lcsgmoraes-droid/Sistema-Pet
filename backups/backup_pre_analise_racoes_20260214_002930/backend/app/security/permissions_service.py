from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.tenancy.context import get_current_tenant
from app.auth import get_current_user
from app.models import UserTenant, RolePermission, Permission, User


def get_user_permissions(db: Session, user_id: int, tenant_id: UUID) -> set[str]:
    perms = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserTenant, UserTenant.role_id == RolePermission.role_id)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
            UserTenant.is_active == True,
            RolePermission.tenant_id == tenant_id,
        )
        .all()
    )
    return {p[0] for p in perms}


def check_permission(db: Session, user_id: int, permission: str, tenant_id: Optional[UUID] = None):
    """
    Verifica se o usuário tem a permissão especificada.
    
    Args:
        db: Sessão do banco de dados
        user_id: ID do usuário
        permission: Código da permissão (ex: "produtos.visualizar")
        tenant_id: UUID do tenant (opcional, usa contexto se não fornecido)
    """
    # Verifica se o usuário é admin - admins têm todas as permissões
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.is_admin:
        return  # Admin tem acesso total, não precisa verificar permissões
    
    # Se tenant_id não foi passado, tenta pegar do contexto
    if tenant_id is None:
        tenant_id = get_current_tenant()
    
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant não definido")

    perms = get_user_permissions(db, user_id, tenant_id)
    if permission not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permissão negada: {permission}",
        )

