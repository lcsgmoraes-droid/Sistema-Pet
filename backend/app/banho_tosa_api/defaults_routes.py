from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_defaults import aplicar_base_padrao_banho_tosa
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.post("/defaults/aplicar")
def aplicar_defaults_banho_tosa(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return aplicar_base_padrao_banho_tosa(db, tenant_id)
