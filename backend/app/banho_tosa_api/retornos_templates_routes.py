from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.banho_tosa_retornos_templates import (
    atualizar_template_retorno,
    criar_template_retorno,
    listar_templates_retorno,
    serializar_template_retorno,
)
from app.banho_tosa_schemas import (
    BanhoTosaRetornoTemplateCreate,
    BanhoTosaRetornoTemplateResponse,
    BanhoTosaRetornoTemplateUpdate,
)
from app.db import get_session
from app.veterinario_core import _get_tenant


router = APIRouter()


@router.get("/retornos/templates", response_model=List[BanhoTosaRetornoTemplateResponse])
def listar_templates(
    tipo_retorno: Optional[str] = Query(None),
    canal: Optional[str] = Query(None),
    ativos_only: bool = Query(False),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    templates = listar_templates_retorno(
        db,
        tenant_id,
        tipo_retorno=tipo_retorno,
        canal=canal,
        ativos_only=ativos_only,
    )
    return [serializar_template_retorno(item) for item in templates]


@router.post("/retornos/templates", response_model=BanhoTosaRetornoTemplateResponse, status_code=201)
def criar_template(
    body: BanhoTosaRetornoTemplateCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return criar_template_retorno(db, tenant_id, body.model_dump())


@router.patch("/retornos/templates/{template_id}", response_model=BanhoTosaRetornoTemplateResponse)
def atualizar_template(
    template_id: int,
    body: BanhoTosaRetornoTemplateUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _get_tenant(current)
    return atualizar_template_retorno(db, tenant_id, template_id, body.model_dump(exclude_unset=True))
