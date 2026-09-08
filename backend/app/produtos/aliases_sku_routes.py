"""Configuracao tenant-scoped de aliases comerciais, com preview antes da gravacao."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.security.permissions_decorator import require_permission
from app.services.produto_alias_service import aplicar_alias, preview_alias

router = APIRouter()


class AliasPreviewRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=100)


class AliasApplyRequest(AliasPreviewRequest):
    motivo: str = Field(min_length=10, max_length=2000)
    preview_token: str = Field(min_length=64, max_length=64)


@router.post("/{produto_id}/aliases-sku/preview")
@require_permission("produtos.editar")
def preview_produto_alias(
    produto_id: int,
    payload: AliasPreviewRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    try:
        return preview_alias(
            db, tenant_id=tenant_id, produto_id=produto_id, sku=payload.sku
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{produto_id}/aliases-sku/aplicar")
@require_permission("produtos.editar")
def aplicar_produto_alias(
    produto_id: int,
    payload: AliasApplyRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    try:
        return aplicar_alias(
            db,
            tenant_id=tenant_id,
            produto_id=produto_id,
            sku=payload.sku,
            preview_token=payload.preview_token,
            user_id=user.id,
            motivo=payload.motivo,
        )
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        detail = (
            str(exc)
            if isinstance(exc, ValueError)
            else "Alias em conflito; revise o cadastro novamente."
        )
        raise HTTPException(status_code=409, detail=detail) from exc
