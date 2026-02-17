"""
Sistema de logging estruturado com trace_id por request
Permite rastreamento completo de requisições em produção
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
import sys

# ============================================================================
# CONFIGURAÇÃO GLOBAL DE LOGGING (PRODUÇÃO)
# ============================================================================

def configure_logging():
    """
    Configura logging estruturado global para produção
    Formato: timestamp, level, logger, message (JSON-like)
    """
    # Configuração básica com formato estruturado
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout,
        force=True  # Força reconfiguração
    )
    
    # Silenciar logs verbosos de terceiros
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Evita duplicação (usamos nosso middleware)

# Context vars para armazenar dados por request
trace_id_ctx: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
user_id_ctx: ContextVar[Optional[int]] = ContextVar('user_id', default=None)
endpoint_ctx: ContextVar[Optional[str]] = ContextVar('endpoint', default=None)


class StructuredLogger:
    """Logger que produz saída estruturada (JSON) com contexto de request"""
    
    def __init__(self, name: str = "pet_shop"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Configura handler se ainda não tiver
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            self.logger.addHandler(handler)
    
    def _build_log_dict(
        self,
        level: str,
        event: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Constrói dicionário estruturado para log"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "event": event,
            "message": message,
            "trace_id": trace_id_ctx.get(),
            "user_id": user_id_ctx.get(),
            "endpoint": endpoint_ctx.get(),
        }
        
        if extra:
            log_data["extra"] = extra
        
        return log_data
    
    def _log(self, level: int, event: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Método interno de log"""
        level_name = logging.getLevelName(level)
        log_dict = self._build_log_dict(level_name, event, message, extra)
        
        # Log como JSON
        log_json = json.dumps(log_dict, ensure_ascii=False, default=str)
        self.logger.log(level, log_json)
    
    def info(self, event_or_message: str = None, message: Optional[str] = None, **kwargs):
        """Log de informação (fluxo normal)"""
        # Compatibilidade: aceita múltiplos formatos de chamada
        if event_or_message is None and 'event' in kwargs:
            # Formato: logger.info(event="x", message="y", ...)
            event = kwargs.pop('event')
            msg = kwargs.pop('message', '')
            self._log(logging.INFO, event, msg, kwargs if kwargs else None)
        elif message is None:
            # Uso simples: logger.info("mensagem")
            self._log(logging.INFO, "info", event_or_message, kwargs if kwargs else None)
        else:
            # Uso estruturado: logger.info("evento", "mensagem")
            self._log(logging.INFO, event_or_message, message, kwargs if kwargs else None)
    
    def warning(self, event_or_message: str = None, message: Optional[str] = None, **kwargs):
        """Log de warning (algo evitado, duplicação, inconsistência)"""
        # Compatibilidade: aceita múltiplos formatos de chamada
        if event_or_message is None and 'event' in kwargs:
            # Formato: logger.warning(event="x", message="y", ...)
            event = kwargs.pop('event')
            msg = kwargs.pop('message', '')
            self._log(logging.WARNING, event, msg, kwargs if kwargs else None)
        elif message is None:
            # Uso simples: logger.warning("mensagem")
            self._log(logging.WARNING, "warning", event_or_message, kwargs if kwargs else None)
        else:
            # Uso estruturado: logger.warning("evento", "mensagem")
            self._log(logging.WARNING, event_or_message, message, kwargs if kwargs else None)
    
    def error(self, event_or_message: str = None, message: Optional[str] = None, **kwargs):
        """Log de erro (exceção, falha técnica)"""
        # Compatibilidade: aceita múltiplos formatos de chamada
        if event_or_message is None and 'event' in kwargs:
            # Formato: logger.error(event="x", message="y", ...)
            event = kwargs.pop('event')
            msg = kwargs.pop('message', '')
            self._log(logging.ERROR, event, msg, kwargs if kwargs else None)
        elif message is None:
            # Uso simples: logger.error("mensagem")
            self._log(logging.ERROR, "error", event_or_message, kwargs if kwargs else None)
        else:
            # Uso estruturado: logger.error("evento", "mensagem")
            self._log(logging.ERROR, event_or_message, message, kwargs if kwargs else None)
    
    def debug(self, event_or_message: str = None, message: Optional[str] = None, **kwargs):
        """Log de debug (desenvolvimento)"""
        # Compatibilidade: aceita múltiplos formatos de chamada
        if event_or_message is None and 'event' in kwargs:
            # Formato: logger.debug(event="x", message="y", ...)
            event = kwargs.pop('event')
            msg = kwargs.pop('message', '')
            self._log(logging.DEBUG, event, msg, kwargs if kwargs else None)
        elif message is None:
            # Uso simples: logger.debug("mensagem")
            self._log(logging.DEBUG, "debug", event_or_message, kwargs if kwargs else None)
        else:
            # Uso estruturado: logger.debug("evento", "mensagem")
            self._log(logging.DEBUG, event_or_message, message, kwargs if kwargs else None)


# Instância global do logger
logger = StructuredLogger("pet_shop")


def set_trace_id(trace_id: str):
    """Define trace_id no contexto da request atual"""
    trace_id_ctx.set(trace_id)


def get_trace_id() -> Optional[str]:
    """Obtém trace_id do contexto da request atual"""
    return trace_id_ctx.get()


def set_user_id(user_id: int):
    """Define user_id no contexto da request atual"""
    user_id_ctx.set(user_id)


def set_endpoint(endpoint: str):
    """Define endpoint no contexto da request atual"""
    endpoint_ctx.set(endpoint)


def generate_trace_id() -> str:
    """Gera novo trace_id único"""
    return str(uuid.uuid4())


def clear_context():
    """Limpa todo o contexto (útil para testes)"""
    trace_id_ctx.set(None)
    user_id_ctx.set(None)
    endpoint_ctx.set(None)
