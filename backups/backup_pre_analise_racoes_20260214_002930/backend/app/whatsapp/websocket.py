"""
WebSocket Server para WhatsApp Atendimento
Gerencia conexões Socket.IO para real-time updates
"""

from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import logging
from datetime import datetime

from app.db import get_session as get_db
from app.auth import get_current_user_from_token
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Gerencia conexões WebSocket dos agentes"""
    
    def __init__(self):
        # agent_id -> set of WebSocket connections
        self.agent_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> agent_id mapping
        self.connection_agents: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, agent_id: str):
        """Conecta um agente"""
        await websocket.accept()
        
        if agent_id not in self.agent_connections:
            self.agent_connections[agent_id] = set()
        
        self.agent_connections[agent_id].add(websocket)
        self.connection_agents[websocket] = agent_id
        
        logger.info(f"Agent {agent_id} connected. Total connections: {len(self.agent_connections[agent_id])}")
        
        # Send welcome message
        await self.send_personal_message({
            "event": "connected",
            "data": {
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Desconecta um agente"""
        if websocket in self.connection_agents:
            agent_id = self.connection_agents[websocket]
            
            if agent_id in self.agent_connections:
                self.agent_connections[agent_id].discard(websocket)
                
                # Remove empty sets
                if not self.agent_connections[agent_id]:
                    del self.agent_connections[agent_id]
            
            del self.connection_agents[websocket]
            logger.info(f"Agent {agent_id} disconnected")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Envia mensagem para uma conexão específica"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to websocket: {e}")
    
    async def send_to_agent(self, message: dict, agent_id: str):
        """Envia mensagem para todas as conexões de um agente"""
        if agent_id in self.agent_connections:
            dead_connections = []
            
            for websocket in self.agent_connections[agent_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to agent {agent_id}: {e}")
                    dead_connections.append(websocket)
            
            # Clean up dead connections
            for websocket in dead_connections:
                self.disconnect(websocket)
    
    async def broadcast_to_all_agents(self, message: dict):
        """Envia mensagem para todos os agentes conectados"""
        for agent_id in list(self.agent_connections.keys()):
            await self.send_to_agent(message, agent_id)
    
    async def broadcast_to_online_agents(self, message: dict, db: Session):
        """Envia mensagem apenas para agentes online"""
        from app.whatsapp.models_handoff import WhatsAppAgent
        
        online_agents = db.query(WhatsAppAgent).filter(
            WhatsAppAgent.status == "online"
        ).all()
        
        for agent in online_agents:
            await self.send_to_agent(message, str(agent.id))

# Singleton instance
manager = ConnectionManager()

# Event emitters (to be called from API endpoints)

async def emit_new_handoff(handoff_dict: dict, db: Session):
    """Emite evento de novo handoff para agentes online"""
    message = {
        "event": "new_handoff",
        "data": handoff_dict
    }
    await manager.broadcast_to_online_agents(message, db)
    logger.info(f"Emitted new_handoff event: {handoff_dict['id']}")

async def emit_handoff_assigned(handoff_dict: dict, agent_id: str):
    """Emite evento de handoff atribuído para o agente"""
    message = {
        "event": "handoff_assigned",
        "data": handoff_dict
    }
    await manager.send_to_agent(message, agent_id)
    logger.info(f"Emitted handoff_assigned to agent {agent_id}")

async def emit_handoff_resolved(handoff_id: str, db: Session):
    """Emite evento de handoff resolvido"""
    message = {
        "event": "handoff_resolved",
        "data": {"handoff_id": handoff_id}
    }
    await manager.broadcast_to_all_agents(message)
    logger.info(f"Emitted handoff_resolved: {handoff_id}")

async def emit_new_message(session_id: str, message_dict: dict, agent_id: str = None):
    """Emite evento de nova mensagem"""
    message = {
        "event": "new_message",
        "data": {
            "session_id": session_id,
            "message": message_dict
        }
    }
    
    if agent_id:
        await manager.send_to_agent(message, agent_id)
    else:
        await manager.broadcast_to_all_agents(message)
    
    logger.info(f"Emitted new_message for session {session_id}")

async def emit_agent_status_change(agent_dict: dict, db: Session):
    """Emite evento de mudança de status do agente"""
    message = {
        "event": "agent_status_change",
        "data": agent_dict
    }
    await manager.broadcast_to_all_agents(message)
    logger.info(f"Emitted agent_status_change: {agent_dict['id']}")

async def emit_typing_indicator(session_id: str, is_typing: bool, agent_id: str):
    """Emite indicador de digitação"""
    message = {
        "event": "typing_indicator",
        "data": {
            "session_id": session_id,
            "is_typing": is_typing
        }
    }
    await manager.send_to_agent(message, agent_id)
