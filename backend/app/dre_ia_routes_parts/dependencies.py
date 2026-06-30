from fastapi import Depends

from app.auth.dependencies import get_current_user_and_tenant
from app.models import User


async def _usuario_dre(
    user_tenant: tuple = Depends(get_current_user_and_tenant),
) -> User:
    """Dependency das rotas de DRE que tocam DREPeriodo (tenant-scoped).

    Reusa a dependency oficial multi-tenant (valida o tenant_id no JWT e estabelece o
    contexto via set_current_tenant) e devolve só o ``User`` — assim o corpo das rotas
    continua usando ``current_user`` como antes, mas agora COM contexto de tenant ativo
    (sem ele, todo SELECT em DREPeriodo daria [ORM FAIL-FAST] após a migração TenantScoped).
    """
    return user_tenant[0]
