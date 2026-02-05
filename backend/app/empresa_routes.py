"""
Rotas da Empresa - Configurações Gerais e Fiscais
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.models import User, Tenant
from app.db import get_session
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.utils.logger import logger


router = APIRouter(prefix="/empresa", tags=["Empresa"])


# ============================================================================
# SCHEMAS
# ============================================================================

class DadosCadastraisResponse(BaseModel):
    cnpj: Optional[str] = None
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    cep: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    
    class Config:
        from_attributes = True


class DadosCadastraisUpdate(BaseModel):
    cnpj: Optional[str] = None
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    cep: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None


class ConfigFiscalResponse(BaseModel):
    id: int
    regime_tributario: str
    simples_ativo: bool
    simples_anexo: Optional[str] = None
    aliquota_simples_vigente: Optional[float] = None
    aliquota_simples_sugerida: Optional[float] = None
    uf: str
    cnae_principal: Optional[str] = None
    cnae_descricao: Optional[str] = None
    cnaes_secundarios: Optional[list] = None
    contribuinte_icms: bool
    
    class Config:
        from_attributes = True


class ConfigFiscalUpdate(BaseModel):
    regime_tributario: Optional[str] = None
    simples_ativo: Optional[bool] = None
    simples_anexo: Optional[str] = None
    aliquota_simples_vigente: Optional[float] = None
    aliquota_simples_sugerida: Optional[float] = None
    uf: Optional[str] = None
    cnae_principal: Optional[str] = None
    cnae_descricao: Optional[str] = None
    cnaes_secundarios: Optional[list] = None
    contribuinte_icms: Optional[bool] = None


# ============================================================================
# ENDPOINTS - CONFIGURAÇÃO FISCAL
# ============================================================================

@router.get("/fiscal", response_model=ConfigFiscalResponse)
def buscar_config_fiscal(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Busca a configuração fiscal da empresa do tenant.
    """
    
    tenant_id = current_user.tenant_id
    
    config = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuração fiscal não encontrada. Configure os dados fiscais da empresa."
        )
    
    return config


@router.put("/fiscal", response_model=ConfigFiscalResponse)
def atualizar_config_fiscal(
    dados: ConfigFiscalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Atualiza a configuração fiscal da empresa.
    
    Valida:
    - Se regime é Simples Nacional, simples_ativo deve ser True
    - Se simples_ativo é False, zera campos relacionados
    """
    
    tenant_id = current_user.tenant_id
    
    config = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuração fiscal não encontrada."
        )
    
    logger.info(f"🔍 Dados recebidos para atualização: {dados.model_dump(exclude_unset=True)}")
    logger.info(f"📊 Regime atual antes da atualização: {config.regime_tributario}")
    
    # Atualizar campos fornecidos
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        logger.info(f"  ➜ Atualizando {campo} = {valor}")
        setattr(config, campo, valor)
    
    logger.info(f"📊 Regime após atualização: {config.regime_tributario}")
    logger.info(f"💰 Alíquota vigente após atualização: {config.aliquota_simples_vigente}")
    
    # Validação: Se regime é Simples Nacional, simples_ativo deve ser True
    if config.regime_tributario == "Simples Nacional":
        config.simples_ativo = True
        
        # Garantir valores padrão apenas se não foram fornecidos
        if not config.simples_anexo:
            config.simples_anexo = "I"
        logger.info("✅ Regime Simples Nacional - mantendo alíquotas")
    
    # Se não é Simples ou simples_ativo=False, zerar campos
    elif config.regime_tributario != "Simples Nacional" or not config.simples_ativo:
        logger.info(f"⚠️ ZERANDO alíquotas - Regime: {config.regime_tributario}, Simples Ativo: {config.simples_ativo}")
        config.simples_ativo = False
        config.simples_anexo = None
        config.aliquota_simples_vigente = 0
        config.aliquota_simples_sugerida = 0
    
    logger.info(f"💾 Salvando no banco - Alíquota final: {config.aliquota_simples_vigente}")
    
    db.commit()
    db.refresh(config)
    
    return config


# ============================================================================
# ENDPOINTS - DADOS CADASTRAIS
# ============================================================================

@router.get("/dados-cadastrais", response_model=DadosCadastraisResponse)
def buscar_dados_cadastrais(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Busca os dados cadastrais da empresa (tenant).
    """
    tenant_id = current_user.tenant_id
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )
    
    return DadosCadastraisResponse(
        cnpj=getattr(tenant, 'cnpj', None),
        razao_social=getattr(tenant, 'razao_social', None),
        nome_fantasia=getattr(tenant, 'name', None),
        inscricao_estadual=getattr(tenant, 'inscricao_estadual', None),
        inscricao_municipal=getattr(tenant, 'inscricao_municipal', None),
        email=getattr(tenant, 'email', None),
        telefone=getattr(tenant, 'telefone', None),
        cep=getattr(tenant, 'cep', None),
        endereco=getattr(tenant, 'endereco', None),
        numero=getattr(tenant, 'numero', None),
        complemento=getattr(tenant, 'complemento', None),
        bairro=getattr(tenant, 'bairro', None),
        cidade=getattr(tenant, 'cidade', None),
        uf=getattr(tenant, 'uf', None)
    )


@router.put("/dados-cadastrais", response_model=DadosCadastraisResponse)
def atualizar_dados_cadastrais(
    dados: DadosCadastraisUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Atualiza os dados cadastrais da empresa (tenant).
    """
    tenant_id = current_user.tenant_id
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada"
        )
    
    # Atualizar apenas campos fornecidos
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        # Mapear nome_fantasia para name (campo real no modelo)
        if campo == 'nome_fantasia':
            setattr(tenant, 'name', valor)
        elif hasattr(tenant, campo):
            setattr(tenant, campo, valor)
    
    db.commit()
    db.refresh(tenant)
    
    return DadosCadastraisResponse(
        cnpj=getattr(tenant, 'cnpj', None),
        razao_social=getattr(tenant, 'razao_social', None),
        nome_fantasia=getattr(tenant, 'name', None),
        inscricao_estadual=getattr(tenant, 'inscricao_estadual', None),
        inscricao_municipal=getattr(tenant, 'inscricao_municipal', None),
        email=getattr(tenant, 'email', None),
        telefone=getattr(tenant, 'telefone', None),
        cep=getattr(tenant, 'cep', None),
        endereco=getattr(tenant, 'endereco', None),
        numero=getattr(tenant, 'numero', None),
        complemento=getattr(tenant, 'complemento', None),
        bairro=getattr(tenant, 'bairro', None),
        cidade=getattr(tenant, 'cidade', None),
        uf=getattr(tenant, 'uf', None)
    )
