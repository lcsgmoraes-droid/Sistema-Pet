"""
Rate Limiting Middleware - FASE 8.3
Proteção contra brute force e spam em rotas sensíveis

LIMITAÇÕES CONHECIDAS:
- In-memory (não persiste entre restarts)
- Não funciona em multi-process/cluster (usar Redis em prod)
- Janela fixa (não sliding window)

CONFIGURAÇÃO:
- Edite RATE_LIMIT_MAX e RATE_LIMIT_WINDOW para ajustar
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from fastapi.responses import JSONResponse


# ============================================================================
# CONFIGURAÇÃO DE RATE LIMIT
# ============================================================================

RATE_LIMIT_MAX = 10      # Máximo de requests por janela
RATE_LIMIT_WINDOW = 60   # Janela em segundos (60s = 1 minuto)

# Rotas protegidas (aplicar rate limit)
PROTECTED_ROUTES = [
    "/auth/login-multitenant",
    "/auth/login",
    "/auth/refresh",
    "/auth/select-tenant"
]

# Rotas excluídas (NUNCA aplicar rate limit)
EXCLUDED_ROUTES = [
    "/health",
    "/ready",
    "/docs",
    "/openapi.json",
    "/redoc"
]


# ============================================================================
# STORAGE IN-MEMORY (Dict)
# ============================================================================

class RateLimitStore:
    """
    Armazenamento em memória de contadores de rate limit.
    
    Estrutura:
    {
        "192.168.1.1:/auth/login": (timestamp_inicio, contador),
        ...
    }
    """
    
    def __init__(self):
        self.store: Dict[str, Tuple[float, int]] = {}
    
    def get_key(self, ip: str, path: str) -> str:
        """Gera chave única para IP + path"""
        return f"{ip}:{path}"
    
    def check_limit(self, ip: str, path: str) -> Tuple[bool, int]:
        """
        Verifica se IP excedeu limite para o path.
        
        Returns:
            (is_allowed, remaining_requests)
        """
        key = self.get_key(ip, path)
        now = time.time()
        
        # Buscar entrada existente
        if key in self.store:
            window_start, count = self.store[key]
            
            # Janela expirou? Resetar
            if now - window_start >= RATE_LIMIT_WINDOW:
                self.store[key] = (now, 1)
                return True, RATE_LIMIT_MAX - 1
            
            # Dentro da janela
            if count >= RATE_LIMIT_MAX:
                return False, 0  # Limite excedido
            
            # Incrementar contador
            self.store[key] = (window_start, count + 1)
            return True, RATE_LIMIT_MAX - (count + 1)
        
        # Primeira request nesta janela
        self.store[key] = (now, 1)
        return True, RATE_LIMIT_MAX - 1
    
    def cleanup_expired(self):
        """Remove entradas expiradas (executar periodicamente)"""
        now = time.time()
        expired_keys = [
            key for key, (window_start, _) in self.store.items()
            if now - window_start >= RATE_LIMIT_WINDOW * 2  # 2x para segurança
        ]
        for key in expired_keys:
            del self.store[key]


# Instância global do store
rate_limit_store = RateLimitStore()


# ============================================================================
# MIDDLEWARE DE RATE LIMIT
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de rate limiting por IP para rotas sensíveis.
    
    Aplica SOMENTE em rotas de autenticação.
    Exclui explicitamente health checks e docs.
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Excluir rotas explicitamente
        if any(path.startswith(excluded) for excluded in EXCLUDED_ROUTES):
            return await call_next(request)
        
        # Aplicar rate limit somente em rotas protegidas
        if not any(path.startswith(protected) for protected in PROTECTED_ROUTES):
            return await call_next(request)
        
        # Extrair IP do cliente
        client_ip = request.client.host if request.client else "unknown"
        
        # Verificar limite
        is_allowed, remaining = rate_limit_store.check_limit(client_ip, path)
        
        if not is_allowed:
            # Rate limit excedido - retornar 429
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "message": f"Limite de {RATE_LIMIT_MAX} requisições por {RATE_LIMIT_WINDOW}s excedido. Aguarde e tente novamente."
                },
                headers={
                    "Retry-After": str(RATE_LIMIT_WINDOW),
                    "X-RateLimit-Limit": str(RATE_LIMIT_MAX),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + RATE_LIMIT_WINDOW)
                }
            )
        
        # Request permitida - processar
        response = await call_next(request)
        
        # Adicionar headers de rate limit
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_MAX)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
