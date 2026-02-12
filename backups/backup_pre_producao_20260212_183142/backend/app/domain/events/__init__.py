"""
Sistema de Eventos de Domínio
==============================

Sistema simples de eventos em memória para desacoplar
reações do domínio principal.

COMPONENTES:
- base.py: Classe base para eventos
- venda_events.py: Eventos do domínio de vendas
- dispatcher.py: Publicador/assinante de eventos
- handlers.py: Manipuladores de eventos
"""

from .base import DomainEvent
from .venda_events import VendaCriada, VendaFinalizada, VendaCancelada
from .dispatcher import EventDispatcher, event_dispatcher
from .handlers import LogEventHandler, AuditoriaEventHandler

__all__ = [
    'DomainEvent',
    'VendaCriada',
    'VendaFinalizada',
    'VendaCancelada',
    'EventDispatcher',
    'event_dispatcher',
    'LogEventHandler',
    'AuditoriaEventHandler',
]
