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
    
    def info(self, event: str, message: str, **kwargs):
        """Log de informação (fluxo normal)"""
        self._log(logging.INFO, event, message, kwargs if kwargs else None)
    
    def warning(self, event: str, message: str, **kwargs):
        """Log de warning (algo evitado, duplicação, inconsistência)"""
        self._log(logging.WARNING, event, message, kwargs if kwargs else None)
    
    def error(self, event: str, message: str, **kwargs):
        """Log de erro (exceção, falha técnica)"""
        self._log(logging.ERROR, event, message, kwargs if kwargs else None)
    
    def debug(self, event: str, message: str, **kwargs):
        """Log de debug (desenvolvimento)"""
        self._log(logging.DEBUG, event, message, kwargs if kwargs else None)


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
