"""
Request Context Middleware - Pré-Prod Bloco 4
==============================================

Middleware para observabilidade e correlação de logs em produção.

Garante que:
1. Todo request tem request_id único (UUID)
2. request_id é propagado via contextvars
3. request_id é incluído automaticamente em logs
4. Contexto suficiente para diagnóstico (método, path, status, duração)
5. Dados sensíveis NÃO são logados

Autor: Sistema Pet - Pré-Prod Block 4
Data: 2026-02-05
"""

import time
import uuid
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from contextvars import ContextVar
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONTEXTVARS PARA REQUEST_ID E METADATA
# ============================================================================

request_id_ctx: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
request_method_ctx: ContextVar[Optional[str]] = ContextVar('request_method', default=None)
request_path_ctx: ContextVar[Optional[str]] = ContextVar('request_path', default=None)


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def generate_request_id() -> str:
    """
    Gera novo request_id único (UUID4).
    
    Returns:
        String UUID no formato: "a1b2c3d4-e5f6-..."
    """
    return str(uuid.uuid4())


def set_request_id(request_id: str) -> None:
    """Define request_id no contexto da request atual"""
    request_id_ctx.set(request_id)


def get_request_id() -> Optional[str]:
    """Obtém request_id do contexto da request atual"""
    return request_id_ctx.get()


def set_request_metadata(method: str, path: str) -> None:
    """Define metadata da request no contexto"""
    request_method_ctx.set(method)
    request_path_ctx.set(path)


def get_request_metadata() -> dict:
    """Obtém metadata da request do contexto"""
    return {
        'request_id': request_id_ctx.get(),
        'method': request_method_ctx.get(),
        'path': request_path_ctx.get()
    }


def clear_request_context() -> None:
    """Limpa contexto da request após processamento"""
    request_id_ctx.set(None)
    request_method_ctx.set(None)
    request_path_ctx.set(None)


# ============================================================================
# MIDDLEWARE
# ============================================================================

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware para injetar request_id e contexto observável em cada request.
    
    Funcionalidades:
    ----------------
    1. Gera ou aceita request_id via header X-Request-ID
    2. Propaga request_id via contextvars (disponível em toda a stack)
    3. Adiciona request_id aos logs automaticamente
    4. Captura metadata essencial: método, path, status, duração
    5. NÃO loga body ou dados sensíveis (segurança)
    6. Adiciona request_id no header de resposta (rastreabilidade)
    
    Headers:
    --------
    Request:
    - X-Request-ID: (opcional) ID do cliente para correlação
    
    Response:
    - X-Request-ID: ID usado nesta request (para cliente correlacionar)
    
    Logs:
    -----
    Todos os logs dentro desta request terão automaticamente:
    - request_id
    - method
    - path
    
    Exemplo de log:
    {
        "timestamp": "2026-02-05T10:30:15.123Z",
        "level": "INFO",
        "message": "Request completed",
        "request_id": "a1b2c3d4-e5f6-...",
        "method": "GET",
        "path": "/api/clientes/123",
        "status_code": 200,
        "duration_ms": 45.2
    }
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Processa request e injeta contexto observável.
        """
        
        # ============================================================
        # 1️⃣ GERAR OU OBTER REQUEST_ID
        # ============================================================
        
        # Tentar obter request_id de header (cliente pode enviar)
        request_id = request.headers.get('X-Request-ID')
        
        # Se não veio do cliente, gerar novo
        if not request_id:
            request_id = generate_request_id()
        
        # Propagar via contextvars
        set_request_id(request_id)
        
        # ============================================================
        # 2️⃣ CAPTURAR METADATA DA REQUEST
        # ============================================================
        
        method = request.method
        path = request.url.path
        
        # Propagar metadata via contextvars
        set_request_metadata(method, path)
        
        # Timestamp de início (para calcular duração)
        start_time = time.time()
        
        # ============================================================
        # 3️⃣ PROCESSAR REQUEST
        # ============================================================
        
        try:
            response = await call_next(request)
            
            # Calcular duração (em milissegundos)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            # ============================================================
            # 4️⃣ LOGGING ESTRUTURADO (sem dados sensíveis)
            # ============================================================
            
            # Determinar nível de log baseado no status
            if response.status_code >= 500:
                log_level = logging.ERROR
            elif response.status_code >= 400:
                log_level = logging.WARNING
            else:
                log_level = logging.INFO
            
            # Log estruturado com contexto completo
            logger.log(
                log_level,
                "Request completed",
                extra={
                    'request_id': request_id,
                    'method': method,
                    'path': path,
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                    'client_ip': request.client.host if request.client else None,
                    'user_agent': request.headers.get('user-agent', 'unknown')[:100]  # Truncado
                }
            )
            
            # ============================================================
            # 5️⃣ ADICIONAR REQUEST_ID NO HEADER DA RESPOSTA
            # ============================================================
            
            response.headers["X-Request-ID"] = request_id
            
            return response
        
        except Exception as e:
            # Em caso de exceção, ainda logar com contexto
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            logger.error(
                f"Request failed with exception: {type(e).__name__}",
                extra={
                    'request_id': request_id,
                    'method': method,
                    'path': path,
                    'duration_ms': duration_ms,
                    'exception_type': type(e).__name__,
                    'exception_message': str(e)[:200]  # Truncado por segurança
                },
                exc_info=True  # Inclui stack trace nos logs
            )
            
            raise  # Re-raise para FastAPI lidar
        
        finally:
            # ============================================================
            # 6️⃣ LIMPAR CONTEXTO APÓS REQUEST
            # ============================================================
            
            clear_request_context()


# ============================================================================
# LOGGING FILTER (OPCIONAL)
# ============================================================================

class RequestContextFilter(logging.Filter):
    """
    Filtro de logging que adiciona request_id automaticamente a TODOS os logs.
    
    Uso:
    ----
    import logging
    
    handler = logging.StreamHandler()
    handler.addFilter(RequestContextFilter())
    logging.getLogger().addHandler(handler)
    
    Resultado:
    ----------
    Qualquer log feito durante uma request terá request_id automaticamente:
    
    >>> logger.info("Processando pagamento")
    # Output: {"message": "Processando pagamento", "request_id": "a1b2c3d4-..."}
    """
    
    def filter(self, record):
        """Adiciona request_id ao record de log"""
        record.request_id = get_request_id() or '-'
        record.request_method = request_method_ctx.get() or '-'
        record.request_path = request_path_ctx.get() or '-'
        return True


# ============================================================================
# FUNÇÕES DE UTILIDADE
# ============================================================================

def get_current_request_context() -> dict:
    """
    Retorna o contexto completo da request atual.
    
    Útil para:
    - Logging customizado
    - Rastreamento de operações
    - Debug
    
    Returns:
        {
            'request_id': str | None,
            'method': str | None,
            'path': str | None
        }
    
    Example:
        >>> context = get_current_request_context()
        >>> logger.info(f"Processing order", extra=context)
    """
    return get_request_metadata()


def log_with_context(level: int, message: str, **kwargs) -> None:
    """
    Helper para logging com contexto de request automaticamente.
    
    Args:
        level: logging.INFO, logging.WARNING, etc.
        message: Mensagem do log
        **kwargs: Campos extras para o log
    
    Example:
        >>> log_with_context(logging.INFO, "User logged in", user_id=123)
        # Log terá automaticamente request_id, method, path, user_id
    """
    context = get_current_request_context()
    logger.log(level, message, extra={**context, **kwargs})
