"""
Rotas para Configuração Geral da Empresa
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.security.permissions_decorator import require_permission
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
    crediario_encargos_automaticos: bool = False
    crediario_multa_percentual: float = Field(default=2.0, ge=0, le=2)
    crediario_juros_mensal_percentual: float = Field(default=1.0, ge=0, le=100)
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
    crediario_encargos_automaticos: Optional[bool] = None
    crediario_multa_percentual: Optional[float] = Field(default=None, ge=0, le=2)
    crediario_juros_mensal_percentual: Optional[float] = Field(
        default=None, ge=0, le=100
    )
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
    dias_tolerancia_atraso: Optional[int] = 5
    crediario_encargos_automaticos: bool
    crediario_multa_percentual: float
    crediario_juros_mensal_percentual: float
    meta_faturamento_mensal: Optional[float] = 0
    alerta_estoque_percentual: Optional[int] = 20
    dias_produto_parado: Optional[int] = 90

    class Config:
        from_attributes = True


def _serializar_config(config: EmpresaConfigGeral) -> EmpresaConfigGeralResponse:
    """Mantem a API compativel com configuracoes antigas que possuem campos nulos."""
    return EmpresaConfigGeralResponse(
        id=config.id,
        razao_social=config.razao_social,
        nome_fantasia=config.nome_fantasia,
        cnpj=config.cnpj,
        margem_saudavel_minima=float(config.margem_saudavel_minima or 30),
        margem_alerta_minima=float(config.margem_alerta_minima or 15),
        mensagem_venda_saudavel=(
            config.mensagem_venda_saudavel or "✅ Venda Saudável! Margem excelente."
        ),
        mensagem_venda_alerta=(
            config.mensagem_venda_alerta or "⚠️ ATENÇÃO: Margem reduzida! Revisar preço."
        ),
        mensagem_venda_critica=(
            config.mensagem_venda_critica
            or "🚨 CRÍTICO: Margem muito baixa! Venda com prejuízo!"
        ),
        aliquota_imposto_padrao=float(config.aliquota_imposto_padrao or 7),
        dias_tolerancia_atraso=(
            config.dias_tolerancia_atraso
            if config.dias_tolerancia_atraso is not None
            else 5
        ),
        crediario_encargos_automaticos=bool(config.crediario_encargos_automaticos),
        crediario_multa_percentual=float(config.crediario_multa_percentual or 0),
        crediario_juros_mensal_percentual=float(
            config.crediario_juros_mensal_percentual or 0
        ),
        meta_faturamento_mensal=float(config.meta_faturamento_mensal or 0),
        alerta_estoque_percentual=(
            config.alerta_estoque_percentual
            if config.alerta_estoque_percentual is not None
            else 20
        ),
        dias_produto_parado=(
            config.dias_produto_parado if config.dias_produto_parado is not None else 90
        ),
    )


# ===== ENDPOINTS =====


@router.get("/", response_model=EmpresaConfigGeralResponse)
@require_permission("configuracoes.editar")
def get_config_empresa(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """
    Busca a configuração geral da empresa
    Se não existir, retorna configuração padrão
    """
    current_user, tenant_id = user_and_tenant

    config = (
        db.query(EmpresaConfigGeral)
        .filter(EmpresaConfigGeral.tenant_id == tenant_id)
        .first()
    )

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
            aliquota_imposto_padrao=7.0,
            dias_tolerancia_atraso=5,
            crediario_encargos_automaticos=False,
            crediario_multa_percentual=2.0,
            crediario_juros_mensal_percentual=1.0,
            meta_faturamento_mensal=0,
            alerta_estoque_percentual=20,
            dias_produto_parado=90,
        )

    return _serializar_config(config)


@router.post("/", response_model=EmpresaConfigGeralResponse)
@require_permission("configuracoes.editar")
def create_config_empresa(
    config_data: EmpresaConfigGeralCreate,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Cria a configuração geral da empresa"""
    current_user, tenant_id = user_and_tenant

    # Verifica se já existe
    config_existente = (
        db.query(EmpresaConfigGeral)
        .filter(EmpresaConfigGeral.tenant_id == tenant_id)
        .first()
    )

    if config_existente:
        raise HTTPException(
            status_code=400, detail="Configuração já existe. Use PUT para atualizar."
        )

    # Cria nova configuração
    config = EmpresaConfigGeral(tenant_id=tenant_id, **config_data.model_dump())

    db.add(config)
    db.commit()
    db.refresh(config)

    logger.info(f"Configuração da empresa criada para tenant {tenant_id}")

    return _serializar_config(config)


@router.put("/", response_model=EmpresaConfigGeralResponse)
@require_permission("configuracoes.editar")
def update_config_empresa(
    config_data: EmpresaConfigGeralUpdate,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Atualiza a configuração geral da empresa"""
    current_user, tenant_id = user_and_tenant

    config = (
        db.query(EmpresaConfigGeral)
        .filter(EmpresaConfigGeral.tenant_id == tenant_id)
        .first()
    )

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

    return _serializar_config(config)


@router.delete("/")
@require_permission("configuracoes.editar")
def delete_config_empresa(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Remove a configuração da empresa (volta para padrão)"""
    current_user, tenant_id = user_and_tenant

    config = (
        db.query(EmpresaConfigGeral)
        .filter(EmpresaConfigGeral.tenant_id == tenant_id)
        .first()
    )

    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")

    db.delete(config)
    db.commit()

    logger.info(f"Configuração da empresa removida para tenant {tenant_id}")

    return {"message": "Configuração removida. Usando valores padrão."}
