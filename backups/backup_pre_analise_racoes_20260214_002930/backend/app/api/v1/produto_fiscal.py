from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session as get_db
from app.services.produto_fiscal_apply_service import aplicar_sugestao_fiscal_produto
from app.auth.dependencies import get_current_tenant

router = APIRouter(prefix="/produto", tags=["Produto Fiscal"])


@router.post("/{produto_id}/fiscal/aplicar")
def aplicar_fiscal_produto(
    produto_id: int,
    sugestao: dict,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Aplica manualmente a sugestão fiscal ao produto.
    """
    config = aplicar_sugestao_fiscal_produto(
        db=db,
        tenant_id=tenant_id,
        produto_id=produto_id,
        sugestao=sugestao
    )
    return {"status": "ok", "config_fiscal": config}
