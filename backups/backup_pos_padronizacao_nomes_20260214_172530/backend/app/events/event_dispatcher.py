"""
Event Dispatcher - Publicação e Subscrição de Eventos
======================================================

Sistema simples de pub/sub para eventos de domínio.

Por enquanto, armazena eventos em memória e permite subscribers.
No futuro, pode ser estendido para:
- Persistir eventos em banco (Event Store)
- Publicar em fila (RabbitMQ, Kafka)
- Integrar com IA para análise

Arquitetura:
- Singleton pattern (instância global)
- Lista em memória de eventos
- Dicionário de subscribers por tipo de evento
- Thread-safe (para uso em FastAPI async)

Uso:
```python
from app.events import publish_event, subscribe_event, VendaRealizadaEvent

# Publicar evento
evento = VendaRealizadaEvent(venda_id=123, total=100.0, user_id=1)
publish_event(evento)

# Subscrever a eventos
def handler(evento: VendaRealizadaEvent):
    logger.info(f"Venda {evento.venda_id} realizada!")

subscribe_event(VendaRealizadaEvent, handler)
```
"""

import logging
from typing import List, Dict, Type, Callable, Any
from threading import Lock

from .domain_events import DomainEvent

logger = logging.getLogger(__name__)


class EventDispatcher:
    """
    Dispatcher de eventos de domínio (Singleton).
    
    Responsabilidades:
    - Armazenar eventos em memória
    - Notificar subscribers quando eventos são publicados
    - Fornecer acesso ao histórico de eventos
    
    Thread-safe para uso em aplicações async.
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._events: List[DomainEvent] = []
        self._subscribers: Dict[Type[DomainEvent], List[Callable]] = {}
        self._initialized = True
        logger.info("📢 EventDispatcher inicializado")
    
    def publish(self, event: DomainEvent) -> None:
        """
        Publica um evento de domínio.
        
        Ações:
        1. Armazena evento na lista em memória
        2. Loga o evento
        3. Notifica todos os subscribers do tipo do evento
        
        Args:
            event: Instância de DomainEvent a ser publicado
        """
        with self._lock:
            # Armazenar evento
            self._events.append(event)
            
            # Log estruturado
            logger.info(
                f"📢 Evento publicado: {event.__class__.__name__} | "
                f"venda_id={getattr(event, 'venda_id', 'N/A')} | "
                f"user_id={event.user_id} | "
                f"timestamp={event.timestamp.isoformat()}"
            )
            
            # Notificar subscribers
            event_type = type(event)
            if event_type in self._subscribers:
                for handler in self._subscribers[event_type]:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(
                            f"❌ Erro ao processar handler para {event.__class__.__name__}: {e}",
                            exc_info=True
                        )
    
    def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """
        Registra um handler para um tipo de evento.
        
        Args:
            event_type: Classe do evento (ex: VendaRealizadaEvent)
            handler: Função que será chamada quando evento for publicado
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            self._subscribers[event_type].append(handler)
            logger.info(f"✅ Handler registrado para {event_type.__name__}")
    
    def get_all_events(self) -> List[DomainEvent]:
        """
        Retorna todos os eventos publicados (histórico em memória).
        
        Útil para:
        - Debugging
        - Análise de comportamento
        - Replay de eventos
        - Testes
        
        Returns:
            Lista de todos os eventos publicados
        """
        with self._lock:
            return self._events.copy()
    
    def get_events_by_type(self, event_type: Type[DomainEvent]) -> List[DomainEvent]:
        """
        Retorna apenas eventos de um tipo específico.
        
        Args:
            event_type: Classe do evento a filtrar
            
        Returns:
            Lista de eventos do tipo especificado
        """
        with self._lock:
            return [e for e in self._events if isinstance(e, event_type)]
    
    def get_events_by_user(self, user_id: int) -> List[DomainEvent]:
        """
        Retorna eventos de um tenant específico.
        
        Args:
            user_id: ID do tenant
            
        Returns:
            Lista de eventos do tenant
        """
        with self._lock:
            return [e for e in self._events if e.user_id == user_id]
    
    def get_events_by_venda(self, venda_id: int) -> List[DomainEvent]:
        """
        Retorna todos os eventos relacionados a uma venda.
        
        Args:
            venda_id: ID da venda
            
        Returns:
            Lista de eventos da venda
        """
        with self._lock:
            return [
                e for e in self._events 
                if hasattr(e, 'venda_id') and e.venda_id == venda_id
            ]
    
    def clear_events(self) -> int:
        """
        Limpa histórico de eventos em memória.
        
        ⚠️ USO CUIDADOSO: Apenas para testes ou reinicialização.
        
        Returns:
            Quantidade de eventos removidos
        """
        with self._lock:
            count = len(self._events)
            self._events.clear()
            logger.warning(f"⚠️  Histórico de eventos limpo: {count} eventos removidos")
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas sobre eventos.
        
        Returns:
            Dict com estatísticas:
            - total: Total de eventos
            - por_tipo: Contagem por tipo de evento
            - por_usuario: Contagem por tenant
        """
        with self._lock:
            stats = {
                'total': len(self._events),
                'por_tipo': {},
                'por_usuario': {}
            }
            
            for event in self._events:
                # Contar por tipo
                event_type_name = event.__class__.__name__
                stats['por_tipo'][event_type_name] = stats['por_tipo'].get(event_type_name, 0) + 1
                
                # Contar por usuário
                stats['por_usuario'][event.user_id] = stats['por_usuario'].get(event.user_id, 0) + 1
            
            return stats


# ============================================================
# INSTÂNCIA GLOBAL (Singleton)
# ============================================================

_dispatcher = EventDispatcher()


# ============================================================
# FUNÇÕES DE CONVENIÊNCIA (API Pública)
# ============================================================

def publish_event(event: DomainEvent) -> None:
    """
    Publica um evento de domínio.
    
    Atalho para EventDispatcher().publish(event)
    
    Args:
        event: Evento a ser publicado
    """
    _dispatcher.publish(event)


def subscribe_event(event_type: Type[DomainEvent], handler: Callable) -> None:
    """
    Registra handler para um tipo de evento.
    
    Atalho para EventDispatcher().subscribe(event_type, handler)
    
    Args:
        event_type: Classe do evento
        handler: Função handler
    """
    _dispatcher.subscribe(event_type, handler)


def get_all_events() -> List[DomainEvent]:
    """
    Retorna todos os eventos publicados.
    
    Atalho para EventDispatcher().get_all_events()
    """
    return _dispatcher.get_all_events()


def get_events_by_type(event_type: Type[DomainEvent]) -> List[DomainEvent]:
    """
    Retorna eventos de um tipo específico.
    
    Atalho para EventDispatcher().get_events_by_type(event_type)
    """
    return _dispatcher.get_events_by_type(event_type)


def get_events_by_user(user_id: int) -> List[DomainEvent]:
    """
    Retorna eventos de um tenant específico.
    
    Atalho para EventDispatcher().get_events_by_user(user_id)
    """
    return _dispatcher.get_events_by_user(user_id)


def get_events_by_venda(venda_id: int) -> List[DomainEvent]:
    """
    Retorna eventos de uma venda específica.
    
    Atalho para EventDispatcher().get_events_by_venda(venda_id)
    """
    return _dispatcher.get_events_by_venda(venda_id)


def get_event_stats() -> Dict[str, Any]:
    """
    Retorna estatísticas sobre eventos.
    
    Atalho para EventDispatcher().get_stats()
    """
    return _dispatcher.get_stats()


def clear_events() -> int:
    """
    Limpa histórico de eventos.
    
    ⚠️ USO CUIDADOSO: Apenas para testes.
    
    Atalho para EventDispatcher().clear_events()
    """
    return _dispatcher.clear_events()
