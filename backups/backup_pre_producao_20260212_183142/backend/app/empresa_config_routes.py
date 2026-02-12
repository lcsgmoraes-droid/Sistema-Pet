"""
Rotas para Configuração Geral da Empresa
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.utils.logger import logger

router = APIRouter(prefix="/empresa/config", tags=["Configuração da Empresa"])


# ===== SCHEMAS =====

class EmpresaConfigGeralCreate(BaseModel):
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    site: Optional[str] = None
    margem_saudavel_minima: float = 30.0
    margem_alerta_minima: float = 15.0
    mensagem_venda_saudavel: str = "✅ Venda Saudável! Margem excelente."
    mensagem_venda_alerta: str = "⚠️ ATENÇÃO: Margem reduzida! Revisar preço."
    mensagem_venda_critica: str = "🚨 CRÍTICO: Margem muito baixa! Venda com prejuízo!"
    dias_tolerancia_atraso: int = 5
    meta_faturamento_mensal: float = 0
    alerta_estoque_percentual: int = 20
    dias_produto_parado: int = 90
    aliquota_imposto_padrao: float = 7.0


class EmpresaConfigGeralUpdate(BaseModel):
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    site: Optional[str] = None
    margem_saudavel_minima: Optional[float] = None
    margem_alerta_minima: Optional[float] = None
    mensagem_venda_saudavel: Optional[str] = None
    mensagem_venda_alerta: Optional[str] = None
    mensagem_venda_critica: Optional[str] = None
    dias_tolerancia_atraso: Optional[int] = None
    meta_faturamento_mensal: Optional[float] = None
    alerta_estoque_percentual: Optional[int] = None
    dias_produto_parado: Optional[int] = None
    aliquota_imposto_padrao: Optional[float] = None


class EmpresaConfigGeralResponse(BaseModel):
    id: int
    razao_social: Optional[str]
    nome_fantasia: Optional[str]
    cnpj: Optional[str]
    margem_saudavel_minima: float
    margem_alerta_minima: float
    mensagem_venda_saudavel: str
    mensagem_venda_alerta: str
    mensagem_venda_critica: str
    aliquota_imposto_padrao: float
    
    class Config:
        from_attributes = True


# ===== ENDPOINTS =====

@router.get("/", response_model=EmpresaConfigGeralResponse)
def get_config_empresa(
    user_tenant: tuple = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Busca a configuração geral da empresa
    Se não existir, retorna configuração padrão
    """
    user, tenant_id = user_tenant
    
    config = db.query(EmpresaConfigGeral).filter(
        EmpresaConfigGeral.tenant_id == tenant_id
    ).first()
    
    if not config:
        # Retorna configuração padrão
        return EmpresaConfigGeralResponse(
            id=0,
            razao_social=None,
            nome_fantasia=None,
            cnpj=None,
            margem_saudavel_minima=30.0,
            margem_alerta_minima=15.0,
            mensagem_venda_saudavel="✅ Venda Saudável! Margem excelente.",
            mensagem_venda_alerta="⚠️ ATENÇÃO: Margem reduzida! Revisar preço.",
            mensagem_venda_critica="🚨 CRÍTICO: Margem muito baixa! Venda com prejuízo!",
            aliquota_imposto_padrao=7.0
        )
    
    return config


@router.post("/", response_model=EmpresaConfigGeralResponse)
def create_config_empresa(
    config_data: EmpresaConfigGeralCreate,
    user_tenant: tuple = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Cria a configuração geral da empresa"""
    user, tenant_id = user_tenant
    
    # Verifica se já existe
    config_existente = db.query(EmpresaConfigGeral).filter(
        EmpresaConfigGeral.tenant_id == tenant_id
    ).first()
    
    if config_existente:
        raise HTTPException(status_code=400, detail="Configuração já existe. Use PUT para atualizar.")
    
    # Cria nova configuração
    config = EmpresaConfigGeral(
        tenant_id=tenant_id,
        **config_data.model_dump()
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    logger.info(f"Configuração da empresa criada para tenant {tenant_id}")
    
    return config


@router.put("/", response_model=EmpresaConfigGeralResponse)
def update_config_empresa(
    config_data: EmpresaConfigGeralUpdate,
    user_tenant: tuple = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Atualiza a configuração geral da empresa"""
    user, tenant_id = user_tenant
    
    config = db.query(EmpresaConfigGeral).filter(
        EmpresaConfigGeral.tenant_id == tenant_id
    ).first()
    
    if not config:
        # Cria se não existir
        config = EmpresaConfigGeral(tenant_id=tenant_id)
        db.add(config)
    
    # Atualiza apenas campos fornecidos
    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    logger.info(f"Configuração da empresa atualizada para tenant {tenant_id}")
    
    return config


@router.delete("/")
def delete_config_empresa(
    user_tenant: tuple = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Remove a configuração da empresa (volta para padrão)"""
    user, tenant_id = user_tenant
    
    config = db.query(EmpresaConfigGeral).filter(
        EmpresaConfigGeral.tenant_id == tenant_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    
    db.delete(config)
    db.commit()
    
    logger.info(f"Configuração da empresa removida para tenant {tenant_id}")
    
    return {"message": "Configuração removida. Usando valores padrão."}
