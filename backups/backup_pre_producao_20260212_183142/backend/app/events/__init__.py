"""
Módulo de Eventos de Domínio
=============================

Este módulo fornece infraestrutura para eventos de domínio no sistema.

Eventos de domínio representam fatos que aconteceram no sistema e são
importantes para o negócio. Eles são imutáveis e contêm apenas dados.

Estrutura:
- domain_events.py: Classes de eventos (apenas dados)
- event_dispatcher.py: Dispatcher em memória para publicar/subscrever eventos
- handlers.py: Handlers que reagem aos eventos (futuro)

Uso:
```python
from app.events import VendaRealizadaEvent, publish_event

# Criar evento
evento = VendaRealizadaEvent(
    venda_id=123,
    user_id=1,
    total=100.50,
    timestamp=datetime.now()
)

# Publicar evento
publish_event(evento)
```

IMPORTANTE:
- Eventos são disparados APÓS o commit da transação
- Eventos não devem alterar o comportamento principal
- Eventos são apenas notificações de fatos ocorridos
"""

from .domain_events import (
    DomainEvent,
    VendaRealizadaEvent,
    ProdutoVendidoEvent,
    KitVendidoEvent
)

from .event_dispatcher import (
    EventDispatcher,
    publish_event,
    subscribe_event,
    get_all_events
)

__all__ = [
    # Eventos
    'DomainEvent',
    'VendaRealizadaEvent',
    'ProdutoVendidoEvent',
    'KitVendidoEvent',
    
    # Dispatcher
    'EventDispatcher',
    'publish_event',
    'subscribe_event',
    'get_all_events'
]
