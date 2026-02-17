"""
Handoff Manager - Gerenciador de transferências para atendentes humanos
Decide quando transferir, atribui atendentes, gerencia fila
"""
from typing import Optional, Tuple, List, Dict
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from app.whatsapp.models_handoff import WhatsAppHandoff, WhatsAppAgent
from app.whatsapp.models import WhatsAppSession
from app.whatsapp.sentiment import get_sentiment_analyzer

logger = logging.getLogger(__name__)


class HandoffManager:
    """Gerencia transferências de bot para atendente humano"""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.sentiment_analyzer = get_sentiment_analyzer()
    
    def should_handoff(
        self,
        session: WhatsAppSession,
        message: str,
        sentiment_result: Optional[Dict] = None
    ) -> Tuple[bool, str, str]:
        """
        Decide se deve transferir para humano
        
        Args:
            session: Sessão WhatsApp
            message: Última mensagem do cliente
            sentiment_result: Resultado da análise de sentimento (opcional)
            
        Returns:
            Tupla (should_handoff, reason, priority)
        """
        # 1. Verificar se já está em handoff
        active_handoff = self.get_active_handoff(session.id)
        if active_handoff:
            logger.info(f"Session {session.id} already in handoff")
            return False, "already_in_handoff", "medium"
        
        # 2. Analisar sentimento se não foi fornecido
        if not sentiment_result:
            sentiment_result = self.sentiment_analyzer.analyze(message)
        
        # 3. Verificar triggers automáticos
        if sentiment_result.get("should_handoff"):
            reason = sentiment_result.get("handoff_reason", "auto_sentiment")
            priority = self._calculate_priority(sentiment_result)
            logger.info(f"Sentiment trigger handoff: reason={reason}, priority={priority}")
            return True, reason, priority
        
        # 4. Verificar mensagens repetidas
        if session.message_count >= 3:
            recent_messages = self._get_recent_user_messages(session.id, limit=3)
            if len(set(recent_messages)) == 1:  # Todas iguais
                logger.warning(f"Repeated message detected in session {session.id}")
                return True, "auto_repeat", "high"
        
        # 5. Verificar timeout (mais de 5 mensagens sem resolução)
        if session.message_count >= 10:
            logger.warning(f"Timeout: session {session.id} has {session.message_count} messages")
            return True, "auto_timeout", "medium"
        
        # 6. Verificar horário (se fora do expediente e cliente insiste)
        # TODO: Implementar verificação de horário
        
        return False, "", "medium"
    
    def create_handoff(
        self,
        session_id: str,
        phone_number: str,
        reason: str,
        priority: str = "medium",
        sentiment_score: Optional[Decimal] = None,
        sentiment_label: Optional[str] = None,
        customer_name: Optional[str] = None,
        reason_details: Optional[str] = None
    ) -> WhatsAppHandoff:
        """
        Cria uma solicitação de handoff
        
        Args:
            session_id: ID da sessão
            phone_number: Telefone do cliente
            reason: Motivo da transferência
            priority: Prioridade (low, medium, high, urgent)
            sentiment_score: Score de sentimento
            sentiment_label: Label do sentimento
            customer_name: Nome do cliente
            reason_details: Detalhes do motivo
            
        Returns:
            WhatsAppHandoff criado
        """
        handoff = WhatsAppHandoff(
            tenant_id=self.tenant_id,
            session_id=session_id,
            phone_number=phone_number,
            customer_name=customer_name,
            reason=reason,
            reason_details=reason_details,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            priority=priority,
            status="pending"
        )
        
        self.db.add(handoff)
        
        # Atualizar status da sessão
        session = self.db.query(WhatsAppSession).filter(
            WhatsAppSession.id == session_id
        ).first()
        
        if session:
            session.status = "waiting_human"
        
        self.db.commit()
        self.db.refresh(handoff)
        
        logger.info(f"Handoff created: {handoff.id} (reason={reason}, priority={priority})")
        
        # Tentar atribuir automaticamente
        self._try_auto_assign(handoff)
        
        return handoff
    
    def assign_to_agent(
        self,
        handoff_id: str,
        agent_id: str,
        auto: bool = False
    ) -> WhatsAppHandoff:
        """
        Atribui handoff para um atendente
        
        Args:
            handoff_id: ID do handoff
            agent_id: ID do agente
            auto: Se foi atribuição automática
            
        Returns:
            Handoff atualizado
        """
        handoff = self.db.query(WhatsAppHandoff).filter(
            WhatsAppHandoff.id == handoff_id,
            WhatsAppHandoff.tenant_id == self.tenant_id
        ).first()
        
        if not handoff:
            raise ValueError(f"Handoff {handoff_id} not found")
        
        if handoff.status not in ["pending", "assigned"]:
            raise ValueError(f"Handoff {handoff_id} cannot be assigned (status={handoff.status})")
        
        # Verificar se agente existe e está disponível
        agent = self.db.query(WhatsAppAgent).filter(
            WhatsAppAgent.id == agent_id,
            WhatsAppAgent.tenant_id == self.tenant_id
        ).first()
        
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        if agent.status != "online" and not auto:
            raise ValueError(f"Agent {agent.name} is {agent.status}")
        
        if agent.current_chats >= agent.max_concurrent_chats:
            raise ValueError(f"Agent {agent.name} is at max capacity")
        
        # Atribuir
        handoff.assigned_to = agent_id
        handoff.assigned_at = datetime.utcnow()
        handoff.status = "assigned"
        
        # Atualizar contador do agente
        agent.current_chats += 1
        
        # Atualizar sessão
        session = handoff.session
        if session:
            session.status = "human"
            session.assigned_to = agent_id
        
        self.db.commit()
        self.db.refresh(handoff)
        
        logger.info(f"Handoff {handoff_id} assigned to agent {agent.name} ({'auto' if auto else 'manual'})")
        
        return handoff
    
    def start_handling(self, handoff_id: str, agent_id: str) -> WhatsAppHandoff:
        """
        Marca que atendente começou a atender
        
        Args:
            handoff_id: ID do handoff
            agent_id: ID do agente
            
        Returns:
            Handoff atualizado
        """
        handoff = self.db.query(WhatsAppHandoff).filter(
            WhatsAppHandoff.id == handoff_id,
            WhatsAppHandoff.assigned_to == agent_id
        ).first()
        
        if not handoff:
            raise ValueError("Handoff not found or not assigned to you")
        
        handoff.status = "in_progress"
        self.db.commit()
        self.db.refresh(handoff)
        
        logger.info(f"Agent {agent_id} started handling {handoff_id}")
        
        return handoff
    
    def resolve_handoff(
        self,
        handoff_id: str,
        agent_id: str,
        resolution_notes: str,
        return_to_bot: bool = False
    ) -> WhatsAppHandoff:
        """
        Marca handoff como resolvido
        
        Args:
            handoff_id: ID do handoff
            agent_id: ID do agente
            resolution_notes: Notas sobre a resolução
            return_to_bot: Se deve retornar para bot após resolver
            
        Returns:
            Handoff resolvido
        """
        handoff = self.db.query(WhatsAppHandoff).filter(
            WhatsAppHandoff.id == handoff_id,
            WhatsAppHandoff.assigned_to == agent_id
        ).first()
        
        if not handoff:
            raise ValueError("Handoff not found or not assigned to you")
        
        # Calcular tempo de resolução
        if handoff.created_at:
            resolution_time = (datetime.utcnow() - handoff.created_at).total_seconds()
            handoff.resolution_time_seconds = int(resolution_time)
        
        handoff.status = "resolved"
        handoff.resolved_at = datetime.utcnow()
        handoff.resolution_notes = resolution_notes
        
        # Atualizar contador do agente
        agent = handoff.agent
        if agent and agent.current_chats > 0:
            agent.current_chats -= 1
        
        # Atualizar sessão
        session = handoff.session
        if session:
            if return_to_bot:
                session.status = "bot"
                session.assigned_to = None
            else:
                session.status = "closed"
                session.closed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(handoff)
        
        logger.info(f"Handoff {handoff_id} resolved by agent {agent_id} ({handoff.resolution_time_seconds}s)")
        
        return handoff
    
    def get_active_handoff(self, session_id: str) -> Optional[WhatsAppHandoff]:
        """Busca handoff ativo para uma sessão"""
        return self.db.query(WhatsAppHandoff).filter(
            WhatsAppHandoff.session_id == session_id,
            WhatsAppHandoff.tenant_id == self.tenant_id,
            WhatsAppHandoff.status.in_(["pending", "assigned", "in_progress"])
        ).first()
    
    def get_pending_handoffs(self, limit: int = 50) -> List[WhatsAppHandoff]:
        """Lista handoffs pendentes"""
        return self.db.query(WhatsAppHandoff).filter(
            WhatsAppHandoff.tenant_id == self.tenant_id,
            WhatsAppHandoff.status == "pending"
        ).order_by(
            WhatsAppHandoff.priority.desc(),
            WhatsAppHandoff.created_at.asc()
        ).limit(limit).all()
    
    def _calculate_priority(self, sentiment_result: Dict) -> str:
        """Calcula prioridade baseado no sentimento"""
        score = float(sentiment_result.get("score", 0))
        
        if score <= -0.8:
            return "urgent"
        elif score <= -0.6:
            return "high"
        elif score <= -0.3:
            return "medium"
        else:
            return "low"
    
    def _get_recent_user_messages(self, session_id: str, limit: int = 5) -> List[str]:
        """Busca mensagens recentes do usuário"""
        from app.whatsapp.models import WhatsAppMessage
        
        messages = self.db.query(WhatsAppMessage).filter(
            WhatsAppMessage.session_id == session_id,
            WhatsAppMessage.tipo == "recebida"
        ).order_by(
            WhatsAppMessage.created_at.desc()
        ).limit(limit).all()
        
        return [msg.conteudo for msg in messages]
    
    def _try_auto_assign(self, handoff: WhatsAppHandoff):
        """Tenta atribuir automaticamente para agente disponível"""
        # Buscar agentes online com auto_assign
        agents = self.db.query(WhatsAppAgent).filter(
            WhatsAppAgent.tenant_id == self.tenant_id,
            WhatsAppAgent.status == "online",
            WhatsAppAgent.auto_assign == True
        ).all()
        
        if not agents:
            logger.info("No agents available for auto-assign")
            return
        
        # Encontrar agente com menos chats
        available_agents = [
            a for a in agents
            if a.current_chats < a.max_concurrent_chats
        ]
        
        if not available_agents:
            logger.warning("All agents at max capacity")
            return
        
        # Atribuir para quem tem menos chats
        agent = min(available_agents, key=lambda a: a.current_chats)
        
        try:
            self.assign_to_agent(handoff.id, agent.id, auto=True)
        except Exception as e:
            logger.error(f"Failed to auto-assign: {e}")


def get_handoff_manager(db: Session, tenant_id: str) -> HandoffManager:
    """Factory function para criar HandoffManager"""
    return HandoffManager(db, tenant_id)
