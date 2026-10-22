"""
WebSocket Router para FastAPI
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import logging
import json
import uuid

from app.db import get_session as get_db
from app.whatsapp.websocket import manager
from app.auth.core import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.security.module_access import tenant_has_active_module
from app.whatsapp.models_handoff import WhatsAppAgent
from app.whatsapp.tenant_context import whatsapp_tenant_context

router = APIRouter()
logger = logging.getLogger(__name__)


async def autorizar_conexao_agente(
    token: str, agent_id: str, db: Session
) -> Optional[str]:
    """Valida quem esta se conectando e devolve o tenant_id, ou None se recusar.

    Regras: token valido, loja identificada, modulo WhatsApp contratado e o
    atendente informado pertencer a ESTE usuario e a ESTA loja. Qualquer falha
    recusa a conexao (sem detalhes para quem tenta).
    """
    try:
        agente_uuid = uuid.UUID(str(agent_id))
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        usuario = get_current_user(credentials=credentials, session=db)
        usuario, tenant_id = await get_current_user_and_tenant(
            credentials=credentials, user=usuario, db=db
        )
        if not tenant_id:
            return None
        if not tenant_has_active_module(db, str(tenant_id), "whatsapp"):
            return None
        with whatsapp_tenant_context(str(tenant_id)):
            agente = (
                db.query(WhatsAppAgent)
                .filter(
                    WhatsAppAgent.id == agente_uuid,
                    WhatsAppAgent.tenant_id == tenant_id,
                    WhatsAppAgent.user_id == usuario.id,
                )
                .first()
            )
        return str(tenant_id) if agente else None
    except Exception:
        return None


@router.websocket("/ws/whatsapp/{agent_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    agent_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint para agentes

    URL: ws://localhost:8000/ws/whatsapp/{agent_id}?token={jwt_token}

    Events emitted from server:
    - connected: Confirmação de conexão
    - new_handoff: Novo handoff criado
    - handoff_assigned: Handoff atribuído
    - handoff_resolved: Handoff resolvido
    - new_message: Nova mensagem na conversa
    - agent_status_change: Status de agente mudou
    - typing_indicator: Cliente está digitando

    Events received from client:
    - join_agent_room: Cliente quer receber notificações
    - leave_agent_room: Cliente quer parar de receber
    - typing: Agente está digitando
    """

    tenant_id = await autorizar_conexao_agente(token, agent_id, db)
    if not tenant_id:
        logger.error("WebSocket auth failed")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    logger.info("WebSocket agent connection authenticated")

    await manager.connect(websocket, agent_id, tenant_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            event = message.get("event")

            # Handle client events
            if event == "join_agent_room":
                logger.info("WebSocket agent joined room")
                # Already connected, nothing to do

            elif event == "leave_agent_room":
                logger.info("WebSocket agent left room")
                manager.disconnect(websocket)
                break

            elif event == "typing":
                # Forward typing indicator
                # Could broadcast to other agents or customer
                logger.info("WebSocket typing event received")

            elif event == "ping":
                # Keepalive
                await manager.send_personal_message(
                    {"event": "pong", "data": {}}, websocket
                )

            else:
                logger.warning("Unknown WebSocket event from client")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket agent disconnected normally")

    except Exception:
        logger.error("WebSocket agent connection failed")
        manager.disconnect(websocket)
