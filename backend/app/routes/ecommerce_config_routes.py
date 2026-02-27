"""Rotas de Configuração da Loja Virtual (E-commerce)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Tenant

router = APIRouter(prefix="/ecommerce-config", tags=["ecommerce-config"])


# ─── Schemas ───────────────────────────────────────────────────────────────

class EcommerceConfigResponse(BaseModel):
    ecommerce_ativo: bool
    ecommerce_descricao: Optional[str]
    ecommerce_horario_abertura: Optional[str]
    ecommerce_horario_fechamento: Optional[str]
    ecommerce_dias_funcionamento: Optional[str]

    class Config:
        from_attributes = True


class EcommerceConfigUpdate(BaseModel):
    ecommerce_ativo: Optional[bool] = None
    ecommerce_descricao: Optional[str] = None
    ecommerce_horario_abertura: Optional[str] = None
    ecommerce_horario_fechamento: Optional[str] = None
    ecommerce_dias_funcionamento: Optional[str] = None


# ─── Endpoints ─────────────────────────────────────────────────────────────

@router.get("", response_model=EcommerceConfigResponse)
def buscar_config(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Retorna as configurações da loja virtual do tenant."""
    _, tenant_id = user_and_tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    return EcommerceConfigResponse(
        ecommerce_ativo=tenant.ecommerce_ativo if tenant.ecommerce_ativo is not None else True,
        ecommerce_descricao=tenant.ecommerce_descricao,
        ecommerce_horario_abertura=tenant.ecommerce_horario_abertura,
        ecommerce_horario_fechamento=tenant.ecommerce_horario_fechamento,
        ecommerce_dias_funcionamento=tenant.ecommerce_dias_funcionamento,
    )


@router.put("", response_model=EcommerceConfigResponse)
def atualizar_config(
    body: EcommerceConfigUpdate,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Atualiza as configurações da loja virtual do tenant."""
    _, tenant_id = user_and_tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    if body.ecommerce_ativo is not None:
        tenant.ecommerce_ativo = body.ecommerce_ativo
    if body.ecommerce_descricao is not None:
        tenant.ecommerce_descricao = body.ecommerce_descricao
    if body.ecommerce_horario_abertura is not None:
        tenant.ecommerce_horario_abertura = body.ecommerce_horario_abertura
    if body.ecommerce_horario_fechamento is not None:
        tenant.ecommerce_horario_fechamento = body.ecommerce_horario_fechamento
    if body.ecommerce_dias_funcionamento is not None:
        tenant.ecommerce_dias_funcionamento = body.ecommerce_dias_funcionamento

    db.commit()
    db.refresh(tenant)

    return EcommerceConfigResponse(
        ecommerce_ativo=tenant.ecommerce_ativo if tenant.ecommerce_ativo is not None else True,
        ecommerce_descricao=tenant.ecommerce_descricao,
        ecommerce_horario_abertura=tenant.ecommerce_horario_abertura,
        ecommerce_horario_fechamento=tenant.ecommerce_horario_fechamento,
        ecommerce_dias_funcionamento=tenant.ecommerce_dias_funcionamento,
    )
