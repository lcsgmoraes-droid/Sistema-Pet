"""
Event Dispatcher - Publicador/Assinante de Eventos
===================================================

Sistema simples de publicação e assinatura de eventos em memória.

CARACTERÍSTICAS:
- Síncrono (sem async)
- Em memória (sem fila externa)
- Thread-safe (futuro: usar lock se necessário)
- Handlers síncronos executados em ordem

IMPORTANTE:
- Erros em handlers NÃO abortam a operação principal
- Cada handler é isolado (erro em um não afeta outros)
- Logs estruturados para debugging
- REPLAY PROTECTION: Emissão de eventos é PROIBIDA durante replay
"""

import logging
from typing import Dict, List, Callable, Type
from .base import DomainEvent

# Importa proteção de replay - só disponível se módulo existir
try:
    from app.core.replay_context import is_replay_mode
    from app.core.side_effects_guard import ReplayViolationError
    REPLAY_PROTECTION_ENABLED = True
except ImportError:
    REPLAY_PROTECTION_ENABLED = False
    def is_replay_mode():
        return False
    class ReplayViolationError(Exception):
        pass

logger = logging.getLogger(__name__)


class EventDispatcher:
    """
    Dispatcher simples de eventos de domínio.
    
    Permite registrar handlers para tipos específicos de eventos
    e publica eventos para todos os handlers interessados.
    
    Uso:
        dispatcher = EventDispatcher()
        dispatcher.subscribe(VendaCriada, meu_handler)
        dispatcher.publish(VendaCriada(...))
    """
    
    def __init__(self):
        """Inicializa o dispatcher com dicionário vazio de handlers"""
        self._handlers: Dict[str, List[Callable]] = {}
        logger.info("🎯 EventDispatcher inicializado")
    
    def subscribe(self, event_type: Type[DomainEvent], handler: Callable[[DomainEvent], None]) -> None:
        """
        Registra um handler para um tipo específico de evento.
        
        Args:
            event_type: Classe do evento (ex: VendaCriada)
            handler: Função que recebe o evento como parâmetro
            
        Exemplo:
            def on_venda_criada(event: VendaCriada):
                logger.info(f"Venda {event.numero_venda} criada!")
            
            dispatcher.subscribe(VendaCriada, on_venda_criada)
        """
        event_name = event_type.__name__
        
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        
        self._handlers[event_name].append(handler)
        
        logger.debug(
            f"📌 Handler registrado: {handler.__name__} para {event_name} "
            f"(total: {len(self._handlers[event_name])})"
        )
    
    def unsubscribe(self, event_type: Type[DomainEvent], handler: Callable[[DomainEvent], None]) -> None:
        """
        Remove um handler de um tipo de evento.
        
        Args:
            event_type: Classe do evento
            handler: Função a ser removida
        """
        event_name = event_type.__name__
        
        if event_name in self._handlers:
            try:
                self._handlers[event_name].remove(handler)
                logger.debug(f"📍 Handler removido: {handler.__name__} de {event_name}")
            except ValueError:
                logger.warning(f"⚠️  Handler {handler.__name__} não encontrado em {event_name}")
    
    def publish(self, event: DomainEvent) -> None:
        """
        Publica um evento para todos os handlers registrados.
        
        IMPORTANTE:
        - Erros em handlers são capturados e logados
        - Não aborta se um handler falhar
        - Handlers são executados em ordem de registro
        - REPLAY PROTECTION: Emissão de eventos é PROIBIDA durante replay
        
        Args:
            event: Instância do evento a ser publicado
            
        Raises:
            ReplayViolationError: Se tentar emitir evento durante replay
            
        Exemplo:
            evento = VendaCriada(
                venda_id=120,
                numero_venda="20260123001",
                user_id=1,
                ...
            )
            dispatcher.publish(evento)
        """
        # PROTEÇÃO CONTRA REPLAY: Eventos nunca devem ser emitidos durante replay!
        if REPLAY_PROTECTION_ENABLED and is_replay_mode():
            error_msg = (
                f"❌ VIOLAÇÃO DE REPLAY: Tentativa de emitir evento {event.event_type} "
                f"durante modo replay! Eventos só podem ser emitidos em produção."
            )
            logger.error(error_msg, extra={
                "event_type": event.event_type,
                "event_id": event.event_id,
                "replay_mode": True
            })
            raise ReplayViolationError(error_msg)
        
        event_name = event.event_type
        handlers = self._handlers.get(event_name, [])
        
        if not handlers:
            logger.debug(f"ℹ️  Nenhum handler registrado para {event_name}")
            return
        
        logger.info(
            f"📢 Publicando evento: {event_name} "
            f"(ID: {event.event_id}, Handlers: {len(handlers)})"
        )
        
        for handler in handlers:
            try:
                logger.debug(f"   ⚙️  Executando: {handler.__name__}")
                handler(event)
                logger.debug(f"   ✅ Concluído: {handler.__name__}")
                
            except Exception as e:
                # Log do erro mas não aborta
                logger.error(
                    f"   ❌ Erro no handler {handler.__name__} "
                    f"ao processar {event_name}: {str(e)}",
                    exc_info=True
                )
                # Continua para próximo handler
        
        logger.info(f"✅ Evento {event_name} processado por {len(handlers)} handler(s)")
    
    def list_handlers(self) -> Dict[str, List[str]]:
        """
        Lista todos os handlers registrados (útil para debugging).
        
        Returns:
            Dict com event_name -> lista de nomes de handlers
        """
        return {
            event_name: [h.__name__ for h in handlers]
            for event_name, handlers in self._handlers.items()
        }
    
    def clear_all_handlers(self) -> None:
        """
        Remove todos os handlers registrados.
        
        Útil para testes ou reset do sistema.
        """
        logger.warning("🗑️  Removendo todos os handlers do dispatcher")
        self._handlers.clear()


# ============================================================================
# INSTÂNCIA GLOBAL (SINGLETON)
# ============================================================================

# Instância global para uso em toda a aplicação
event_dispatcher = EventDispatcher()


# ============================================================================
# FUNÇÕES DE CONVENIÊNCIA
# ============================================================================

def publish_event(event: DomainEvent) -> None:
    """
    Função de conveniência para publicar eventos usando o dispatcher global.
    
    Args:
        event: Evento a ser publicado
        
    Exemplo:
        from app.domain.events import publish_event, VendaCriada
        
        evento = VendaCriada(...)
        publish_event(evento)
    """
    event_dispatcher.publish(event)


def subscribe_handler(event_type: Type[DomainEvent], handler: Callable[[DomainEvent], None]) -> None:
    """
    Função de conveniência para registrar handlers usando o dispatcher global.
    
    Args:
        event_type: Tipo do evento
        handler: Função handler
        
    Exemplo:
        from app.domain.events import subscribe_handler, VendaCriada
        
        def meu_handler(event: VendaCriada):
            logger.info(f"Venda criada: {event.numero_venda}")
        
        subscribe_handler(VendaCriada, meu_handler)
    """
    event_dispatcher.subscribe(event_type, handler)
