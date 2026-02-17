"""
Gerenciamento de Contexto de Conversação
Mantém histórico e contexto para respostas mais inteligentes
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from app.whatsapp.models import WhatsAppSession, WhatsAppMessage
from app.whatsapp.intents import IntentType
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Contexto completo de uma conversa"""
    session_id: str
    phone_number: str
    tenant_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    current_intent: Optional[IntentType] = None
    customer_data: Optional[Dict[str, Any]] = None
    conversation_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    def add_message(self, role: str, content: str, intent: Optional[IntentType] = None):
        """Adiciona mensagem ao histórico"""
        self.messages.append({
            "role": role,  # "user" ou "assistant"
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "intent": intent.value if intent else None
        })
        self.last_activity = datetime.utcnow()
        
        # Limitar histórico a últimas 10 mensagens para não explodir o contexto
        if len(self.messages) > 10:
            self.messages = self.messages[-10:]
    
    def get_last_messages(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retorna últimas N mensagens"""
        return self.messages[-limit:]
    
    def get_formatted_history(self, limit: int = 5) -> str:
        """Retorna histórico formatado para prompt da IA"""
        last_messages = self.get_last_messages(limit)
        if not last_messages:
            return "Nenhum histórico de conversa."
        
        history = []
        for msg in last_messages:
            role = "Cliente" if msg["role"] == "user" else "Assistente"
            history.append(f"{role}: {msg['content']}")
        
        return "\n".join(history)
    
    def set_customer_data(self, data: Dict[str, Any]):
        """Define dados do cliente identificado"""
        self.customer_data = data
    
    def set_data(self, key: str, value: Any):
        """Define dado no contexto da conversa"""
        self.conversation_data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Obtém dado do contexto"""
        return self.conversation_data.get(key, default)
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Verifica se contexto expirou por inatividade"""
        expiration_time = self.last_activity + timedelta(minutes=timeout_minutes)
        return datetime.utcnow() > expiration_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa contexto para dicionário"""
        return {
            "session_id": self.session_id,
            "phone_number": self.phone_number,
            "tenant_id": self.tenant_id,
            "messages": self.messages,
            "current_intent": self.current_intent.value if self.current_intent else None,
            "customer_data": self.customer_data,
            "conversation_data": self.conversation_data,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }


class ContextManager:
    """Gerenciador de contextos de conversação"""
    
    def __init__(self):
        # Cache em memória de contextos ativos (phone_number -> ConversationContext)
        self._contexts: Dict[str, ConversationContext] = {}
        self._cleanup_interval_minutes = 30
    
    def get_or_create_context(
        self,
        db: Session,
        phone_number: str,
        tenant_id: str,
        session_id: Optional[str] = None
    ) -> ConversationContext:
        """
        Obtém contexto existente ou cria novo
        
        Args:
            db: Sessão do banco
            phone_number: Telefone do usuário
            tenant_id: ID do tenant
            session_id: ID da sessão (opcional)
            
        Returns:
            ConversationContext
        """
        # Verificar cache primeiro
        cache_key = f"{tenant_id}:{phone_number}"
        
        if cache_key in self._contexts:
            context = self._contexts[cache_key]
            
            # Verificar se expirou
            if context.is_expired(self._cleanup_interval_minutes):
                logger.info(f"Contexto expirado para {phone_number}, criando novo")
                del self._contexts[cache_key]
            else:
                return context
        
        # Buscar sessão ativa no banco
        session = None
        if session_id:
            session = db.query(WhatsAppSession).filter(
                WhatsAppSession.id == session_id,
                WhatsAppSession.tenant_id == tenant_id
            ).first()
        
        if not session:
            # Buscar última sessão ativa para este número
            session = db.query(WhatsAppSession).filter(
                WhatsAppSession.phone_number == phone_number,
                WhatsAppSession.tenant_id == tenant_id,
                WhatsAppSession.status.in_(["active", "waiting"])
            ).order_by(WhatsAppSession.started_at.desc()).first()
        
        # Criar novo contexto
        context = ConversationContext(
            session_id=str(session.id) if session else "",
            phone_number=phone_number,
            tenant_id=tenant_id
        )
        
        # Carregar histórico de mensagens se sessão existir
        if session:
            context = self._load_session_history(db, session, context)
        
        # Tentar identificar cliente
        customer_data = self._identify_customer(db, phone_number, tenant_id)
        if customer_data:
            context.set_customer_data(customer_data)
        
        # Salvar no cache
        self._contexts[cache_key] = context
        
        return context
    
    def _load_session_history(
        self,
        db: Session,
        session: WhatsAppSession,
        context: ConversationContext
    ) -> ConversationContext:
        """Carrega histórico de mensagens da sessão"""
        try:
            messages = db.query(WhatsAppMessage).filter(
                WhatsAppMessage.session_id == session.id
            ).order_by(WhatsAppMessage.timestamp.asc()).limit(10).all()
            
            for msg in messages:
                context.add_message(
                    role="user" if msg.direction == "inbound" else "assistant",
                    content=msg.message_body or "",
                    intent=IntentType(msg.intent) if msg.intent else None
                )
            
            logger.info(f"Carregadas {len(messages)} mensagens para sessão {session.id}")
        except Exception as e:
            logger.error(f"Erro ao carregar histórico: {e}")
        
        return context
    
    def _identify_customer(
        self,
        db: Session,
        phone_number: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Tenta identificar cliente pelo telefone
        Busca em tabelas de clientes/vendas/etc
        """
        try:
            # TODO: Implementar busca real quando tivermos tabela de clientes
            # Por enquanto, retorna None
            # 
            # Exemplo futuro:
            # from app.models import Customer
            # customer = db.query(Customer).filter(
            #     Customer.phone == phone_number,
            #     Customer.tenant_id == tenant_id
            # ).first()
            # 
            # if customer:
            #     return {
            #         "id": str(customer.id),
            #         "name": customer.name,
            #         "email": customer.email,
            #         "pets": [...],
            #         "last_purchase": {...}
            #     }
            
            return None
        except Exception as e:
            logger.error(f"Erro ao identificar cliente: {e}")
            return None
    
    def update_context(self, context: ConversationContext):
        """Atualiza contexto no cache"""
        cache_key = f"{context.tenant_id}:{context.phone_number}"
        context.last_activity = datetime.utcnow()
        self._contexts[cache_key] = context
    
    def clear_context(self, phone_number: str, tenant_id: str):
        """Remove contexto do cache"""
        cache_key = f"{tenant_id}:{phone_number}"
        if cache_key in self._contexts:
            del self._contexts[cache_key]
            logger.info(f"Contexto removido para {phone_number}")
    
    def cleanup_expired_contexts(self):
        """Remove contextos expirados do cache"""
        expired_keys = []
        
        for key, context in self._contexts.items():
            if context.is_expired(self._cleanup_interval_minutes):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._contexts[key]
        
        if expired_keys:
            logger.info(f"Removidos {len(expired_keys)} contextos expirados")
    
    def get_active_contexts_count(self) -> int:
        """Retorna número de contextos ativos"""
        self.cleanup_expired_contexts()
        return len(self._contexts)


# Instância singleton
context_manager = ContextManager()
