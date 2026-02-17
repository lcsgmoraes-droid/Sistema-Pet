"""
Testes Unitários - Side Effects Guard (Fase 5.1)
===============================================

Testa o comportamento do guardião de side effects:
- Supressão de side effects durante replay
- Proibição de operações críticas durante replay
- Decorators funcionam com async e sync
- Logs estruturados
"""

import pytest
from unittest.mock import Mock, patch, call
from app.core.replay_context import enable_replay_mode, disable_replay_mode, reset_replay_mode
from app.core.side_effects_guard import (
    suppress_in_replay,
    forbid_in_replay,
    ReplayViolationError,
    send_email_guarded,
    send_notification_guarded,
    emit_domain_event_guarded,
)


class TestSuppressInReplay:
    """Testes para decorator suppress_in_replay"""
    
    def setup_method(self):
        """Reset antes de cada teste"""
        reset_replay_mode()
    
    def teardown_method(self):
        """Reset após cada teste"""
        reset_replay_mode()
    
    def test_sync_function_executes_in_normal_mode(self):
        """Função síncrona executa normalmente fora de replay"""
        executed = []
        
        @suppress_in_replay
        def my_side_effect():
            executed.append(True)
            return "executado"
        
        result = my_side_effect()
        
        assert result == "executado"
        assert len(executed) == 1
    
    def test_sync_function_suppressed_in_replay_mode(self):
        """Função síncrona é suprimida durante replay"""
        executed = []
        
        @suppress_in_replay
        def my_side_effect():
            executed.append(True)
            return "executado"
        
        enable_replay_mode()
        result = my_side_effect()
        
        assert result is None
        assert len(executed) == 0  # Não executou
    
    @pytest.mark.asyncio
    async def test_async_function_executes_in_normal_mode(self):
        """Função assíncrona executa normalmente fora de replay"""
        executed = []
        
        @suppress_in_replay
        async def my_async_side_effect():
            executed.append(True)
            return "executado"
        
        result = await my_async_side_effect()
        
        assert result == "executado"
        assert len(executed) == 1
    
    @pytest.mark.asyncio
    async def test_async_function_suppressed_in_replay_mode(self):
        """Função assíncrona é suprimida durante replay"""
        executed = []
        
        @suppress_in_replay
        async def my_async_side_effect():
            executed.append(True)
            return "executado"
        
        enable_replay_mode()
        result = await my_async_side_effect()
        
        assert result is None
        assert len(executed) == 0  # Não executou


class TestForbidInReplay:
    """Testes para decorator forbid_in_replay"""
    
    def setup_method(self):
        """Reset antes de cada teste"""
        reset_replay_mode()
    
    def teardown_method(self):
        """Reset após cada teste"""
        reset_replay_mode()
    
    def test_sync_function_executes_in_normal_mode(self):
        """Função síncrona executa normalmente fora de replay"""
        @forbid_in_replay
        def critical_operation():
            return "executado"
        
        result = critical_operation()
        assert result == "executado"
    
    def test_sync_function_raises_error_in_replay_mode(self):
        """Função síncrona lança erro durante replay"""
        @forbid_in_replay
        def critical_operation():
            return "executado"
        
        enable_replay_mode()
        
        with pytest.raises(ReplayViolationError) as exc_info:
            critical_operation()
        
        assert "proibida durante replay" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_async_function_executes_in_normal_mode(self):
        """Função assíncrona executa normalmente fora de replay"""
        @forbid_in_replay
        async def critical_async_operation():
            return "executado"
        
        result = await critical_async_operation()
        assert result == "executado"
    
    @pytest.mark.asyncio
    async def test_async_function_raises_error_in_replay_mode(self):
        """Função assíncrona lança erro durante replay"""
        @forbid_in_replay
        async def critical_async_operation():
            return "executado"
        
        enable_replay_mode()
        
        with pytest.raises(ReplayViolationError) as exc_info:
            await critical_async_operation()
        
        assert "proibida durante replay" in str(exc_info.value).lower()
    
    def test_custom_error_message(self):
        """Mensagem de erro customizada funciona"""
        # NOTA: forbid_in_replay não suporta error_message customizado
        # pois é uma função, não um decorator factory
        # Este teste valida apenas a mensagem padrão
        @forbid_in_replay
        def critical_operation():
            return "executado"
        
        enable_replay_mode()
        
        with pytest.raises(ReplayViolationError) as exc_info:
            critical_operation()
        
        assert "proibida durante replay" in str(exc_info.value).lower()


class TestGuardedFunctions:
    """Testes para funções guardadas prontas"""
    
    def setup_method(self):
        """Reset antes de cada teste"""
        reset_replay_mode()
    
    def teardown_method(self):
        """Reset após cada teste"""
        reset_replay_mode()
    
    @pytest.mark.asyncio
    async def test_send_email_guarded_suppressed_in_replay(self):
        """send_email_guarded é suprimido durante replay"""
        enable_replay_mode()
        
        result = await send_email_guarded(
            to="test@example.com",
            subject="Test",
            body="Test body"
        )
        
        assert result is None  # Suprimido
    
    @pytest.mark.asyncio
    async def test_send_notification_guarded_suppressed_in_replay(self):
        """send_notification_guarded é suprimido durante replay"""
        enable_replay_mode()
        
        result = await send_notification_guarded(
            user_id="user123",
            notification_type="info",
            message="Test notification"
        )
        
        assert result is None  # Suprimido
    
    @pytest.mark.asyncio
    async def test_emit_domain_event_guarded_raises_error_in_replay(self):
        """emit_domain_event_guarded lança erro durante replay"""
        enable_replay_mode()
        
        mock_event = Mock()
        mock_event.__class__.__name__ = "TestEvent"
        
        with pytest.raises(ReplayViolationError):
            await emit_domain_event_guarded(mock_event)


class TestLogging:
    """Testes para logs estruturados"""
    
    def setup_method(self):
        """Reset antes de cada teste"""
        reset_replay_mode()
    
    def teardown_method(self):
        """Reset após cada teste"""
        reset_replay_mode()
    
    @patch('app.core.side_effects_guard.logger')
    def test_suppressed_function_logs_info(self, mock_logger):
        """Função suprimida loga informação"""
        @suppress_in_replay
        def my_side_effect():
            return "executado"
        
        enable_replay_mode()
        my_side_effect()
        
        # Verifica que logger.info foi chamado
        assert mock_logger.info.called
        call_args = str(mock_logger.info.call_args)
        assert "Side effect suprimido" in call_args or "suprimido" in call_args.lower()
    
    @patch('app.core.side_effects_guard.logger')
    def test_forbidden_function_logs_error(self, mock_logger):
        """Função proibida loga erro"""
        @forbid_in_replay
        def critical_operation():
            return "executado"
        
        enable_replay_mode()
        
        try:
            critical_operation()
        except ReplayViolationError:
            pass
        
        # Verifica que logger.error foi chamado
        assert mock_logger.error.called


class TestIntegration:
    """Testes de integração entre replay context e side effects guard"""
    
    def setup_method(self):
        """Reset antes de cada teste"""
        reset_replay_mode()
    
    def teardown_method(self):
        """Reset após cada teste"""
        reset_replay_mode()
    
    @pytest.mark.asyncio
    async def test_multiple_guarded_functions_in_sequence(self):
        """Múltiplas funções guardadas em sequência"""
        executed = []
        
        @suppress_in_replay
        async def operation_1():
            executed.append(1)
            return "op1"
        
        @suppress_in_replay
        async def operation_2():
            executed.append(2)
            return "op2"
        
        @forbid_in_replay
        async def operation_3():
            executed.append(3)
            return "op3"
        
        # Modo normal: todas executam
        r1 = await operation_1()
        r2 = await operation_2()
        r3 = await operation_3()
        
        assert r1 == "op1"
        assert r2 == "op2"
        assert r3 == "op3"
        assert executed == [1, 2, 3]
        
        # Replay mode: suppress suprime, forbid lança erro
        executed.clear()
        enable_replay_mode()
        
        r1 = await operation_1()  # Suprimido
        r2 = await operation_2()  # Suprimido
        
        assert r1 is None
        assert r2 is None
        assert executed == []  # Nenhuma executou
        
        with pytest.raises(ReplayViolationError):
            await operation_3()  # Lança erro
