"""
API de Configurações Fiscais e Dados da Empresa
Permite configurar tributação padrão e dados cadastrais da empresa
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from uuid import UUID

from app.db import get_session as get_db
from app.auth.dependencies import get_current_user_and_tenant
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.fiscal_state_rules import production_fiscal_pending, state_profile_payload
from app.models import Tenant, User
from app.services.fiscal_config_service import (
    obter_ou_criar_config_fiscal_empresa_padrao,
)
from app.security.permissions_decorator import require_any_permission
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
    codigo_municipio: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    email_resposta: Optional[EmailStr] = None
    site: Optional[str] = None
    logo_url: Optional[str] = None

    @field_validator("email_resposta", mode="before")
    @classmethod
    def empty_reply_email_as_none(cls, value):
        if value is None or not str(value).strip():
            return None
        return str(value).strip()


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
    configuracao_confirmada: Optional[bool] = None

    @field_validator("icms_aliquota_interna", "icms_aliquota_interestadual")
    @classmethod
    def validate_icms_rate(cls, value):
        if value is not None and not 0 <= value <= 100:
            raise ValueError("Alíquota de ICMS deve ficar entre 0% e 100%")
        return value

    @field_validator("cfop_venda_interna", "cfop_venda_interestadual", "cfop_compra")
    @classmethod
    def validate_cfop(cls, value):
        if value is not None and (len(value) != 4 or not value.isdigit()):
            raise ValueError("CFOP deve conter quatro dígitos")
        return value


def _config_fiscal_response(config, tenant):
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
        "configuracao_confirmada": bool(config.configuracao_confirmada),
        "configuracao_confirmada_em": config.configuracao_confirmada_em,
        "perfil_estado": state_profile_payload(config.uf),
        "pendencias_producao": production_fiscal_pending(tenant, config),
    }


@router.get("/dados-basicos")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
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
        "codigo_municipio": tenant.codigo_municipio,
        "uf": tenant.uf,
        "cep": tenant.cep,
        "telefone": tenant.telefone,
        "email": tenant.email,
        "email_resposta": tenant.email_resposta,
        "site": tenant.site,
        "logo_url": tenant.logo_url,
    }


@router.put("/dados-basicos")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
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
        },
    }


@router.get("/fiscal")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def obter_config_fiscal_empresa(
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    """
    Retorna as configurações fiscais da empresa.
    Se não existir, cria uma configuração padrão baseada no estado.
    """
    _, tenant_id = user_and_tenant

    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    config = obter_ou_criar_config_fiscal_empresa_padrao(db, tenant_id, commit=True)
    return _config_fiscal_response(config, tenant)


@router.put("/fiscal")
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def atualizar_config_fiscal_empresa(
    data: EmpresaConfigFiscalUpdate,
    db: Session = Depends(get_db),
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
):
    """
    Atualiza as configurações fiscais da empresa.
    """
    _, tenant_id = user_and_tenant

    config = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=404,
            detail="Configuração fiscal não encontrada. Execute GET primeiro para criar.",
        )

    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Atualizar campos. Qualquer alteração fiscal exige nova confirmação explícita.
    update_data = data.model_dump(exclude_unset=True)
    confirmation = update_data.pop("configuracao_confirmada", None)
    logger.info(f"🔍 Dados recebidos para atualização fiscal: {update_data}")

    for key, value in update_data.items():
        if hasattr(config, key):
            logger.info(f"  ✅ Atualizando {key} = {value}")
            setattr(config, key, value)
        else:
            logger.info(f"  ⚠️ Campo {key} não existe no modelo")

    # Marcar que não é mais herdado do estado (foi personalizado)
    config.herdado_do_estado = False
    if "simples" in str(config.regime_tributario or "").casefold():
        config.aplica_difal = False
    if confirmation is True:
        config.configuracao_confirmada = True
        config.configuracao_confirmada_em = datetime.now(timezone.utc)
    elif confirmation is False or update_data:
        config.configuracao_confirmada = False
        config.configuracao_confirmada_em = None

    logger.info(f"💾 CNAE Descrição antes do commit: {config.cnae_descricao}")
    logger.info(f"💾 CNAEs Secundários antes do commit: {config.cnaes_secundarios}")

    db.commit()
    db.refresh(config)

    logger.info(f"✅ CNAE Descrição após commit: {config.cnae_descricao}")
    logger.info(f"✅ CNAEs Secundários após commit: {config.cnaes_secundarios}")

    return {
        "message": "Configurações fiscais atualizadas com sucesso",
        "config": _config_fiscal_response(config, tenant),
    }
