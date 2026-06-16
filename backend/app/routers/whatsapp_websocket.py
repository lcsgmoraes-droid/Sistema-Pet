"""
WebSocket Router para FastAPI
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
import logging
import json

from app.db import get_session as get_db
from app.whatsapp.websocket import manager
from app.auth import get_current_user_from_token

router = APIRouter()
logger = logging.getLogger(__name__)


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

    # Validar token JWT
    try:
        get_current_user_from_token(token, db)
        logger.info("WebSocket agent connection authenticated")
    except Exception:
        logger.error("WebSocket auth failed")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    await manager.connect(websocket, agent_id)

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
