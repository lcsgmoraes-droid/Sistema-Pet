"""
Contexto de Replay - Fase 5.1 Fundação

Gerencia o estado de "modo replay" usando ContextVar para garantir
isolamento em ambientes assíncronos sem usar variáveis globais.

IMPORTANTE:
- ContextVar é compatível com asyncio
- Cada task/request tem seu próprio contexto
- Não há vazamento entre testes ou requests
"""

from contextvars import ContextVar
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ContextVar para modo replay - default False (produção)
_replay_mode: ContextVar[bool] = ContextVar('replay_mode', default=False)


def is_replay_mode() -> bool:
    """
    Verifica se o sistema está em modo replay.
    
    Returns:
        bool: True se em modo replay, False caso contrário
        
    Example:
        >>> if is_replay_mode():
        ...     logger.info("Suprimindo side effects")
    """
    return _replay_mode.get()


def enable_replay_mode() -> None:
    """
    Ativa o modo replay no contexto atual.
    
    IMPORTANTE: Deve ser chamado APENAS pela Replay Engine.
    Uso fora da engine pode causar comportamento inesperado.
    
    Example:
        >>> enable_replay_mode()
        >>> assert is_replay_mode() == True
    """
    _replay_mode.set(True)
    logger.info("🔄 Modo replay ATIVADO - Side effects serão suprimidos")


def disable_replay_mode() -> None:
    """
    Desativa o modo replay no contexto atual.
    
    Retorna ao comportamento normal de produção.
    
    Example:
        >>> disable_replay_mode()
        >>> assert is_replay_mode() == False
    """
    _replay_mode.set(False)
    logger.info("✅ Modo replay DESATIVADO - Operações normais retomadas")


def reset_replay_mode() -> None:
    """
    Reset do contexto de replay para o valor padrão (False).
    
    Útil em testes para garantir isolamento entre casos de teste.
    
    Example:
        >>> # Em teardown de testes
        >>> reset_replay_mode()
    """
    _replay_mode.set(False)


class ReplayMode:
    """
    Context manager para ativar temporariamente o modo replay.
    
    Garante que o modo seja desativado mesmo em caso de exceção.
    
    Example:
        >>> async with ReplayMode():
        ...     # Código executado em modo replay
        ...     await process_events(events)
        >>> # Modo replay desativado automaticamente
    """
    
    def __init__(self):
        self._previous_mode: Optional[bool] = None
    
    def __enter__(self):
        """Ativa modo replay ao entrar no contexto"""
        self._previous_mode = is_replay_mode()
        enable_replay_mode()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restaura modo anterior ao sair do contexto"""
        if self._previous_mode:
            enable_replay_mode()
        else:
            disable_replay_mode()
        return False
    
    async def __aenter__(self):
        """Versão assíncrona do __enter__"""
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Versão assíncrona do __exit__"""
        return self.__exit__(exc_type, exc_val, exc_tb)
