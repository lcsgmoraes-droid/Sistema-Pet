"""Rotas de Configuração da Loja Virtual (E-commerce)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Tenant
from app.security.permissions_decorator import require_permission

router = APIRouter(prefix="/ecommerce-config", tags=["ecommerce-config"])


# ─── Schemas ───────────────────────────────────────────────────────────────


class EcommerceConfigResponse(BaseModel):
    ecommerce_ativo: bool
    ecommerce_descricao: Optional[str]
    ecommerce_horario_abertura: Optional[str]
    ecommerce_horario_fechamento: Optional[str]
    ecommerce_dias_funcionamento: Optional[str]
    ecommerce_entrega_ativa: bool
    ecommerce_retirada_ativa: bool
    ecommerce_taxa_entrega: float
    ecommerce_frete_gratis_acima: Optional[float]
    ecommerce_pedido_minimo: float
    ecommerce_prazo_entrega_texto: Optional[str]
    ecommerce_usar_estoque_canal: bool
    ecommerce_ocultar_sem_estoque: bool
    ecommerce_ocultar_sem_imagem: bool
    ecommerce_ocultar_servicos: bool
    ecommerce_cor_primaria: str
    ecommerce_cor_secundaria: str

    class Config:
        from_attributes = True


class EcommerceConfigUpdate(BaseModel):
    ecommerce_ativo: Optional[bool] = None
    ecommerce_descricao: Optional[str] = None
    ecommerce_horario_abertura: Optional[str] = None
    ecommerce_horario_fechamento: Optional[str] = None
    ecommerce_dias_funcionamento: Optional[str] = None
    ecommerce_entrega_ativa: Optional[bool] = None
    ecommerce_retirada_ativa: Optional[bool] = None
    ecommerce_taxa_entrega: Optional[float] = Field(default=None, ge=0)
    ecommerce_frete_gratis_acima: Optional[float] = Field(default=None, ge=0)
    ecommerce_pedido_minimo: Optional[float] = Field(default=None, ge=0)
    ecommerce_prazo_entrega_texto: Optional[str] = Field(default=None, max_length=80)
    ecommerce_usar_estoque_canal: Optional[bool] = None
    ecommerce_ocultar_sem_estoque: Optional[bool] = None
    ecommerce_ocultar_sem_imagem: Optional[bool] = None
    ecommerce_ocultar_servicos: Optional[bool] = None
    ecommerce_cor_primaria: Optional[str] = Field(
        default=None, pattern=r"^#[0-9A-Fa-f]{6}$"
    )
    ecommerce_cor_secundaria: Optional[str] = Field(
        default=None, pattern=r"^#[0-9A-Fa-f]{6}$"
    )


_CONFIG_FIELDS = tuple(EcommerceConfigResponse.model_fields)


def _serialize_config(tenant: Tenant) -> EcommerceConfigResponse:
    values = {field: getattr(tenant, field, None) for field in _CONFIG_FIELDS}
    values.update(
        {
            "ecommerce_ativo": bool(
                tenant.ecommerce_ativo if tenant.ecommerce_ativo is not None else True
            ),
            "ecommerce_entrega_ativa": bool(tenant.ecommerce_entrega_ativa),
            "ecommerce_retirada_ativa": bool(tenant.ecommerce_retirada_ativa),
            "ecommerce_taxa_entrega": float(tenant.ecommerce_taxa_entrega or 0),
            "ecommerce_pedido_minimo": float(tenant.ecommerce_pedido_minimo or 0),
            "ecommerce_usar_estoque_canal": bool(tenant.ecommerce_usar_estoque_canal),
            "ecommerce_ocultar_sem_estoque": bool(tenant.ecommerce_ocultar_sem_estoque),
            "ecommerce_ocultar_sem_imagem": bool(tenant.ecommerce_ocultar_sem_imagem),
            "ecommerce_ocultar_servicos": bool(tenant.ecommerce_ocultar_servicos),
            "ecommerce_cor_primaria": tenant.ecommerce_cor_primaria or "#f97316",
            "ecommerce_cor_secundaria": tenant.ecommerce_cor_secundaria or "#0f766e",
        }
    )
    if tenant.ecommerce_frete_gratis_acima is not None:
        values["ecommerce_frete_gratis_acima"] = float(
            tenant.ecommerce_frete_gratis_acima
        )
    return EcommerceConfigResponse(**values)


# ─── Endpoints ─────────────────────────────────────────────────────────────


@router.get("", response_model=EcommerceConfigResponse)
@require_permission("configuracoes.editar")
def buscar_config(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Retorna as configurações da loja virtual do tenant."""
    _, tenant_id = user_and_tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    return _serialize_config(tenant)


@router.put("", response_model=EcommerceConfigResponse)
@require_permission("configuracoes.editar")
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

    for field in body.model_fields_set:
        value = getattr(body, field)
        if isinstance(value, str):
            value = value.strip() or None
        setattr(tenant, field, value)

    db.commit()
    db.refresh(tenant)

    return _serialize_config(tenant)
