"""
Testes de Integração - Event Dispatcher com Replay Protection (Fase 5.1)
========================================================================

Testa a integração do dispatcher de eventos com proteção de replay:
- Eventos são publicados normalmente fora de replay
- Eventos são BLOQUEADOS durante replay (erro)
- Handlers funcionam normalmente
"""

import pytest
from unittest.mock import Mock
from dataclasses import dataclass
from app.domain.events.dispatcher import EventDispatcher, event_dispatcher
from app.domain.events.base import DomainEvent
from app.core.replay_context import enable_replay_mode, disable_replay_mode, reset_replay_mode
from app.core.side_effects_guard import ReplayViolationError


# Mock de evento para testes
@dataclass(frozen=True, kw_only=True)
class MockTestEvent(DomainEvent):
    """Evento de teste"""
    data: str


class TestEventDispatcherReplayProtection:
    """Testes para proteção de replay no dispatcher"""
    
    def setup_method(self):
        """Limpa handlers e reseta replay mode antes de cada teste"""
        reset_replay_mode()
        self.dispatcher = EventDispatcher()
    
    def teardown_method(self):
        """Reset após cada teste"""
        reset_replay_mode()
    
    def test_publish_works_in_normal_mode(self):
        """Publicar evento funciona normalmente fora de replay"""
        executed = []
        
        def handler(event: MockTestEvent):
            executed.append(event.data)
        
        self.dispatcher.subscribe(MockTestEvent, handler)
        event = MockTestEvent(data="test data")
        
        # Não deve lançar erro
        self.dispatcher.publish(event)
        
        assert len(executed) == 1
        assert executed[0] == "test data"
    
    def test_publish_blocked_in_replay_mode(self):
        """Publicar evento é bloqueado durante replay"""
        executed = []
        
        def handler(event: MockTestEvent):
            executed.append(event.data)
        
        self.dispatcher.subscribe(MockTestEvent, handler)
        event = MockTestEvent(data="test data")
        
        enable_replay_mode()
        
        # Deve lançar ReplayViolationError
        with pytest.raises(ReplayViolationError) as exc_info:
            self.dispatcher.publish(event)
        
        # Verifica mensagem de erro
        error_msg = str(exc_info.value).lower()
        assert "replay" in error_msg
        assert "evento" in error_msg or "event" in error_msg
        
        # Handler não deve ter executado
        assert len(executed) == 0
    
    def test_multiple_publish_blocked_in_replay_mode(self):
        """Múltiplas tentativas de publish são todas bloqueadas"""
        handler = Mock(__name__='mock_handler')
        
        self.dispatcher.subscribe(MockTestEvent, handler)
        enable_replay_mode()
        
        # Tentar publicar 3 eventos
        for i in range(3):
            event = MockTestEvent(data=f"data {i}")
            with pytest.raises(ReplayViolationError):
                self.dispatcher.publish(event)
        
        # Nenhum handler deve ter sido executado
        assert handler.call_count == 0
    
    def test_subscribe_works_in_replay_mode(self):
        """Registrar handlers funciona mesmo em replay (não é proibido)"""
        enable_replay_mode()
        
        handler = Mock(__name__='mock_handler')
        
        # Subscribe deve funcionar
        self.dispatcher.subscribe(MockTestEvent, handler)
        
        # Verificar que handler foi registrado
        handlers_list = self.dispatcher.list_handlers()
        assert "MockTestEvent" in handlers_list
        assert len(handlers_list["MockTestEvent"]) == 1


class TestGlobalDispatcherReplayProtection:
    """Testes usando o dispatcher global"""
    
    def setup_method(self):
        """Limpa handlers e reseta replay mode antes de cada teste"""
        reset_replay_mode()
        event_dispatcher.clear_all_handlers()
    
    def teardown_method(self):
        """Reset após cada teste"""
        reset_replay_mode()
        event_dispatcher.clear_all_handlers()
    
    def test_global_dispatcher_protected(self):
        """Dispatcher global também tem proteção de replay"""
        handler = Mock(__name__='mock_handler')
        event_dispatcher.subscribe(MockTestEvent, handler)
        
        enable_replay_mode()
        
        event = MockTestEvent(data="test")
        
        with pytest.raises(ReplayViolationError):
            event_dispatcher.publish(event)
        
        assert handler.call_count == 0


class TestReplayProtectionEdgeCases:
    """Testes de edge cases da proteção de replay"""
    
    def setup_method(self):
        """Setup antes de cada teste"""
        reset_replay_mode()
        self.dispatcher = EventDispatcher()
    
    def teardown_method(self):
        """Reset após cada teste"""
        reset_replay_mode()
    
    def test_enable_disable_cycle(self):
        """Ciclo de ativar/desativar replay"""
        handler = Mock(__name__='mock_handler')
        self.dispatcher.subscribe(MockTestEvent, handler)
        event = MockTestEvent(data="test")
        
        # Normal → funciona
        self.dispatcher.publish(event)
        assert handler.call_count == 1
        
        # Replay → bloqueado
        enable_replay_mode()
        with pytest.raises(ReplayViolationError):
            self.dispatcher.publish(event)
        assert handler.call_count == 1  # Não incrementou
        
        # Normal novamente → funciona
        disable_replay_mode()
        self.dispatcher.publish(event)
        assert handler.call_count == 2
    
    def test_multiple_handlers_none_executed_in_replay(self):
        """Múltiplos handlers registrados, nenhum executa em replay"""
        handler1 = Mock(__name__='handler1')
        handler2 = Mock(__name__='handler2')
        handler3 = Mock(__name__='handler3')
        
        self.dispatcher.subscribe(MockTestEvent, handler1)
        self.dispatcher.subscribe(MockTestEvent, handler2)
        self.dispatcher.subscribe(MockTestEvent, handler3)
        
        enable_replay_mode()
        event = MockTestEvent(data="test")
        
        with pytest.raises(ReplayViolationError):
            self.dispatcher.publish(event)
        
        # Nenhum handler deve ter executado
        assert handler1.call_count == 0
        assert handler2.call_count == 0
        assert handler3.call_count == 0
    
    def test_event_without_handlers_still_blocked(self):
        """Evento sem handlers registrados ainda é bloqueado"""
        enable_replay_mode()
        event = MockTestEvent(data="test")
        
        # Sem handlers, mas ainda deve lançar erro
        with pytest.raises(ReplayViolationError):
            self.dispatcher.publish(event)
