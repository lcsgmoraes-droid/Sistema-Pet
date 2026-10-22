"""Rotas do CRM. O modulo "crm" e exigido na montagem do router (main_routers)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.crm.lojas import lojas_permitidas
from app.db import get_session
from app.security.permissions_decorator import require_permission_dependency

router = APIRouter(
    prefix="/crm",
    tags=["CRM"],
    dependencies=[Depends(require_permission_dependency("crm.visualizar"))],
)


@router.get("/lojas")
async def listar_lojas_do_crm(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lojas que o usuario pode ver no CRM (alimenta o filtro de lojas da tela)."""
    usuario, tenant_id = user_and_tenant
    lojas = lojas_permitidas(db, usuario, tenant_id)
    return {
        "loja_atual_id": str(tenant_id),
        "lojas": [{"id": str(loja.id), "nome": loja.nome} for loja in lojas],
    }
