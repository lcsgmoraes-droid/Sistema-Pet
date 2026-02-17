"""
Serviço de Feature Flags com cache em memória.

Permite verificar se features estão ativas para um tenant específico,
com cache de curta duração para otimizar performance.

Regra crítica: Sempre retorna False se a flag não existir,
garantindo que o sistema nunca dependa de features experimentais para funcionar.
"""
import time
from typing import Dict, Tuple, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models import FeatureFlag


class FeatureFlagCache:
    """
    Cache em memória para feature flags com TTL (Time To Live).
    
    Estrutura: {(tenant_id, feature_key): (enabled, timestamp)}
    TTL padrão: 30 segundos
    """
    
    def __init__(self, ttl_seconds: int = 30):
        self._cache: Dict[Tuple[UUID, str], Tuple[bool, float]] = {}
        self._ttl = ttl_seconds
    
    def get(self, tenant_id: UUID, feature_key: str) -> Optional[bool]:
        """
        Recupera valor do cache se ainda válido.
        
        Returns:
            bool: Status da feature se encontrada e válida
            None: Se não encontrada ou expirada
        """
        cache_key = (tenant_id, feature_key)
        if cache_key not in self._cache:
            return None
        
        enabled, timestamp = self._cache[cache_key]
        
        # Verifica se expirou
        if time.time() - timestamp > self._ttl:
            del self._cache[cache_key]
            return None
        
        return enabled
    
    def set(self, tenant_id: UUID, feature_key: str, enabled: bool) -> None:
        """Armazena valor no cache com timestamp atual."""
        cache_key = (tenant_id, feature_key)
        self._cache[cache_key] = (enabled, time.time())
    
    def invalidate(self, tenant_id: UUID, feature_key: str) -> None:
        """Remove entrada específica do cache."""
        cache_key = (tenant_id, feature_key)
        self._cache.pop(cache_key, None)
    
    def clear(self) -> None:
        """Limpa todo o cache."""
        self._cache.clear()


# Instância global do cache
_feature_flag_cache = FeatureFlagCache(ttl_seconds=30)


def is_feature_enabled(
    db: Session,
    tenant_id: UUID,
    feature_key: str,
    use_cache: bool = True
) -> bool:
    """
    Verifica se uma feature está ativa para um tenant específico.
    
    Args:
        db: Sessão do banco de dados
        tenant_id: UUID do tenant
        feature_key: Identificador da feature (ex: "PDV_IA_OPORTUNIDADES")
        use_cache: Se True, usa cache em memória (padrão: True)
    
    Returns:
        bool: True se feature está ativa, False caso contrário
        
    Comportamento crítico:
        - Retorna False por padrão se flag não existir no banco
        - Retorna False se tenant_id for None
        - Nunca lança exceção
        - Cache de 30 segundos para otimizar performance
    
    Exemplos:
        >>> is_feature_enabled(db, tenant_id, "PDV_IA_OPORTUNIDADES")
        False  # Feature não existe ou está desligada
        
        >>> is_feature_enabled(db, tenant_id, "PDV_IA_OPORTUNIDADES")
        True  # Feature existe e está ativa
    """
    # Validação de entrada
    if tenant_id is None:
        return False
    
    # Tenta buscar do cache primeiro
    if use_cache:
        cached_value = _feature_flag_cache.get(tenant_id, feature_key)
        if cached_value is not None:
            return cached_value
    
    try:
        # Busca no banco de dados
        feature_flag = db.query(FeatureFlag).filter(
            FeatureFlag.tenant_id == tenant_id,
            FeatureFlag.feature_key == feature_key
        ).first()
        
        # Se não existe, retorna False por padrão (fail-safe)
        if feature_flag is None:
            enabled = False
        else:
            enabled = feature_flag.enabled
        
        # Armazena no cache
        if use_cache:
            _feature_flag_cache.set(tenant_id, feature_key, enabled)
        
        return enabled
    
    except Exception:
        # Em caso de erro (banco indisponível, etc), retorna False
        # Garante que o sistema funcione mesmo sem acesso ao banco
        return False


def set_feature_flag(
    db: Session,
    tenant_id: UUID,
    feature_key: str,
    enabled: bool
) -> FeatureFlag:
    """
    Cria ou atualiza uma feature flag para um tenant.
    
    Args:
        db: Sessão do banco de dados
        tenant_id: UUID do tenant
        feature_key: Identificador da feature
        enabled: Status desejado (True/False)
    
    Returns:
        FeatureFlag: Objeto criado ou atualizado
        
    Note:
        Automaticamente invalida o cache para essa flag.
    """
    # Busca flag existente
    feature_flag = db.query(FeatureFlag).filter(
        FeatureFlag.tenant_id == tenant_id,
        FeatureFlag.feature_key == feature_key
    ).first()
    
    if feature_flag:
        # Atualiza existente
        feature_flag.enabled = enabled
    else:
        # Cria nova
        feature_flag = FeatureFlag(
            tenant_id=tenant_id,
            feature_key=feature_key,
            enabled=enabled
        )
        db.add(feature_flag)
    
    db.commit()
    db.refresh(feature_flag)
    
    # Invalida cache
    _feature_flag_cache.invalidate(tenant_id, feature_key)
    
    return feature_flag


def get_all_feature_flags(db: Session, tenant_id: UUID) -> Dict[str, bool]:
    """
    Retorna todas as feature flags de um tenant como dicionário.
    
    Args:
        db: Sessão do banco de dados
        tenant_id: UUID do tenant
    
    Returns:
        Dict[str, bool]: Dicionário {feature_key: enabled}
    """
    flags = db.query(FeatureFlag).filter(
        FeatureFlag.tenant_id == tenant_id
    ).all()
    
    return {flag.feature_key: flag.enabled for flag in flags}


def clear_cache() -> None:
    """
    Limpa todo o cache de feature flags.
    
    Útil para testes ou quando houver atualização em massa de flags.
    """
    _feature_flag_cache.clear()
