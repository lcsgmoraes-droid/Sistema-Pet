"""
API de Configurações Fiscais e Dados da Empresa
Permite configurar tributação padrão e dados cadastrais da empresa
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.db import get_session as get_db
from app.auth.dependencies import get_current_tenant, get_current_user_and_tenant
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.models import Tenant, User
from app.utils.logger import logger

router = APIRouter(prefix="/empresa", tags=["Empresa - Configuração"])


class EmpresaDadosBasicosUpdate(BaseModel):
    """Schema para atualização dos dados básicos da empresa"""
    name: Optional[str] = None  # Nome Fantasia
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    site: Optional[str] = None
    logo_url: Optional[str] = None


class EmpresaConfigFiscalUpdate(BaseModel):
    """Schema para atualização da configuração fiscal"""
    regime_tributario: Optional[str] = None
    cnae_principal: Optional[str] = None
    cnae_descricao: Optional[str] = None
    cnaes_secundarios: Optional[list] = None
    # Simples Nacional
    simples_ativo: Optional[bool] = None
    simples_anexo: Optional[str] = None
    aliquota_simples_vigente: Optional[float] = None
    aliquota_simples_sugerida: Optional[float] = None
    # ICMS
    icms_aliquota_interna: Optional[float] = None
    icms_aliquota_interestadual: Optional[float] = None
    aplica_difal: Optional[bool] = None
    # CFOPs
    cfop_venda_interna: Optional[str] = None
    cfop_venda_interestadual: Optional[str] = None
    cfop_compra: Optional[str] = None
    # PIS/COFINS
    pis_cst_padrao: Optional[str] = None
    cofins_cst_padrao: Optional[str] = None


@router.get("/dados-basicos")
def obter_dados_basicos_empresa(
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Retorna os dados básicos cadastrais da empresa (tenant).
    """
    _, tenant_id = user_and_tenant
    
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    return {
        "name": tenant.name,
        "razao_social": tenant.razao_social,
        "cnpj": tenant.cnpj,
        "inscricao_estadual": tenant.inscricao_estadual,
        "inscricao_municipal": tenant.inscricao_municipal,
        "endereco": tenant.endereco,
        "numero": tenant.numero,
        "complemento": tenant.complemento,
        "bairro": tenant.bairro,
        "cidade": tenant.cidade,
        "uf": tenant.uf,
        "cep": tenant.cep,
        "telefone": tenant.telefone,
        "email": tenant.email,
        "site": tenant.site,
        "logo_url": tenant.logo_url,
    }


@router.put("/dados-basicos")
def atualizar_dados_basicos_empresa(
    data: EmpresaDadosBasicosUpdate,
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Atualiza os dados básicos cadastrais da empresa.
    """
    _, tenant_id = user_and_tenant
    
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    # Atualizar campos
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(tenant, key):
            setattr(tenant, key, value)
    
    db.commit()
    db.refresh(tenant)
    
    return {
        "message": "Dados da empresa atualizados com sucesso",
        "empresa": {
            "name": tenant.name,
            "razao_social": tenant.razao_social,
            "cnpj": tenant.cnpj,
        }
    }


@router.get("/fiscal")
def obter_config_fiscal_empresa(
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Retorna as configurações fiscais da empresa.
    Se não existir, cria uma configuração padrão baseada no estado.
    """
    config = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )

    if not config:
        # Criar configuração padrão
        config = EmpresaConfigFiscal(
            tenant_id=tenant_id,
            uf="SP",  # Padrão, deve vir do cadastro da empresa
            regime_tributario="Simples Nacional",
            contribuinte_icms=True,
            icms_aliquota_interna=18.0,
            icms_aliquota_interestadual=12.0,
            aplica_difal=True,
            cfop_venda_interna="5102",
            cfop_venda_interestadual="6102",
            cfop_compra="1102",
            herdado_do_estado=True
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return {
        "uf": config.uf,
        "regime_tributario": config.regime_tributario,
        "cnae_principal": config.cnae_principal,
        "cnae_descricao": config.cnae_descricao,
        "cnaes_secundarios": config.cnaes_secundarios,
        "simples_ativo": config.simples_ativo,
        "simples_anexo": config.simples_anexo,
        "aliquota_simples_vigente": float(config.aliquota_simples_vigente or 0),
        "aliquota_simples_sugerida": float(config.aliquota_simples_sugerida or 0),
        "icms_aliquota_interna": float(config.icms_aliquota_interna or 0),
        "icms_aliquota_interestadual": float(config.icms_aliquota_interestadual or 0),
        "aplica_difal": config.aplica_difal,
        "cfop_venda_interna": config.cfop_venda_interna,
        "cfop_venda_interestadual": config.cfop_venda_interestadual,
        "cfop_compra": config.cfop_compra,
        "pis_cst_padrao": config.pis_cst_padrao,
        "cofins_cst_padrao": config.cofins_cst_padrao,
        "herdado_do_estado": config.herdado_do_estado,
    }


@router.put("/fiscal")
def atualizar_config_fiscal_empresa(
    data: EmpresaConfigFiscalUpdate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Atualiza as configurações fiscais da empresa.
    """
    config = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=404,
            detail="Configuração fiscal não encontrada. Execute GET primeiro para criar."
        )

    # Atualizar campos
    update_data = data.dict(exclude_unset=True)
    logger.info(f"🔍 Dados recebidos para atualização fiscal: {update_data}")
    
    for key, value in update_data.items():
        if hasattr(config, key):
            logger.info(f"  ✅ Atualizando {key} = {value}")
            setattr(config, key, value)
        else:
            logger.info(f"  ⚠️ Campo {key} não existe no modelo")

    # Marcar que não é mais herdado do estado (foi personalizado)
    config.herdado_do_estado = False
    
    logger.info(f"💾 CNAE Descrição antes do commit: {config.cnae_descricao}")
    logger.info(f"💾 CNAEs Secundários antes do commit: {config.cnaes_secundarios}")

    db.commit()
    db.refresh(config)
    
    logger.info(f"✅ CNAE Descrição após commit: {config.cnae_descricao}")
    logger.info(f"✅ CNAEs Secundários após commit: {config.cnaes_secundarios}")

    return {
        "message": "Configurações fiscais atualizadas com sucesso",
        "config": {
            "uf": config.uf,
            "regime_tributario": config.regime_tributario,
            "cnae_principal": config.cnae_principal,
            "cnae_descricao": config.cnae_descricao,
            "cnaes_secundarios": config.cnaes_secundarios,
            "simples_ativo": config.simples_ativo,
            "simples_anexo": config.simples_anexo,
            "aliquota_simples_vigente": float(config.aliquota_simples_vigente or 0),
            "aliquota_simples_sugerida": float(config.aliquota_simples_sugerida or 0),
            "icms_aliquota_interna": float(config.icms_aliquota_interna or 0),
            "icms_aliquota_interestadual": float(config.icms_aliquota_interestadual or 0),
            "aplica_difal": config.aplica_difal,
            "cfop_venda_interna": config.cfop_venda_interna,
            "cfop_venda_interestadual": config.cfop_venda_interestadual,
            "cfop_compra": config.cfop_compra,
            "herdado_do_estado": config.herdado_do_estado,
        }
    }
