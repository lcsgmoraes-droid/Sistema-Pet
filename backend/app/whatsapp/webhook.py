"""
WhatsApp Webhook Receiver (360dialog)

Recebe mensagens do 360dialog via webhook.
Valida assinatura, identifica tenant, enfileira processamento.

Endpoints:
- POST /webhook/whatsapp/{tenant_id} - Recebe mensagens
- GET /webhook/whatsapp/{tenant_id} - Validação inicial (Meta)
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session
import hashlib
import hmac
import logging
from typing import Dict, Any
from datetime import datetime

from app.db import get_session as get_db
from app.whatsapp.models import TenantWhatsAppConfig, WhatsAppSession, WhatsAppMessage
from app.whatsapp.schemas import Webhook360DialogPayload
from app.models import Cliente

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook/whatsapp", tags=["WhatsApp Webhook"])


# ============================================================================
# WEBHOOK VALIDATION (360dialog)
# ============================================================================

def validate_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """
    Valida assinatura do webhook 360dialog.
    
    360dialog usa HMAC-SHA256 com o webhook_secret.
    """
    try:
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Erro ao validar assinatura: {e}")
        return False


# ============================================================================
# GET WEBHOOK (Verificação Meta)
# ============================================================================

@router.get("/{tenant_id}")
async def webhook_verification(
    tenant_id: str,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    db: Session = Depends(get_db)
):
    """
    GET webhook para verificação inicial da Meta.
    
    Meta/360dialog envia GET com:
    - hub.mode=subscribe
    - hub.challenge=random_string
    - hub.verify_token=seu_token
    
    Você deve retornar hub.challenge se verify_token estiver correto.
    """
    logger.info(f"Verificação webhook recebida: tenant={tenant_id}, mode={hub_mode}")
    
    # Buscar config do tenant
    config = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == tenant_id
    ).first()
    
    if not config or not config.webhook_secret:
        logger.warning(f"Tenant {tenant_id} sem configuração WhatsApp")
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    
    # Validar verify token
    if hub_mode == "subscribe" and hub_verify_token == config.webhook_secret:
        logger.info(f"✅ Webhook verificado com sucesso: tenant={tenant_id}")
        return int(hub_challenge)  # Meta espera número
    
    logger.warning(f"❌ Falha na verificação: token inválido")
    raise HTTPException(status_code=403, detail="Verificação falhou")


# ============================================================================
# POST WEBHOOK (Recebe Mensagens)
# ============================================================================

@router.post("/{tenant_id}")
async def receive_webhook(
    tenant_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    POST webhook para receber mensagens do 360dialog.
    
    Fluxo:
    1. Valida assinatura (segurança)
    2. Parseia payload
    3. Identifica cliente
    4. Enfileira processamento em background
    5. Retorna 200 OK imediatamente
    """
    # 1. Buscar config do tenant
    config = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == tenant_id
    ).first()
    
    if not config:
        logger.warning(f"Tenant {tenant_id} sem configuração")
        raise HTTPException(status_code=404, detail="Tenant não configurado")
    
    # 2. Validar assinatura (se configurada)
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    if config.webhook_secret and signature:
        # Remover prefixo "sha256=" se existir
        signature = signature.replace("sha256=", "")
        
        if not validate_webhook_signature(body, signature, config.webhook_secret):
            logger.warning(f"❌ Assinatura inválida: tenant={tenant_id}")
            raise HTTPException(status_code=403, detail="Assinatura inválida")
    
    # 3. Parsear payload JSON
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Erro ao parsear payload: {e}")
        raise HTTPException(status_code=400, detail="Payload inválido")
    
    # 4. Processar mensagens
    try:
        processed_count = await process_webhook_payload(
            tenant_id=tenant_id,
            payload=payload,
            background_tasks=background_tasks,
            db=db
        )
        
        logger.info(f"✅ Webhook processado: {processed_count} mensagens")
        
        # Retornar 200 OK rapidamente (WhatsApp espera resposta em <500ms)
        return {"status": "received", "messages_processed": processed_count}
        
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        # Retornar 200 mesmo com erro interno (para não reenviar)
        return {"status": "error", "message": str(e)}


# ============================================================================
# PROCESSAMENTO DO PAYLOAD
# ============================================================================

async def process_webhook_payload(
    tenant_id: str,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session
) -> int:
    """
    Processa payload do 360dialog.
    
    Estrutura 360dialog:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "account_id",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {...},
                    "messages": [
                        {
                            "from": "5511999999999",
                            "id": "wamid.xxx",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Olá"}
                        }
                    ]
                },
                "field": "messages"
            }]
        }]
    }
    """
    processed = 0
    
    # Iterar entries
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            
            # Processar cada mensagem
            for msg in messages:
                try:
                    # Extrair dados
                    phone = msg.get("from")
                    whatsapp_msg_id = msg.get("id")
                    msg_type = msg.get("type")
                    timestamp = msg.get("timestamp")
                    
                    # Suportar apenas texto por enquanto
                    if msg_type != "text":
                        logger.info(f"Tipo {msg_type} não suportado (ainda)")
                        continue
                    
                    text_content = msg.get("text", {}).get("body", "")
                    
                    if not phone or not text_content:
                        logger.warning("Mensagem sem phone ou conteúdo")
                        continue
                    
                    # Enfileirar processamento
                    background_tasks.add_task(
                        process_incoming_message,
                        tenant_id=tenant_id,
                        phone=phone,
                        message_content=text_content,
                        whatsapp_msg_id=whatsapp_msg_id,
                        db=db
                    )
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem individual: {e}")
                    continue
    
    return processed


# ============================================================================
# PROCESSAR MENSAGEM INDIVIDUAL
# ============================================================================

async def process_incoming_message(
    tenant_id: str,
    phone: str,
    message_content: str,
    whatsapp_msg_id: str,
    db: Session
):
    """
    Processa mensagem individual (roda em background).
    
    Fluxo:
    1. Normalizar telefone
    2. Buscar/criar sessão
    3. Salvar mensagem recebida
    4. [PRÓXIMO SPRINT] Processar com IA
    5. [PRÓXIMO SPRINT] Enviar resposta
    """
    try:
        logger.info(f"📨 Processando mensagem: tenant={tenant_id}, phone={phone}")
        
        # 1. Normalizar telefone (remover caracteres especiais)
        phone_normalized = normalize_phone(phone)
        
        # 2. Buscar ou criar sessão
        session = get_or_create_session(
            db=db,
            tenant_id=tenant_id,
            phone=phone_normalized
        )
        
        # 3. Salvar mensagem recebida
        message = WhatsAppMessage(
            session_id=session.id,
            tenant_id=tenant_id,
            tipo="recebida",
            conteudo=message_content,
            whatsapp_message_id=whatsapp_msg_id,
            created_at=datetime.utcnow()
        )
        
        db.add(message)
        
        # Atualizar sessão
        session.message_count += 1
        session.last_message_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"✅ Mensagem salva: session={session.id}")
        
        # 4. Processar com IA
        try:
            from app.whatsapp.processor import MessageProcessor
            
            processor = MessageProcessor(db=db, tenant_id=tenant_id)
            result = await processor.process_message(
                session_id=session.id,
                message_id=message.id,
                message_content=message_content
            )
            
            logger.info(f"✅ Processamento concluído: {result.get('action')}")
            
        except Exception as proc_error:
            logger.error(f"Erro no processor (não-bloqueante): {proc_error}")
            # Não falha se processor der erro
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar mensagem: {e}")
        db.rollback()
        raise


# ============================================================================
# HELPERS
# ============================================================================

def normalize_phone(phone: str) -> str:
    """
    Normaliza identificador de telefone/chat do WhatsApp.

    - Para formato @lid (novo identificador interno do WhatsApp):
      mantém o sufixo @lid, ex: "266915104710838@lid"
    - Para demais formatos (@c.us, etc.): retorna apenas dígitos.
    """
    import re
    if "@lid" in phone:
        digits = re.sub(r'[^\d]', '', phone.split("@")[0])
        return f"{digits}@lid"
    return re.sub(r'[^\d]', '', phone)


def get_or_create_session(
    db: Session,
    tenant_id: str,
    phone: str
) -> WhatsAppSession:
    """
    Busca sessão ativa ou cria nova.
    
    Sessão ativa = status 'bot' ou 'human' (não 'closed')
    """
    # Buscar sessão ativa
    session = db.query(WhatsAppSession).filter(
        WhatsAppSession.tenant_id == tenant_id,
        WhatsAppSession.phone_number == phone,
        WhatsAppSession.status.in_(["bot", "human", "waiting_human"])
    ).order_by(WhatsAppSession.last_message_at.desc()).first()
    
    if session:
        return session
    
    # Buscar cliente (se identificado) sem carregar todas as colunas de `clientes`,
    # para evitar quebrar em bancos legados com schema parcial.
    cliente_id = None
    try:
        telefone_sufixo = phone[-8:] if phone else ""
        cliente_row = db.query(Cliente.id).filter(
            Cliente.tenant_id == tenant_id,
            (
                (Cliente.celular == phone) |
                (Cliente.telefone == phone) |
                (Cliente.celular.ilike(f"%{telefone_sufixo}%")) |
                (Cliente.telefone.ilike(f"%{telefone_sufixo}%"))
            )
        ).first()
        if cliente_row:
            cliente_id = cliente_row[0] if isinstance(cliente_row, tuple) else cliente_row
    except Exception as cliente_lookup_error:
        logger.warning(f"Falha ao identificar cliente por telefone: {cliente_lookup_error}")
        cliente_id = None
    
    # Criar nova sessão
    session = WhatsAppSession(
        tenant_id=tenant_id,
        cliente_id=cliente_id,
        phone_number=phone,
        status="bot",
        started_at=datetime.utcnow(),
        last_message_at=datetime.utcnow()
    )
    
    db.add(session)
    db.flush()
    
    logger.info(f"🆕 Nova sessão criada: {session.id}")
    
    return session
