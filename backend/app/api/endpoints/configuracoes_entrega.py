"""
Endpoints para ConfiguracaoEntrega
Sprint 1 BLOCO 3 - Configuração Global de Entregas
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.models import ConfiguracaoEntrega, Tenant
from app.schemas.configuracao_entrega import (
    ConfiguracaoEntregaResponse,
    ConfiguracaoEntregaUpdate,
)

router = APIRouter(prefix="/configuracoes/entregas", tags=["Configurações - Entregas"])


@router.get("", response_model=ConfiguracaoEntregaResponse)
def get_configuracao_entrega(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna a configuração de entrega do tenant atual.
    Cria automaticamente se não existir.
    
    ✅ Multi-tenant: usa tenant_id do contexto
    ✅ Idempotente: cria se não existir
    """
    current_user, tenant_id = user_and_tenant
    
    # Verifica se tenant existe
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # Busca ou cria configuração
    config = (
        db.query(ConfiguracaoEntrega)
        .filter(ConfiguracaoEntrega.tenant_id == tenant_id)
        .first()
    )

    if not config:
        # Cria configuração padrão
        config = ConfiguracaoEntrega(
            user_id=current_user.id,
            tenant_id=tenant_id,
            entregador_padrao_id=None,
            logradouro=None,
            cep=None,
            numero=None,
            complemento=None,
            bairro=None,
            cidade=None,
            estado=None
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


@router.put("", response_model=ConfiguracaoEntregaResponse)
def update_configuracao_entrega(
    payload: ConfiguracaoEntregaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualiza a configuração de entrega do tenant atual.
    
    ✅ Multi-tenant: usa tenant_id do contexto
    ✅ Idempotente: cria se não existir
    ✅ Parcial: aceita campos opcionais
    """
    current_user, tenant_id = user_and_tenant
    
    # Verifica se tenant existe
    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    # Busca ou cria configuração
    config = (
        db.query(ConfiguracaoEntrega)
        .filter(ConfiguracaoEntrega.tenant_id == tenant_id)
        .first()
    )

    if not config:
        # Cria se não existe
        config = ConfiguracaoEntrega(
            user_id=current_user.id,
            tenant_id=tenant_id
        )
        db.add(config)

    # Atualiza apenas campos fornecidos
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)

    return config
