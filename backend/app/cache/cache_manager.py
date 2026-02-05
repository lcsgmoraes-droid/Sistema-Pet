"""
Cache Manager - Abstração de Cache

Suporta:
- In-Memory (MVP) - funciona sem Redis
- Redis (Produção) - migração transparente

Uso:
    from app.cache.cache_manager import cache
    
    @cache.cached(ttl=300)
    async def get_produtos_populares(tenant_id):
        return await db.query(...)
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
import json
import os
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# ABSTRACT CACHE
# ============================================================================

class CacheBackend(ABC):
    """Interface abstrata de cache"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Buscar valor no cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Armazenar valor no cache"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Deletar valor do cache"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Limpar todo o cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Verificar se chave existe"""
        pass


# ============================================================================
# IN-MEMORY CACHE (MVP)
# ============================================================================

class InMemoryCache(CacheBackend):
    """
    Cache em memória (processo atual).
    
    Vantagens:
    - Zero configuração
    - Zero infra adicional
    - Perfeito para MVP
    
    Limitações:
    - Não compartilhado entre workers
    - Perdido ao reiniciar
    - Cresce com uso de memória
    """
    
    def __init__(self):
        self._cache: dict = {}
        self._timestamps: dict = {}
        self._max_size = 1000  # Limite de segurança
        logger.info("✅ InMemoryCache inicializado (MVP mode)")
    
    async def get(self, key: str) -> Optional[Any]:
        """Buscar no cache"""
        if key in self._cache:
            # Verificar TTL
            expires_at = self._timestamps.get(key)
            if expires_at and datetime.now() < expires_at:
                return self._cache[key]
            else:
                # Expirou
                await self.delete(key)
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Armazenar no cache"""
        try:
            # Proteção contra crescimento infinito
            if len(self._cache) >= self._max_size and key not in self._cache:
                # Remover item mais antigo
                oldest_key = min(self._timestamps, key=self._timestamps.get)
                await self.delete(oldest_key)
            
            self._cache[key] = value
            self._timestamps[key] = datetime.now() + timedelta(seconds=ttl)
            return True
        except Exception as e:
            logger.error(f"Erro ao armazenar no cache: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Deletar do cache"""
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]
        return True
    
    async def clear(self) -> bool:
        """Limpar cache"""
        self._cache.clear()
        self._timestamps.clear()
        logger.info("Cache limpo")
        return True
    
    async def exists(self, key: str) -> bool:
        """Verificar existência"""
        value = await self.get(key)
        return value is not None
    
    def stats(self) -> dict:
        """Estatísticas do cache"""
        now = datetime.now()
        expired = sum(1 for exp in self._timestamps.values() if exp < now)
        return {
            "total_keys": len(self._cache),
            "expired_keys": expired,
            "active_keys": len(self._cache) - expired,
            "max_size": self._max_size
        }


# ============================================================================
# REDIS CACHE (PRODUÇÃO)
# ============================================================================

class RedisCache(CacheBackend):
    """
    Cache Redis (produção).
    
    Vantagens:
    - Compartilhado entre workers
    - Persiste entre restarts (opcional)
    - Alta performance
    
    Requer:
    - REDIS_URL no .env
    - redis-py instalado
    """
    
    def __init__(self, redis_url: str):
        try:
            import redis.asyncio as aioredis
            self.redis = aioredis.from_url(redis_url, decode_responses=True)
            logger.info(f"✅ RedisCache conectado: {redis_url}")
        except ImportError:
            raise ImportError("redis-py não instalado. Execute: pip install redis")
        except Exception as e:
            logger.error(f"Erro ao conectar Redis: {e}")
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """Buscar no Redis"""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar do Redis: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Armazenar no Redis"""
        try:
            serialized = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Erro ao armazenar no Redis: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Deletar do Redis"""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar do Redis: {e}")
            return False
    
    async def clear(self) -> bool:
        """Limpar Redis (cuidado!)"""
        try:
            await self.redis.flushdb()
            logger.warning("Redis flushdb executado")
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar Redis: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Verificar existência"""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Erro ao verificar existência: {e}")
            return False


# ============================================================================
# CACHE MANAGER (Singleton)
# ============================================================================

class CacheManager:
    """
    Gerenciador de cache com seleção automática de backend.
    
    Usa Redis se REDIS_URL estiver configurado, senão in-memory.
    """
    
    def __init__(self):
        redis_url = os.getenv("REDIS_URL")
        
        if redis_url:
            try:
                self.backend = RedisCache(redis_url)
                self.backend_type = "redis"
            except Exception as e:
                logger.warning(f"Redis não disponível: {e}. Usando in-memory cache.")
                self.backend = InMemoryCache()
                self.backend_type = "in-memory"
        else:
            self.backend = InMemoryCache()
            self.backend_type = "in-memory"
        
        logger.info(f"🗄️ Cache Manager inicializado: {self.backend_type}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Buscar valor"""
        return await self.backend.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Armazenar valor"""
        return await self.backend.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Deletar valor"""
        return await self.backend.delete(key)
    
    async def clear(self) -> bool:
        """Limpar cache"""
        return await self.backend.clear()
    
    async def exists(self, key: str) -> bool:
        """Verificar existência"""
        return await self.backend.exists(key)
    
    def cached(self, ttl: int = 300, key_prefix: str = ""):
        """
        Decorator para cachear resultados de função.
        
        Uso:
            @cache.cached(ttl=300, key_prefix="produtos")
            async def get_produtos(tenant_id):
                return await db.query(...)
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Gerar chave do cache
                cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
                
                # Tentar buscar do cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached_value
                
                # Cache miss - executar função
                logger.debug(f"Cache MISS: {cache_key}")
                result = await func(*args, **kwargs)
                
                # Armazenar no cache
                await self.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def get_stats(self) -> dict:
        """Estatísticas do cache"""
        stats = {
            "backend": self.backend_type
        }
        
        if hasattr(self.backend, "stats"):
            stats.update(self.backend.stats())
        
        return stats


# ============================================================================
# SINGLETON GLOBAL
# ============================================================================

cache = CacheManager()
