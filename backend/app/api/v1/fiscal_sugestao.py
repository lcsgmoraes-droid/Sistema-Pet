from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session as get_db
from app.services.fiscal_sugestao_service import (
    pesquisar_base_fiscal,
    sugerir_fiscal_por_descricao,
)

router = APIRouter(prefix="/fiscal/sugestao", tags=["Fiscal"])


class SugestaoProdutoRequest(BaseModel):
    descricao: str = Field(min_length=2, max_length=500)


@router.post("/produto")
def sugestao_fiscal_produto(
    payload: Annotated[SugestaoProdutoRequest, Body()],
    _user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Sugere sem gravar; mantido para o cadastro fiscal legado do produto."""
    return {"sugestoes": sugerir_fiscal_por_descricao(db, payload.descricao)}


@router.get("/pesquisar")
def pesquisar_referencias_fiscais(
    q: Annotated[str, Query(min_length=2, max_length=200)],
    limite: Annotated[int, Query(ge=1, le=20)] = 8,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Pesquisa referências fiscais sem alterar o cadastro do produto."""
    _user, tenant_id = user_and_tenant
    return pesquisar_base_fiscal(db, tenant_id, q, limite)
