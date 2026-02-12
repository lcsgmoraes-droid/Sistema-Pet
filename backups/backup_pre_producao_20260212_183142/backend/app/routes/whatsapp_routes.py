"""
Rotas WhatsApp - Configuração, Webhook, Testes
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User

from app.whatsapp.schemas import (
    TenantWhatsAppConfigCreate,
    TenantWhatsAppConfigUpdate,
    TenantWhatsAppConfigResponse,
    WhatsAppStatsResponse
)
from app.whatsapp.models import TenantWhatsAppConfig
from app.whatsapp.tools import ToolExecutor, TOOLS_DEFINITIONS
from app.whatsapp.ai_service import get_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

@router.get("/config", response_model=TenantWhatsAppConfigResponse)
async def get_config(
    current_user: User = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Obtém configuração WhatsApp do tenant"""
    config = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == current_user.tenant_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    
    return config


# ============================================================================
# MENSAGENS DO CLIENTE
# ============================================================================

@router.get("/clientes/{cliente_id}/whatsapp/ultimas")
async def get_ultimas_mensagens_cliente(
    cliente_id: int,
    limit: int = 5,
    user_and_tenant = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Obtém as últimas mensagens WhatsApp de um cliente específico
    
    Args:
        cliente_id: ID do cliente
        limit: Quantidade máxima de mensagens a retornar (padrão: 5)
    
    Returns:
        Lista com as últimas mensagens do cliente
    """
    try:
        from app.ia.aba6_aba9_models import MensagemWhatsApp, ConversaWhatsApp
        from app.models import Cliente
        
        current_user, tenant_id = user_and_tenant
        
        # Verificar se cliente existe e pertence ao tenant
        cliente = db.query(Cliente).filter(
            Cliente.id == cliente_id,
            Cliente.tenant_id == tenant_id
        ).first()
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        # Buscar conversas do cliente
        conversas = db.query(ConversaWhatsApp).filter(
            ConversaWhatsApp.cliente_id == cliente_id,
            ConversaWhatsApp.tenant_id == tenant_id
        ).all()
        
        if not conversas:
            # Cliente existe mas não tem conversas, retornar lista vazia
            return []
        
        conversa_ids = [c.id for c in conversas]
        
        # Buscar últimas mensagens dessas conversas
        mensagens = db.query(MensagemWhatsApp).filter(
            MensagemWhatsApp.conversa_id.in_(conversa_ids),
            MensagemWhatsApp.tenant_id == tenant_id
        ).order_by(
            MensagemWhatsApp.data_hora.desc()
        ).limit(limit).all()
        
        # Formatar resposta
        resultado = []
        for msg in mensagens:
            resultado.append({
                'id': msg.id,
                'conversa_id': msg.conversa_id,
                'remetente': msg.remetente,
                'tipo': msg.tipo,
                'mensagem': msg.mensagem,
                'intencao_detectada': msg.intencao_detectada,
                'confianca_intencao': msg.confianca_intencao,
                'processada_por_ia': msg.processada_por_ia,
                'resposta_ia': msg.resposta_ia,
                'data_hora': msg.data_hora.isoformat() if msg.data_hora else None
            })
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar mensagens do cliente {cliente_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar mensagens: {str(e)}"
        )


@router.post("/config", response_model=TenantWhatsAppConfigResponse, status_code=201)
async def create_config(
    config_data: TenantWhatsAppConfigCreate,
    current_user: User = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Cria configuração WhatsApp"""
    
    # Verificar se já existe
    existing = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == current_user.tenant_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Configuração já existe. Use PUT para atualizar."
        )
    
    # Criar nova configuração
    new_config = TenantWhatsAppConfig(
        tenant_id=current_user.tenant_id,
        **config_data.model_dump()
    )
    
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    return new_config


@router.put("/config", response_model=TenantWhatsAppConfigResponse)
async def update_config(
    config_data: TenantWhatsAppConfigUpdate,
    current_user: User = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Atualiza configuração WhatsApp"""
    
    config = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == current_user.tenant_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    
    # Atualizar campos
    for field, value in config_data.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    return config


@router.delete("/config", status_code=204)
async def delete_config(
    current_user: User = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Remove configuração WhatsApp"""
    
    config = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == current_user.tenant_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    
    db.delete(config)
    db.commit()


@router.get("/config/stats", response_model=WhatsAppStatsResponse)
async def get_stats(
    current_user: User = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """Obtém estatísticas de uso"""
    # TODO: Implementar estatísticas reais
    return {
        "total_sessions": 0,
        "active_sessions": 0,
        "total_messages": 0,
        "messages_today": 0,
        "avg_response_time": 0.0,
        "ai_usage_percentage": 0.0
    }


# ============================================================================
# WEBHOOK (Recebe mensagens do provedor)
# ============================================================================

@router.post("/webhook")
@router.get("/webhook")
async def webhook(
    hub_mode: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
    hub_challenge: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """
    Webhook para receber mensagens do WhatsApp
    
    GET: Verificação do webhook (360dialog/Twilio)
    POST: Recebe mensagens
    """
    
    # Verificação do webhook (GET)
    if hub_mode and hub_verify_token:
        if hub_mode == "subscribe" and hub_verify_token == "meu_token_secreto":
            return int(hub_challenge)
        else:
            raise HTTPException(status_code=403, detail="Token inválido")
    
    # Processar mensagem (POST)
    # TODO: Implementar processamento de webhook
    return {"status": "ok"}


# ============================================================================
# TESTE DE TOOLS
# ============================================================================

@router.post("/test-tool")
async def test_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    current_user: User = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Testa execução de uma tool específica
    
    Exemplo:
    ```json
    {
        "tool_name": "buscar_produtos",
        "arguments": {
            "query": "ração golden",
            "limite": 3
        }
    }
    ```
    """
    
    try:
        # Executar tool
        executor = ToolExecutor(db, current_user.tenant_id)
        result = executor.execute_tool(tool_name, arguments)
        
        return {
            "success": True,
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Erro ao testar tool {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_tools():
    """Lista todas as tools disponíveis para a IA"""
    
    tools = []
    for tool_def in TOOLS_DEFINITIONS:
        func = tool_def["function"]
        tools.append({
            "name": func["name"],
            "description": func["description"],
            "parameters": func["parameters"]["properties"].keys()
        })
    
    return {
        "total": len(tools),
        "tools": tools
    }


# ============================================================================
# TESTE DE MENSAGEM (Simula conversa)
# ============================================================================

@router.post("/test-message")
async def test_message(
    message: str,
    phone_number: str = "5511999999999",
    current_user: User = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Testa processamento completo de uma mensagem
    
    Simula recebimento de mensagem e retorna resposta da IA
    """
    
    try:
        # Processar mensagem
        ai_service = get_ai_service(db, current_user.tenant_id)
        result = await ai_service.process_message(
            message=message,
            phone_number=phone_number
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Erro ao processar mensagem de teste: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TESTE DE CONVERSAÇÃO (Múltiplas mensagens)
# ============================================================================

@router.post("/test-conversation")
async def test_conversation(
    messages: list[str],
    phone_number: str = "5511999999999",
    current_user: User = Depends(get_current_user_and_tenant),
    db: Session = Depends(get_session)
):
    """
    Testa uma conversação completa (múltiplas mensagens)
    
    Exemplo:
    ```json
    {
        "messages": [
            "Olá!",
            "Tem ração Golden?",
            "Quero comprar 2 pacotes"
        ]
    }
    ```
    """
    
    try:
        ai_service = get_ai_service(db, current_user.tenant_id)
        
        conversation = []
        session_id = None
        
        for msg in messages:
            result = await ai_service.process_message(
                message=msg,
                phone_number=phone_number,
                session_id=session_id
            )
            
            # Capturar session_id para próximas mensagens
            if not session_id and "session_id" in result:
                session_id = result["session_id"]
            
            conversation.append({
                "user": msg,
                "assistant": result.get("response"),
                "intent": result.get("intent"),
                "tool_calls": result.get("metadata", {}).get("tool_calls", 0)
            })
        
        return {
            "success": True,
            "conversation": conversation,
            "total_messages": len(messages)
        }
    
    except Exception as e:
        logger.error(f"Erro ao testar conversação: {e}")
        raise HTTPException(status_code=500, detail=str(e))
