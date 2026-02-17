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

# Limites por tipo de rota
RATE_LIMIT_AUTH_MAX = 5          # Auth: 5 req/min (brute force protection)
RATE_LIMIT_AUTH_WINDOW = 60

RATE_LIMIT_API_MAX = 100         # APIs: 100 req/min (uso normal)
RATE_LIMIT_API_WINDOW = 60

# Rotas de autenticação (limite mais restritivo)
AUTH_ROUTES = [
    "/auth/login-multitenant",
    "/auth/login",
    "/auth/refresh",
    "/auth/select-tenant"
]

# Rotas de API (limite menos restritivo)
API_ROUTES = [
    "/analytics/",
    "/api/",
    "/vendas/",
    "/produtos/",
    "/clientes/",
    "/funcionarios/",
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
    
    def clear(self):
        """Limpa todos os dados do store (útil para testes)"""
        self.store.clear()
    
    def get_key(self, ip: str, path: str) -> str:
        """Gera chave única para IP + path"""
        return f"{ip}:{path}"
    
    def check_limit(self, ip: str, path: str, max_requests: int, window: int) -> Tuple[bool, int]:
        """
        Verifica se IP excedeu limite para o path.
        
        Args:
            ip: IP do cliente
            path: Path da requisição
            max_requests: Máximo de requisições permitidas
            window: Janela de tempo em segundos
        
        Returns:
            (is_allowed, remaining_requests)
        """
        key = self.get_key(ip, path)
        now = time.time()
        
        # Buscar entrada existente
        if key in self.store:
            window_start, count = self.store[key]
            
            # Janela expirou? Resetar
            if now - window_start >= window:
                self.store[key] = (now, 1)
                return True, max_requests - 1
            
            # Dentro da janela
            if count >= max_requests:
                return False, 0  # Limite excedido
            
            # Incrementar contador
            self.store[key] = (window_start, count + 1)
            return True, max_requests - (count + 1)
        
        # Primeira request nesta janela
        self.store[key] = (now, 1)
        return True, max_requests - 1
    
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
    Middleware de rate limiting por IP com limites diferenciados.
    
    Limites:
    - Autenticação: 5 req/min (proteção contra brute force)
    - APIs gerais: 100 req/min (uso normal)
    
    Exclui: health checks, docs.
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Excluir rotas explicitamente
        if any(path.startswith(excluded) for excluded in EXCLUDED_ROUTES):
            return await call_next(request)
        
        # Determinar tipo de rota e limites
        max_requests = None
        window = None
        route_type = None
        
        # Rotas de autenticação (limite restritivo)
        if any(path.startswith(auth_route) for auth_route in AUTH_ROUTES):
            max_requests = RATE_LIMIT_AUTH_MAX
            window = RATE_LIMIT_AUTH_WINDOW
            route_type = "auth"
        
        # Rotas de API (limite normal)
        elif any(path.startswith(api_route) for api_route in API_ROUTES):
            max_requests = RATE_LIMIT_API_MAX
            window = RATE_LIMIT_API_WINDOW
            route_type = "api"
        
        # Sem rate limit para outras rotas
        if max_requests is None:
            return await call_next(request)
        
        # Extrair IP do cliente
        client_ip = request.client.host if request.client else "unknown"
        
        # Verificar limite
        is_allowed, remaining = rate_limit_store.check_limit(
            client_ip, path, max_requests, window
        )
        
        if not is_allowed:
            # Rate limit excedido - retornar 429
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Limite de {max_requests} requisições por minuto excedido. Aguarde e tente novamente.",
                    "retry_after": window
                },
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + window)
                }
            )
        
        # Request permitida - processar
        response = await call_next(request)
        
        # Adicionar headers de rate limit
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
