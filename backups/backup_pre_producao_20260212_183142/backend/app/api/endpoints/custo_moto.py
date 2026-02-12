"""
Endpoints para Configuração de Custos da Moto
ETAPA 8 - Custos da Moto
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.models_custo_moto import ConfiguracaoCustoMoto
from app.schemas.custo_moto import (
    ConfiguracaoCustoMotoCreate,
    ConfiguracaoCustoMotoUpdate,
    ConfiguracaoCustoMotoResponse,
    SimulacaoCustoResponse
)
from app.services.custo_moto_service import (
    obter_configuracao_moto,
    simular_custo_por_km
)

router = APIRouter(prefix="/custos-moto", tags=["Custos - Moto da Loja"])


@router.get("/", response_model=ConfiguracaoCustoMotoResponse)
def obter_configuracao(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Obtém a configuração de custos da moto do tenant.
    Se não existir, retorna uma configuração padrão.
    """
    user, tenant_id = user_and_tenant
    
    config = obter_configuracao_moto(db, tenant_id)
    
    if not config:
        # Retornar configuração padrão
        raise HTTPException(
            status_code=404,
            detail="Configuração não encontrada. Use POST para criar."
        )
    
    return config


@router.post("/", response_model=ConfiguracaoCustoMotoResponse)
def criar_configuracao(
    payload: ConfiguracaoCustoMotoCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Cria a configuração de custos da moto.
    Apenas uma configuração por tenant.
    """
    user, tenant_id = user_and_tenant
    
    # Verificar se já existe
    config_existente = obter_configuracao_moto(db, tenant_id)
    if config_existente:
        raise HTTPException(
            status_code=400,
            detail="Configuração já existe. Use PUT para atualizar."
        )
    
    config = ConfiguracaoCustoMoto(
        tenant_id=tenant_id,
        **payload.model_dump()
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return config


@router.put("/", response_model=ConfiguracaoCustoMotoResponse)
def atualizar_configuracao(
    payload: ConfiguracaoCustoMotoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Atualiza a configuração de custos da moto.
    """
    user, tenant_id = user_and_tenant
    
    config = obter_configuracao_moto(db, tenant_id)
    
    if not config:
        raise HTTPException(
            status_code=404,
            detail="Configuração não encontrada. Use POST para criar."
        )
    
    # Atualizar campos
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    return config


@router.get("/simular", response_model=SimulacaoCustoResponse)
def simular_custo(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Simula o custo por KM com base na configuração atual.
    Retorna breakdown e exemplos para diferentes distâncias.
    """
    user, tenant_id = user_and_tenant
    
    config = obter_configuracao_moto(db, tenant_id)
    
    if not config:
        raise HTTPException(
            status_code=404,
            detail="Configure os custos da moto antes de simular."
        )
    
    resultado = simular_custo_por_km(config)
    
    return resultado
