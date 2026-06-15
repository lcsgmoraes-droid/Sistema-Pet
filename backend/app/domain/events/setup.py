"""
Inicialização do Sistema de Eventos
====================================

Registra todos os handlers de eventos no dispatcher.

Este módulo deve ser importado na inicialização da aplicação
(ex: no main.py) para garantir que os handlers estejam registrados.
"""

import logging
from .dispatcher import event_dispatcher
from .venda_events import VendaCriada, VendaFinalizada, VendaCancelada
from .handlers import (
    LogEventHandler,
    AuditoriaEventHandler,
    IAEventHandler
)
from .kit_handler import KitEstoqueEventHandler

logger = logging.getLogger(__name__)


def setup_event_handlers(db_session_factory=None) -> None:
    """
    Registra todos os handlers de eventos no dispatcher.
    
    Esta função deve ser chamada na inicialização da aplicação
    para configurar o sistema de eventos.
    
    Args:
        db_session_factory: Factory para criar sessões do banco (opcional)
        
    Exemplo:
        from app.db import get_session
        from app.domain.events.setup import setup_event_handlers
        
        # No main.py (inicialização)
        setup_event_handlers(db_session_factory=get_session)
    """
    logger.info("🚀 Configurando sistema de eventos...")
    
    # ========================================================================
    # LOG HANDLERS (sempre ativo)
    # ========================================================================
    
    event_dispatcher.subscribe(VendaCriada, LogEventHandler.on_venda_criada)
    event_dispatcher.subscribe(VendaFinalizada, LogEventHandler.on_venda_finalizada)
    event_dispatcher.subscribe(VendaCancelada, LogEventHandler.on_venda_cancelada)
    
    logger.info("   ✅ LogEventHandler registrado")
    
    # ========================================================================
    # AUDITORIA HANDLERS (se db_session_factory fornecido)
    # ========================================================================
    
    if db_session_factory:
        auditoria_handler = AuditoriaEventHandler(db_session_factory)
        
        event_dispatcher.subscribe(VendaCriada, auditoria_handler.on_venda_criada)
        event_dispatcher.subscribe(VendaFinalizada, auditoria_handler.on_venda_finalizada)
        event_dispatcher.subscribe(VendaCancelada, auditoria_handler.on_venda_cancelada)
        
        logger.info("   ✅ AuditoriaEventHandler registrado")
    else:
        logger.warning("   ⚠️  AuditoriaEventHandler NÃO registrado (sem db_session_factory)")
    
    # ========================================================================
    # IA HANDLERS (placeholder - sempre registra mas não faz nada por enquanto)
    # ========================================================================
    
    event_dispatcher.subscribe(VendaCriada, IAEventHandler.on_venda_criada)
    event_dispatcher.subscribe(VendaFinalizada, IAEventHandler.on_venda_finalizada)
    event_dispatcher.subscribe(VendaCancelada, IAEventHandler.on_venda_cancelada)
    
    logger.info("   ✅ IAEventHandler registrado (placeholder)")
    
    # ========================================================================
    # KIT ESTOQUE HANDLERS (recalcula estoque virtual de KITs)
    # ========================================================================
    
    event_dispatcher.subscribe(VendaFinalizada, KitEstoqueEventHandler.on_venda_finalizada)
    event_dispatcher.subscribe(VendaCancelada, KitEstoqueEventHandler.on_venda_cancelada)
    
    logger.info("   ✅ KitEstoqueEventHandler registrado")
    
    # ========================================================================
    # NOTIFICAÇÃO HANDLERS (placeholder - desabilitado por padrão)
    # ========================================================================
    
    # Descomentar quando implementar:
    # event_dispatcher.subscribe(VendaFinalizada, NotificacaoEventHandler.on_venda_finalizada)
    # event_dispatcher.subscribe(VendaCancelada, NotificacaoEventHandler.on_venda_cancelada)
    # logger.info("   ✅ NotificacaoEventHandler registrado")
    
    logger.info("   ℹ️  NotificacaoEventHandler não registrado (placeholder)")
    
    # ========================================================================
    # INTEGRAÇÃO HANDLERS (placeholder - desabilitado por padrão)
    # ========================================================================
    
    # Descomentar quando implementar:
    # event_dispatcher.subscribe(VendaFinalizada, IntegracaoEventHandler.on_venda_finalizada)
    # logger.info("   ✅ IntegracaoEventHandler registrado")
    
    logger.info("   ℹ️  IntegracaoEventHandler não registrado (placeholder)")
    
    # ========================================================================
    # RESUMO
    # ========================================================================
    
    handlers_info = event_dispatcher.list_handlers()
    total_handlers = sum(len(h) for h in handlers_info.values())
    
    logger.info(
        f"✅ Sistema de eventos configurado com sucesso!\n"
        f"   📊 Total de handlers: {total_handlers}\n"
        f"   📋 Eventos cobertos: {len(handlers_info)}"
    )
    
    for event_name, handler_names in handlers_info.items():
        logger.debug(f"   - {event_name}: {', '.join(handler_names)}")
