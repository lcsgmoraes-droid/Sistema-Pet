"""
Rotas para Configuração Geral da Empresa
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, model_validator
from typing import Optional

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.caixa_models import Caixa
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
    margem_preco_sugestao_1: float = Field(default=30.0, ge=0, lt=100)
    margem_preco_sugestao_2: float = Field(default=34.0, ge=0, lt=100)
    mensagem_venda_saudavel: str = "✅ Venda Saudável! Margem excelente."
    mensagem_venda_alerta: str = "⚠️ ATENÇÃO: Margem reduzida! Revisar preço."
    mensagem_venda_critica: str = "🚨 CRÍTICO: Margem muito baixa! Venda com prejuízo!"
    caixa_compartilhado: bool = False
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
    margem_preco_sugestao_1: Optional[float] = Field(default=None, ge=0, lt=100)
    margem_preco_sugestao_2: Optional[float] = Field(default=None, ge=0, lt=100)
    mensagem_venda_saudavel: Optional[str] = None
    mensagem_venda_alerta: Optional[str] = None
    mensagem_venda_critica: Optional[str] = None
    caixa_compartilhado: Optional[bool] = None
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
    margem_preco_sugestao_1: float
    margem_preco_sugestao_2: float
    mensagem_venda_saudavel: str
    mensagem_venda_alerta: str
    mensagem_venda_critica: str
    caixa_compartilhado: bool
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
        margem_preco_sugestao_1=float(
            getattr(config, "margem_preco_sugestao_1", None)
            if getattr(config, "margem_preco_sugestao_1", None) is not None
            else 30
        ),
        margem_preco_sugestao_2=float(
            getattr(config, "margem_preco_sugestao_2", None)
            if getattr(config, "margem_preco_sugestao_2", None) is not None
            else 34
        ),
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
        caixa_compartilhado=bool(
            getattr(config, "caixa_compartilhado", False)
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


class EmpresaConfigMargensPrecoUpdate(BaseModel):
    margem_preco_sugestao_1: float = Field(ge=0, lt=100)
    margem_preco_sugestao_2: float = Field(ge=0, lt=100)

    @model_validator(mode="after")
    def validar_sugestoes_diferentes(self):
        if self.margem_preco_sugestao_1 == self.margem_preco_sugestao_2:
            raise ValueError("As duas sugestões de margem precisam ser diferentes.")
        return self


class EmpresaConfigMargensPrecoResponse(BaseModel):
    margem_preco_sugestao_1: float = Field(ge=0, lt=100)
    margem_preco_sugestao_2: float = Field(ge=0, lt=100)


def _serializar_margens_preco(
    config: Optional[EmpresaConfigGeral],
) -> EmpresaConfigMargensPrecoResponse:
    if not config:
        return EmpresaConfigMargensPrecoResponse(
            margem_preco_sugestao_1=30.0,
            margem_preco_sugestao_2=34.0,
        )

    margem_1 = getattr(config, "margem_preco_sugestao_1", None)
    margem_2 = getattr(config, "margem_preco_sugestao_2", None)
    return EmpresaConfigMargensPrecoResponse(
        margem_preco_sugestao_1=float(margem_1 if margem_1 is not None else 30),
        margem_preco_sugestao_2=float(margem_2 if margem_2 is not None else 34),
    )


def _validar_ativacao_caixa_compartilhado(db: Session, tenant_id) -> None:
    """Impede ativar o modo enquanto houver mais de um caixa aberto na loja."""
    caixas_abertos = (
        db.query(Caixa.id)
        .filter(Caixa.tenant_id == tenant_id, Caixa.status == "aberto")
        .count()
    )
    if caixas_abertos > 1:
        raise HTTPException(
            status_code=400,
            detail=(
                "Para compartilhar o caixa, feche os caixas extras e mantenha "
                "somente um caixa aberto na empresa."
            ),
        )


# ===== ENDPOINTS =====


@router.get("/margens-preco", response_model=EmpresaConfigMargensPrecoResponse)
@require_permission("produtos.editar")
def get_margens_preco(
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Busca as duas margens sugeridas no cadastro de produtos."""
    _, tenant_id = user_and_tenant
    config = (
        db.query(EmpresaConfigGeral)
        .filter(EmpresaConfigGeral.tenant_id == tenant_id)
        .first()
    )
    return _serializar_margens_preco(config)


@router.put("/margens-preco", response_model=EmpresaConfigMargensPrecoResponse)
@require_permission("produtos.editar")
def update_margens_preco(
    config_data: EmpresaConfigMargensPrecoUpdate,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session),
):
    """Atualiza as sugestões sem alterar custos ou preços de produtos."""
    _, tenant_id = user_and_tenant
    config = (
        db.query(EmpresaConfigGeral)
        .filter(EmpresaConfigGeral.tenant_id == tenant_id)
        .first()
    )

    if not config:
        config = EmpresaConfigGeral(tenant_id=tenant_id)
        db.add(config)

    config.margem_preco_sugestao_1 = config_data.margem_preco_sugestao_1
    config.margem_preco_sugestao_2 = config_data.margem_preco_sugestao_2
    db.commit()
    db.refresh(config)

    logger.info("Margens sugeridas de preço atualizadas para tenant %s", tenant_id)
    return _serializar_margens_preco(config)


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
            margem_preco_sugestao_1=30.0,
            margem_preco_sugestao_2=34.0,
            mensagem_venda_saudavel="✅ Venda Saudável! Margem excelente.",
            mensagem_venda_alerta="⚠️ ATENÇÃO: Margem reduzida! Revisar preço.",
            mensagem_venda_critica="🚨 CRÍTICO: Margem muito baixa! Venda com prejuízo!",
            caixa_compartilhado=False,
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

    if config_data.caixa_compartilhado:
        _validar_ativacao_caixa_compartilhado(db, tenant_id)

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
        .with_for_update()
        .first()
    )

    if not config:
        # Cria se não existir
        config = EmpresaConfigGeral(tenant_id=tenant_id)
        db.add(config)

    # Atualiza apenas campos fornecidos
    update_data = config_data.model_dump(exclude_unset=True)
    if update_data.get("caixa_compartilhado") and not bool(
        getattr(config, "caixa_compartilhado", False)
    ):
        _validar_ativacao_caixa_compartilhado(db, tenant_id)
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
