"""
API de Configurações Fiscais e Dados da Empresa
Permite configurar tributação padrão e dados cadastrais da empresa
"""

import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.db import get_session as get_db
from app.auth.dependencies import get_current_user_and_tenant
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.models import Tenant, User
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
    # NFS-e / ISS (usados no rascunho da emissão manual assistida)
    municipio_iss: Optional[str] = None
    municipio_iss_codigo: Optional[str] = None
    iss_aliquota: Optional[float] = None
    iss_retido: Optional[bool] = None
    nfse_item_lista_servico: Optional[str] = None
    nfse_natureza_operacao: Optional[str] = None
    nfse_regime_especial_tributacao: Optional[str] = None
    nfse_incentivador_cultural: Optional[bool] = None
    nfse_portal_url: Optional[str] = None


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
        "uf": tenant.uf,
        "cep": tenant.cep,
        "telefone": tenant.telefone,
        "email": tenant.email,
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

    config = (
        db.query(EmpresaConfigFiscal)
        .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
        .first()
    )
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    is_prudente = bool(
        tenant
        and (tenant.cidade or "").strip().lower() == "presidente prudente"
        and (tenant.uf or "").upper() == "SP"
    )

    if not config:
        # Criar configuração padrão
        config = EmpresaConfigFiscal(
            tenant_id=tenant_id,
            uf=(tenant.uf or "SP").upper() if tenant else "SP",
            regime_tributario="Simples Nacional",
            contribuinte_icms=True,
            icms_aliquota_interna=18.0,
            icms_aliquota_interestadual=12.0,
            aplica_difal=True,
            cfop_venda_interna="5102",
            cfop_venda_interestadual="6102",
            cfop_compra="1102",
            herdado_do_estado=True,
            municipio_iss=tenant.cidade if tenant else None,
            municipio_iss_codigo="3541406" if is_prudente else None,
            iss_retido=False,
            nfse_natureza_operacao="1",
            nfse_incentivador_cultural=False,
            nfse_portal_url="https://issprudente.sp.gov.br/" if is_prudente else None,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    else:
        defaults_changed = False
        if not config.municipio_iss and tenant and tenant.cidade:
            config.municipio_iss = tenant.cidade
            defaults_changed = True
        if is_prudente and not config.municipio_iss_codigo:
            config.municipio_iss_codigo = "3541406"
            defaults_changed = True
        if is_prudente and not config.nfse_portal_url:
            config.nfse_portal_url = "https://issprudente.sp.gov.br/"
            defaults_changed = True
        if not config.nfse_natureza_operacao:
            config.nfse_natureza_operacao = "1"
            defaults_changed = True
        if defaults_changed:
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
        "municipio_iss": config.municipio_iss,
        "municipio_iss_codigo": config.municipio_iss_codigo,
        "iss_aliquota": float(config.iss_aliquota)
        if config.iss_aliquota is not None
        else None,
        "iss_retido": bool(config.iss_retido),
        "nfse_item_lista_servico": config.nfse_item_lista_servico,
        "nfse_natureza_operacao": config.nfse_natureza_operacao or "1",
        "nfse_regime_especial_tributacao": config.nfse_regime_especial_tributacao,
        "nfse_incentivador_cultural": bool(config.nfse_incentivador_cultural),
        "nfse_portal_url": config.nfse_portal_url,
        "herdado_do_estado": config.herdado_do_estado,
    }


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

    # Atualizar campos
    update_data = data.dict(exclude_unset=True)
    municipality_code = update_data.get("municipio_iss_codigo")
    if municipality_code and not re.fullmatch(r"\d{7}", municipality_code.strip()):
        raise HTTPException(
            status_code=422, detail="Código IBGE do município deve ter 7 dígitos."
        )
    if municipality_code:
        update_data["municipio_iss_codigo"] = municipality_code.strip()
    service_item = update_data.get("nfse_item_lista_servico")
    if service_item and not re.fullmatch(r"\d{1,2}\.\d{2}", service_item.strip()):
        raise HTTPException(
            status_code=422,
            detail="Item da lista de serviços deve usar formato como 5.01.",
        )
    if service_item:
        update_data["nfse_item_lista_servico"] = service_item.strip()
    if update_data.get("nfse_natureza_operacao") not in {
        None,
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    }:
        raise HTTPException(
            status_code=422, detail="Natureza da operação deve ficar entre 1 e 6."
        )
    if update_data.get("nfse_regime_especial_tributacao") not in {
        None,
        "",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    }:
        raise HTTPException(
            status_code=422, detail="Regime especial deve ficar entre 1 e 6."
        )
    iss_rate = update_data.get("iss_aliquota")
    if iss_rate is not None and not 0 <= iss_rate <= 100:
        raise HTTPException(
            status_code=422, detail="Alíquota de ISS deve ficar entre 0 e 100."
        )
    portal_url = (update_data.get("nfse_portal_url") or "").strip()
    if portal_url:
        if len(portal_url) > 500:
            raise HTTPException(
                status_code=422, detail="A URL do portal de NFS-e é muito longa."
            )
        parsed_portal = urlparse(portal_url)
        if parsed_portal.scheme not in {"http", "https"} or not parsed_portal.netloc:
            raise HTTPException(
                status_code=422, detail="Informe uma URL válida para o portal de NFS-e."
            )
        update_data["nfse_portal_url"] = portal_url
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
            "icms_aliquota_interestadual": float(
                config.icms_aliquota_interestadual or 0
            ),
            "aplica_difal": config.aplica_difal,
            "cfop_venda_interna": config.cfop_venda_interna,
            "cfop_venda_interestadual": config.cfop_venda_interestadual,
            "cfop_compra": config.cfop_compra,
            "municipio_iss": config.municipio_iss,
            "municipio_iss_codigo": config.municipio_iss_codigo,
            "iss_aliquota": float(config.iss_aliquota)
            if config.iss_aliquota is not None
            else None,
            "iss_retido": bool(config.iss_retido),
            "nfse_item_lista_servico": config.nfse_item_lista_servico,
            "nfse_natureza_operacao": config.nfse_natureza_operacao or "1",
            "nfse_regime_especial_tributacao": config.nfse_regime_especial_tributacao,
            "nfse_incentivador_cultural": bool(config.nfse_incentivador_cultural),
            "nfse_portal_url": config.nfse_portal_url,
            "herdado_do_estado": config.herdado_do_estado,
        },
    }
