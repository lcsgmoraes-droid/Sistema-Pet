"""
Guardião de Side Effects - Fase 5.1 Fundação

Suprime side effects (emails, notificações, integrações externas) durante replay.
Fornece decorators e wrappers para proteger funções de side effects.

IMPORTANTE:
- Side effects NÃO devem executar durante replay
- Emissão de eventos durante replay é PROIBIDA e gera erro
- Logs estruturados informam sobre supressões
"""

from functools import wraps
from typing import Any, Callable, TypeVar, Optional
import logging

from app.core.replay_context import is_replay_mode

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ReplayViolationError(Exception):
    """
    Exceção lançada quando uma operação proibida é tentada durante replay.

    Exemplos de violações:
    - Tentar emitir novo evento de domínio
    - Modificar write model
    - Operações irreversíveis sem guarda
    """

    pass


def suppress_in_replay(
    func: Callable[..., T],
    *,
    log_level: str = "INFO",
    custom_message: Optional[str] = None,
) -> Callable[..., Optional[T]]:
    """
    Decorator que suprime a execução de uma função durante modo replay.

    Args:
        func: Função a ser protegida
        log_level: Nível de log para supressão (INFO, DEBUG, WARNING)
        custom_message: Mensagem customizada de log

    Returns:
        Wrapper que executa a função apenas se NÃO estiver em replay

    Example:
        >>> @suppress_in_replay
        ... async def send_email(to: str, subject: str):
        ...     # Envia email
        ...     pass
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> Optional[T]:
        if is_replay_mode():
            msg = custom_message or f"Side effect suprimido: {func.__name__}"
            getattr(logger, log_level.lower())(
                f"🚫 {msg}",
                extra={
                    "function": func.__name__,
                    "replay_mode": True,
                    "args": str(args)[:100],  # Trunca para não logar dados sensíveis
                },
            )
            return None

        return await func(*args, **kwargs)

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> Optional[T]:
        if is_replay_mode():
            msg = custom_message or f"Side effect suprimido: {func.__name__}"
            getattr(logger, log_level.lower())(
                f"🚫 {msg}",
                extra={
                    "function": func.__name__,
                    "replay_mode": True,
                    "args": str(args)[:100],
                },
            )
            return None

        return func(*args, **kwargs)

    # Detecta se função é async ou sync
    import inspect

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def forbid_in_replay(
    func: Callable[..., T], *, error_message: Optional[str] = None
) -> Callable[..., T]:
    """
    Decorator que PROÍBE a execução de uma função durante replay.

    Diferente de suppress_in_replay, este LANÇA ERRO se chamado em replay.
    Usado para operações que NUNCA devem ocorrer durante replay.

    Args:
        func: Função a ser protegida
        error_message: Mensagem de erro customizada

    Returns:
        Wrapper que lança ReplayViolationError se em modo replay

    Example:
        >>> @forbid_in_replay
        ... async def emit_domain_event(event):
        ...     # Emite evento
        ...     pass
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> T:
        if is_replay_mode():
            msg = error_message or f"Operação proibida durante replay: {func.__name__}"
            logger.error(
                f"❌ VIOLAÇÃO DE REPLAY: {msg}",
                extra={
                    "function": func.__name__,
                    "replay_mode": True,
                },
            )
            raise ReplayViolationError(msg)

        return await func(*args, **kwargs)

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> T:
        if is_replay_mode():
            msg = error_message or f"Operação proibida durante replay: {func.__name__}"
            logger.error(
                f"❌ VIOLAÇÃO DE REPLAY: {msg}",
                extra={
                    "function": func.__name__,
                    "replay_mode": True,
                },
            )
            raise ReplayViolationError(msg)

        return func(*args, **kwargs)

    # Detecta se função é async ou sync
    import inspect

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# =====================================
# FUNÇÕES GUARDADAS PRONTAS PARA USO
# =====================================


@suppress_in_replay
async def send_email_guarded(
    to: str, subject: str, body: str, **kwargs
) -> Optional[bool]:
    """
    Wrapper guardado para envio de email.

    Durante replay: suprimido (retorna None)
    Durante produção: delega para implementação real

    NOTA: Esta é uma função placeholder. Integrar com serviço real de email.
    """
    logger.info(f"📧 Enviando email para {to}: {subject}")
    # TODO: Integrar com serviço real (SendGrid, AWS SES, etc)
    return True


@suppress_in_replay
async def send_notification_guarded(
    user_id: str, notification_type: str, message: str, **kwargs
) -> Optional[bool]:
    """
    Wrapper guardado para envio de notificações.

    Durante replay: suprimido (retorna None)
    Durante produção: delega para implementação real
    """
    logger.info(f"🔔 Notificação para {user_id}: {notification_type} - {message}")
    # TODO: Integrar com sistema de notificações
    return True


@suppress_in_replay
async def call_external_api_guarded(
    url: str, method: str = "GET", **kwargs
) -> Optional[dict]:
    """
    Wrapper guardado para chamadas a APIs externas.

    Durante replay: suprimido (retorna None)
    Durante produção: delega para implementação real
    """
    logger.info(f"🌐 Chamando API externa: {method} {url}")
    # TODO: Integrar com httpx/aiohttp
    return None


@forbid_in_replay
async def emit_domain_event_guarded(event: Any) -> None:
    """
    Wrapper guardado para emissão de eventos de domínio.

    Durante replay: LANÇA ERRO (ReplayViolationError)
    Durante produção: delega para event bus

    IMPORTANTE: Eventos nunca devem ser emitidos durante replay!
    """
    logger.info(f"📤 Emitindo evento de domínio: {event.__class__.__name__}")
    # TODO: Integrar com event bus real
    pass


@forbid_in_replay
async def modify_write_model_guarded(operation: str, **kwargs) -> None:
    """
    Wrapper guardado para modificações no write model.

    Durante replay: LANÇA ERRO (ReplayViolationError)
    Durante produção: permite operação

    IMPORTANTE: Write model é READ-ONLY durante replay!
    """
    logger.warning(f"⚠️ Modificação de write model: {operation}")
    raise NotImplementedError("Implementar proteção específica para write model")


# =====================================
# HELPERS
# =====================================


def is_side_effect_suppressed(func: Callable) -> bool:
    """
    Verifica se uma função está protegida contra replay.

    Útil para debugging e validação de handlers.
    """
    return hasattr(func, "__wrapped__") or hasattr(func, "__name__")


def get_suppressed_side_effects_count() -> int:
    """
    Retorna contador de side effects suprimidos (para métricas).

    TODO: Implementar contador global thread-safe se necessário.
    """
    return 0  # Placeholder
