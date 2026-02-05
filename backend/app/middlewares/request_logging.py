"""
Middleware de logging de requests
Loga método, path, status_code e tempo de resposta
NÃO loga body nem headers sensíveis (segurança)
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.utils.logger import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging estruturado de requests HTTP"""
    
    async def dispatch(self, request: Request, call_next):
        # Capturar timestamp de início
        start_time = time.time()
        
        # Processar request
        response = await call_next(request)
        
        # Calcular tempo de resposta (em ms)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        # Log estruturado (INFO)
        logger.info(
            event="http_request",
            message=f"{request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None
        )
        
        return response
