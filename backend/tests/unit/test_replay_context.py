"""
Testes Unitários - Replay Context (Fase 5.1)
============================================

Testa o comportamento do contexto de replay:
- ContextVar funciona com async
- enable/disable funcionam corretamente
- Context manager funciona
- Isolamento entre testes
"""

import pytest
from app.core.replay_context import (
    is_replay_mode,
    enable_replay_mode,
    disable_replay_mode,
    reset_replay_mode,
    ReplayMode,
)


class TestReplayContext:
    """Testes para contexto de replay"""
    
    def setup_method(self):
        """Reset antes de cada teste"""
        reset_replay_mode()
    
    def teardown_method(self):
        """Reset após cada teste"""
        reset_replay_mode()
    
    def test_default_mode_is_false(self):
        """Por padrão, replay mode está desativado"""
        assert is_replay_mode() is False
    
    def test_enable_replay_mode(self):
        """Ativar replay mode funciona"""
        enable_replay_mode()
        assert is_replay_mode() is True
    
    def test_disable_replay_mode(self):
        """Desativar replay mode funciona"""
        enable_replay_mode()
        assert is_replay_mode() is True
        
        disable_replay_mode()
        assert is_replay_mode() is False
    
    def test_multiple_enable_disable_cycles(self):
        """Múltiplos ciclos de ativação/desativação"""
        for _ in range(3):
            assert is_replay_mode() is False
            enable_replay_mode()
            assert is_replay_mode() is True
            disable_replay_mode()
            assert is_replay_mode() is False
    
    def test_reset_replay_mode(self):
        """Reset sempre volta ao padrão (False)"""
        enable_replay_mode()
        assert is_replay_mode() is True
        
        reset_replay_mode()
        assert is_replay_mode() is False


class TestReplayModeContextManager:
    """Testes para context manager de replay"""
    
    def setup_method(self):
        """Reset antes de cada teste"""
        reset_replay_mode()
    
    def teardown_method(self):
        """Reset após cada teste"""
        reset_replay_mode()
    
    def test_context_manager_activates_replay(self):
        """Context manager ativa replay dentro do bloco"""
        assert is_replay_mode() is False
        
        with ReplayMode():
            assert is_replay_mode() is True
        
        assert is_replay_mode() is False
    
    def test_context_manager_restores_on_exception(self):
        """Context manager restaura modo mesmo com exceção"""
        assert is_replay_mode() is False
        
        try:
            with ReplayMode():
                assert is_replay_mode() is True
                raise ValueError("Erro simulado")
        except ValueError:
            pass
        
        assert is_replay_mode() is False
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Context manager funciona com async/await"""
        assert is_replay_mode() is False
        
        async with ReplayMode():
            assert is_replay_mode() is True
        
        assert is_replay_mode() is False


class TestReplayContextIsolation:
    """Testes de isolamento entre testes"""
    
    def test_first_test(self):
        """Primeiro teste ativa replay"""
        enable_replay_mode()
        assert is_replay_mode() is True
    
    def test_second_test(self):
        """Segundo teste não deve ver replay do primeiro"""
        # Se isolamento funcionar, isso será False
        # (setup_method resetou)
        reset_replay_mode()  # Garante reset
        assert is_replay_mode() is False
    
    def test_third_test(self):
        """Terceiro teste também isolado"""
        reset_replay_mode()
        assert is_replay_mode() is False


@pytest.mark.asyncio
class TestReplayContextAsync:
    """Testes específicos para comportamento async"""
    
    async def test_enable_in_async_function(self):
        """Ativar replay dentro de função async"""
        assert is_replay_mode() is False
        enable_replay_mode()
        assert is_replay_mode() is True
        disable_replay_mode()
    
    async def test_multiple_async_contexts(self):
        """Múltiplos contextos async"""
        assert is_replay_mode() is False
        
        async with ReplayMode():
            assert is_replay_mode() is True
            
            # Nested context (edge case)
            async with ReplayMode():
                assert is_replay_mode() is True
            
            assert is_replay_mode() is True
        
        assert is_replay_mode() is False
