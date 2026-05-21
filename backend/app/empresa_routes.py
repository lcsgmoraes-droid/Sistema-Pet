"""
Rotas da Empresa - Configurações Gerais e Fiscais
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.models import Tenant
from app.db import get_session
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.estoque_validade_service import EstoqueValidadeService
from app.security.permissions_decorator import require_any_permission, require_permission
from app.utils.logger import logger


router = APIRouter(prefix="/empresa", tags=["Empresa"])


def _buscar_tenant_por_contexto(db: Session, tenant_id) -> Tenant | None:
    return db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()


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
    
    @field_validator('cnaes_secundarios', mode='before')
    @classmethod
    def ensure_list(cls, v):
        """Garante que cnaes_secundarios sempre seja uma lista"""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []
    
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
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def buscar_config_fiscal(
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Busca a configuração fiscal da empresa do tenant.
    """
    
    _current_user, tenant_id = user_and_tenant
    
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
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def atualizar_config_fiscal(
    dados: ConfigFiscalUpdate,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Atualiza a configuração fiscal da empresa.
    
    Valida:
    - Se regime é Simples Nacional, simples_ativo deve ser True
    - Se simples_ativo é False, zera campos relacionados
    """
    
    _current_user, tenant_id = user_and_tenant
    
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
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def buscar_dados_cadastrais(
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Busca os dados cadastrais da empresa (tenant).
    """
    _current_user, tenant_id = user_and_tenant
    
    tenant = _buscar_tenant_por_contexto(db, tenant_id)
    
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
@require_any_permission(("configuracoes.empresa", "configuracoes.editar"))
def atualizar_dados_cadastrais(
    dados: DadosCadastraisUpdate,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Atualiza os dados cadastrais da empresa (tenant).
    """
    _current_user, tenant_id = user_and_tenant
    
    tenant = _buscar_tenant_por_contexto(db, tenant_id)
    
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


# ============================================================================
# ENDPOINTS - CONFIGURAÃ‡ÃƒO DE ESTOQUE
# ============================================================================

class ConfigEstoqueResponse(BaseModel):
    permite_estoque_negativo: bool
    protecao_validade_ativa: bool = False
    dias_alerta_validade: int = 15
    bloquear_validade_pdv: bool = True
    bloquear_validade_ecommerce: bool = True
    bloquear_validade_integracoes_online: bool = False
    
    class Config:
        from_attributes = True


class ConfigEstoqueUpdate(BaseModel):
    permite_estoque_negativo: bool
    protecao_validade_ativa: bool = False
    dias_alerta_validade: int = 15
    bloquear_validade_pdv: bool = True
    bloquear_validade_ecommerce: bool = True
    bloquear_validade_integracoes_online: bool = False


def _config_estoque_response(tenant: Tenant) -> ConfigEstoqueResponse:
    return ConfigEstoqueResponse(
        permite_estoque_negativo=tenant.permite_estoque_negativo,
        protecao_validade_ativa=bool(getattr(tenant, "protecao_validade_ativa", False)),
        dias_alerta_validade=int(getattr(tenant, "dias_alerta_validade", 15) or 15),
        bloquear_validade_pdv=bool(getattr(tenant, "bloquear_validade_pdv", True)),
        bloquear_validade_ecommerce=bool(getattr(tenant, "bloquear_validade_ecommerce", True)),
        bloquear_validade_integracoes_online=bool(
            getattr(tenant, "bloquear_validade_integracoes_online", False)
        ),
    )


@router.get("/config-estoque", response_model=ConfigEstoqueResponse)
@require_permission("configuracoes.editar")
def buscar_config_estoque(
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Busca configuraÃ§Ãµes de estoque do tenant.
    """
    _current_user, tenant_id = user_and_tenant
    
    tenant = _buscar_tenant_por_contexto(db, tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa nÃ£o encontrada"
        )
    
    return _config_estoque_response(tenant)


@router.put("/config-estoque", response_model=ConfigEstoqueResponse)
@require_permission("configuracoes.editar")
def atualizar_config_estoque(
    config: ConfigEstoqueUpdate,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Atualiza configuraÃ§Ãµes de estoque do tenant.
    
    IMPORTANTE: 
    - Se permite_estoque_negativo = True: Sistema permite vendas mesmo sem estoque
    - Se permite_estoque_negativo = False: Sistema bloqueia vendas quando estoque insuficiente (padrÃ£o)
    """
    _current_user, tenant_id = user_and_tenant
    
    tenant = _buscar_tenant_por_contexto(db, tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa nÃ£o encontrada"
        )
    
    # Atualizar configuraÃ§Ã£o
    tenant.permite_estoque_negativo = config.permite_estoque_negativo
    tenant.protecao_validade_ativa = config.protecao_validade_ativa
    tenant.dias_alerta_validade = max(1, min(int(config.dias_alerta_validade or 15), 365))
    tenant.bloquear_validade_pdv = config.bloquear_validade_pdv
    tenant.bloquear_validade_ecommerce = config.bloquear_validade_ecommerce
    tenant.bloquear_validade_integracoes_online = config.bloquear_validade_integracoes_online
    
    db.commit()
    db.refresh(tenant)

    if tenant.protecao_validade_ativa:
        try:
            resultado_validade = EstoqueValidadeService.processar_lotes_em_risco(
                db=db,
                tenant=tenant,
                user_id=getattr(_current_user, "id", None),
                origem="configuracao",
            )
            db.commit()
            db.refresh(tenant)
            processados = int(resultado_validade.get("processados") or 0)
            if processados:
                logger.info(
                    f"Validade processada apos ativar configuracao - Tenant: {tenant.name}, "
                    f"Lotes: {processados}"
                )
        except Exception as exc:
            db.rollback()
            logger.warning(
                f"Nao foi possivel processar lotes por validade apos salvar configuracao "
                f"- Tenant: {tenant.name}, erro: {exc}"
            )
    
    logger.info(
        f"âœ… ConfiguraÃ§Ã£o de estoque atualizada - Tenant: {tenant.name}, "
        f"Permite Estoque Negativo: {tenant.permite_estoque_negativo}"
    )
    
    return _config_estoque_response(tenant)
