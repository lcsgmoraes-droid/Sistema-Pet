"""
WhatsApp Configuration Endpoints

CRUD para configuração WhatsApp por tenant.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.db import get_session as get_db
from app.auth import get_current_user
from app.models import User
from app.whatsapp.models import TenantWhatsAppConfig
from app.whatsapp.schemas import (
    TenantWhatsAppConfigBase,
    TenantWhatsAppConfigCreate,
    TenantWhatsAppConfigUpdate,
    TenantWhatsAppConfigResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp/config", tags=["WhatsApp Config"])


# ============================================================================
# GET CONFIG
# ============================================================================

@router.get("", response_model=Optional[TenantWhatsAppConfigResponse])
def get_whatsapp_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Busca configuração WhatsApp do tenant.
    """
    try:
        logger.info(f"📡 GET /api/whatsapp/config - tenant={current_user.tenant_id}")
        
        config = db.query(TenantWhatsAppConfig).filter(
            TenantWhatsAppConfig.tenant_id == current_user.tenant_id
        ).first()
        
        if config:
            logger.info(f"✅ Config encontrada: {config.id}")
        else:
            logger.info("ℹ️ Nenhuma config encontrada")
        
        return config
    except Exception as e:
        logger.error(f"❌ Erro no GET config: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao buscar config: {str(e)}")


# ============================================================================
# CREATE CONFIG
# ============================================================================

@router.post("", response_model=TenantWhatsAppConfigResponse)
def create_whatsapp_config(
    data: TenantWhatsAppConfigBase,  # Alterado de Create para Base (não precisa tenant_id)
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cria configuração WhatsApp para o tenant.
    Tenant ID é obtido automaticamente do usuário logado.
    """
    # Verificar se já existe
    existing = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == current_user.tenant_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Configuração já existe. Use PUT para atualizar.")
    
    # Criar
    config = TenantWhatsAppConfig(
        tenant_id=current_user.tenant_id,
        **data.model_dump()
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    logger.info(f"✅ Config WhatsApp criada: tenant={current_user.tenant_id}")
    
    return config


# ============================================================================
# UPDATE CONFIG
# ============================================================================

@router.put("", response_model=TenantWhatsAppConfigResponse)
def update_whatsapp_config(
    data: TenantWhatsAppConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atualiza configuração WhatsApp do tenant.
    """
    config = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == current_user.tenant_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    
    # Atualizar campos fornecidos
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    logger.info(f"✅ Config WhatsApp atualizada: tenant={current_user.tenant_id}")
    
    return config


# ============================================================================
# DELETE CONFIG
# ============================================================================

@router.delete("")
def delete_whatsapp_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deleta configuração WhatsApp do tenant.
    """
    config = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == current_user.tenant_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    
    db.delete(config)
    db.commit()
    
    logger.info(f"🗑️ Config WhatsApp deletada: tenant={current_user.tenant_id}")
    
    return {"message": "Configuração deletada com sucesso"}


# ============================================================================
# TEST WEBHOOK (Desenvolvimento)
# ============================================================================

@router.post("/test-webhook")
async def test_webhook_connection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Testa conexão com 360dialog.
    
    Envia mensagem de teste para o número configurado.
    """
    config = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == current_user.tenant_id
    ).first()
    
    if not config or not config.api_key:
        raise HTTPException(status_code=400, detail="API key não configurada")
    
    try:
        from app.whatsapp.sender import Dialog360Client
        
        client = Dialog360Client(api_key=config.api_key)
        
        # Enviar mensagem de teste (para o próprio número)
        if not config.phone_number:
            raise HTTPException(status_code=400, detail="Phone number não configurado")
        
        response = await client.send_text_message(
            to=config.phone_number,
            message="🧪 Teste de conexão WhatsApp - Sistema Pet Shop Pro"
        )
        
        return {
            "status": "success",
            "message": "Mensagem de teste enviada",
            "whatsapp_response": response
        }
        
    except Exception as e:
        logger.error(f"Erro no teste: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao testar conexão: {str(e)}")


# ============================================================================
# ESTATÍSTICAS
# ============================================================================

@router.get("/stats")
def get_whatsapp_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Estatísticas de uso do WhatsApp.
    """
    from app.whatsapp.models import WhatsAppSession, WhatsAppMessage, WhatsAppMetric
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    tenant_id = current_user.tenant_id
    hoje = datetime.now().date()
    
    # Sessões ativas
    sessoes_ativas = db.query(WhatsAppSession).filter(
        WhatsAppSession.tenant_id == tenant_id,
        WhatsAppSession.status.in_(["bot", "human", "waiting_human"])
    ).count()
    
    # Mensagens hoje
    mensagens_hoje = db.query(WhatsAppMessage).filter(
        WhatsAppMessage.tenant_id == tenant_id,
        func.date(WhatsAppMessage.created_at) == hoje
    ).count()
    
    # Total sessões
    total_sessoes = db.query(WhatsAppSession).filter(
        WhatsAppSession.tenant_id == tenant_id
    ).count()
    
    # Tokens usados hoje
    tokens_hoje = db.query(func.sum(WhatsAppMetric.value)).filter(
        WhatsAppMetric.tenant_id == tenant_id,
        WhatsAppMetric.metric_type == "tokens_used",
        func.date(WhatsAppMetric.timestamp) == hoje
    ).scalar() or 0
    
    return {
        "sessoes_ativas": sessoes_ativas,
        "mensagens_hoje": mensagens_hoje,
        "total_sessoes": total_sessoes,
        "tokens_usados_hoje": int(tokens_hoje),
        "custo_estimado_usd": round(tokens_hoje * 0.0001 / 1000, 4)  # Estimativa GPT-4o-mini
    }
