"""
WhatsApp Message Sender (360dialog)

Envia mensagens via API do 360dialog.
Trata erros, retries, registra no banco.
"""
import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.whatsapp.models import TenantWhatsAppConfig, WhatsAppSession, WhatsAppMessage

logger = logging.getLogger(__name__)


# ============================================================================
# CLIENT 360DIALOG
# ============================================================================

class Dialog360Client:
    """
    Cliente HTTP para 360dialog API.
    
    Docs: https://docs.360dialog.com/whatsapp-api/whatsapp-api
    """
    
    BASE_URL = "https://waba.360dialog.io/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "D360-API-KEY": api_key,
            "Content-Type": "application/json"
        }
    
    async def send_text_message(
        self,
        to: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Envia mensagem de texto.
        
        Args:
            to: Número com código do país (ex: 5511999999999)
            message: Texto da mensagem
            
        Returns:
            Response da API com message_id
        """
        payload = {
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/messages",
                headers=self.headers,
                json=payload
            )
            
            response.raise_for_status()
            return response.json()
    
    async def send_image_message(
        self,
        to: str,
        image_url: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia imagem com legenda opcional.
        
        Args:
            to: Número com código do país
            image_url: URL pública da imagem
            caption: Legenda (opcional, máx 1024 caracteres)
        """
        payload = {
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": {
                "link": image_url
            }
        }
        
        if caption:
            payload["image"]["caption"] = caption[:1024]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/messages",
                headers=self.headers,
                json=payload
            )
            
            response.raise_for_status()
            return response.json()
    
    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "pt_BR",
        parameters: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Envia template aprovado (para iniciar conversa fora da janela 24h).
        
        Args:
            to: Número com código do país
            template_name: Nome do template aprovado pela Meta
            language_code: Código do idioma (pt_BR, en_US, etc)
            parameters: Lista de parâmetros do template
        """
        payload = {
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        if parameters:
            payload["template"]["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(p)} for p in parameters
                    ]
                }
            ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/messages",
                headers=self.headers,
                json=payload
            )
            
            response.raise_for_status()
            return response.json()


# ============================================================================
# SEND MESSAGE (HIGH-LEVEL)
# ============================================================================

async def send_whatsapp_message(
    db: Session,
    tenant_id: str,
    session_id: str,
    message: str,
    message_type: str = "text",
    image_url: Optional[str] = None,
    sent_by_user_id: Optional[str] = None
) -> Optional[WhatsAppMessage]:
    """
    Envia mensagem via WhatsApp e registra no banco.
    
    Args:
        db: Database session
        tenant_id: ID do tenant
        session_id: ID da sessão
        message: Conteúdo da mensagem
        message_type: "text", "image", "notificacao_sistema"
        image_url: URL da imagem (se type=image)
        sent_by_user_id: ID do usuário (se enviada por humano)
        
    Returns:
        WhatsAppMessage criada ou None se falhar
    """
    try:
        # 1. Buscar config e sessão
        config = db.query(TenantWhatsAppConfig).filter(
            TenantWhatsAppConfig.tenant_id == tenant_id
        ).first()
        
        if not config or not config.api_key:
            logger.error(f"Tenant {tenant_id} sem API key configurada")
            return None
        
        session = db.query(WhatsAppSession).get(session_id)
        if not session:
            logger.error(f"Sessão {session_id} não encontrada")
            return None
        
        # 2. Enviar via API
        client = Dialog360Client(api_key=config.api_key)
        
        if message_type == "image" and image_url:
            response = await client.send_image_message(
                to=session.phone_number,
                image_url=image_url,
                caption=message
            )
        else:
            response = await client.send_text_message(
                to=session.phone_number,
                message=message
            )
        
        # 3. Extrair message_id da resposta
        whatsapp_message_id = response.get("messages", [{}])[0].get("id")
        
        # 4. Registrar no banco
        db_message = WhatsAppMessage(
            session_id=session_id,
            tenant_id=tenant_id,
            tipo="enviada",
            conteudo=message,
            whatsapp_message_id=whatsapp_message_id,
            sent_by_user_id=sent_by_user_id,
            created_at=datetime.utcnow()
        )
        
        db.add(db_message)
        
        # 5. Atualizar sessão
        session.message_count += 1
        session.last_message_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_message)
        
        logger.info(f"✅ Mensagem enviada: {whatsapp_message_id}")
        
        return db_message
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Erro HTTP ao enviar mensagem: {e.response.status_code} - {e.response.text}")
        db.rollback()
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem: {e}")
        db.rollback()
        return None


# ============================================================================
# SEND NOTIFICACAO ENTREGA (Integração com sistema existente)
# ============================================================================

async def send_notificacao_entrega(
    db: Session,
    tenant_id: str,
    cliente_phone: str,
    mensagem: str
) -> bool:
    """
    Envia notificação de entrega (integra com sistema existente).
    
    Usado por: app/services/notificacao_entrega_service.py
    
    Args:
        db: Database session
        tenant_id: ID do tenant
        cliente_phone: Telefone do cliente
        mensagem: Mensagem formatada pelo sistema de entregas
        
    Returns:
        True se enviado com sucesso
    """
    try:
        # 1. Verificar se WhatsApp está habilitado
        config = db.query(TenantWhatsAppConfig).filter(
            TenantWhatsAppConfig.tenant_id == tenant_id,
            TenantWhatsAppConfig.notificacoes_entrega_enabled == True
        ).first()
        
        if not config:
            logger.info(f"Notificações de entrega desabilitadas: tenant={tenant_id}")
            return False
        
        # 2. Buscar/criar sessão
        from app.whatsapp.webhook import get_or_create_session, normalize_phone
        
        phone_normalized = normalize_phone(cliente_phone)
        session = get_or_create_session(db, tenant_id, phone_normalized)
        
        # 3. Enviar mensagem
        result = await send_whatsapp_message(
            db=db,
            tenant_id=tenant_id,
            session_id=session.id,
            message=mensagem,
            message_type="notificacao_sistema"
        )
        
        return result is not None
        
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de entrega: {e}")
        return False


# ============================================================================
# BULK SEND (Para campanhas futuras)
# ============================================================================

async def send_bulk_messages(
    db: Session,
    tenant_id: str,
    recipients: list[str],
    message: str,
    template_name: Optional[str] = None
) -> Dict[str, int]:
    """
    Envia mensagem em massa (campanha).
    
    ⚠️ Requer template aprovado para clientes fora da janela 24h.
    
    Args:
        recipients: Lista de telefones
        message: Mensagem ou parâmetros do template
        template_name: Nome do template (se usar)
        
    Returns:
        {"success": N, "failed": M}
    """
    config = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == tenant_id
    ).first()
    
    if not config:
        return {"success": 0, "failed": len(recipients)}
    
    client = Dialog360Client(api_key=config.api_key)
    
    success = 0
    failed = 0
    
    for phone in recipients:
        try:
            if template_name:
                await client.send_template_message(
                    to=phone,
                    template_name=template_name,
                    parameters=[message]
                )
            else:
                await client.send_text_message(
                    to=phone,
                    message=message
                )
            
            success += 1
            
        except Exception as e:
            logger.error(f"Erro ao enviar para {phone}: {e}")
            failed += 1
    
    logger.info(f"📤 Bulk send: {success} enviados, {failed} falharam")
    
    return {"success": success, "failed": failed}
