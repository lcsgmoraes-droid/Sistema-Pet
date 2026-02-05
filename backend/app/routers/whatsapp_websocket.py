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
    db: Session = Depends(get_db)
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
        user = get_current_user_from_token(token, db)
        logger.info(f"WebSocket: user {user.id} connecting as agent {agent_id}")
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    await manager.connect(websocket, agent_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            event = message.get("event")
            payload = message.get("data", {})
            
            # Handle client events
            if event == "join_agent_room":
                logger.info(f"Agent {agent_id} joined room")
                # Already connected, nothing to do
                
            elif event == "leave_agent_room":
                logger.info(f"Agent {agent_id} left room")
                manager.disconnect(websocket)
                break
                
            elif event == "typing":
                # Forward typing indicator
                session_id = payload.get("session_id")
                is_typing = payload.get("is_typing", False)
                
                # Could broadcast to other agents or customer
                logger.info(f"Agent {agent_id} typing in session {session_id}: {is_typing}")
                
            elif event == "ping":
                # Keepalive
                await manager.send_personal_message(
                    {"event": "pong", "data": {}},
                    websocket
                )
                
            else:
                logger.warning(f"Unknown event from client: {event}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"Agent {agent_id} disconnected normally")
    
    except Exception as e:
        logger.error(f"WebSocket error for agent {agent_id}: {e}")
        manager.disconnect(websocket)
