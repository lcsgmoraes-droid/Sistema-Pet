"""
Cost Control - Controle de Custo de IA

Gerencia limites de custo por tenant para evitar gastos excessivos.

FUNCIONALIDADES:
- Limite diário por tenant
- Soft limit (aviso)
- Hard limit (bloqueio)
- Log de consumo
- Reset automático diário
"""

import logging
from typing import Dict, Optional
from datetime import datetime, date
from dataclasses import dataclass, field

from app.ai.settings import AISettings


logger = logging.getLogger(__name__)


@dataclass
class TenantUsage:
    """
    Uso de IA por tenant em um dia específico.
    
    Atributos:
        tenant_id: ID do tenant
        date: Data do uso
        total_tokens: Total de tokens consumidos
        total_cost_usd: Custo total em USD
        request_count: Número de requests
        last_updated: Última atualização
    """
    tenant_id: int
    date: date
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    request_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def add_usage(self, tokens: int, cost: float):
        """Adiciona uso"""
        self.total_tokens += tokens
        self.total_cost_usd += cost
        self.request_count += 1
        self.last_updated = datetime.now()
    
    def is_over_limit(self, limit_usd: float) -> bool:
        """Verifica se excedeu o limite"""
        return self.total_cost_usd >= limit_usd
    
    def is_near_limit(self, limit_usd: float, threshold: float = 0.8) -> bool:
        """Verifica se está próximo do limite"""
        return self.total_cost_usd >= (limit_usd * threshold)
    
    def get_percentage_used(self, limit_usd: float) -> float:
        """Retorna percentual usado do limite"""
        if limit_usd == 0:
            return 0.0
        return (self.total_cost_usd / limit_usd) * 100


class CostController:
    """
    Controlador de custo de IA.
    
    Gerencia limites por tenant e previne gastos excessivos.
    """
    
    def __init__(
        self,
        daily_limit_usd: float = None,
        warning_threshold: float = None
    ):
        """
        Inicializa o controlador.
        
        Args:
            daily_limit_usd: Limite diário em USD (usa settings se None)
            warning_threshold: Threshold para aviso (usa settings se None)
        """
        self.daily_limit_usd = daily_limit_usd or AISettings.DAILY_COST_LIMIT_USD
        self.warning_threshold = warning_threshold or AISettings.COST_WARNING_THRESHOLD
        
        # Cache em memória (em produção, usar Redis)
        self._usage_cache: Dict[str, TenantUsage] = {}
        
        logger.info(
            f"[CostController] Inicializado com limite diário de ${self.daily_limit_usd:.2f}"
        )
    
    def _get_cache_key(self, tenant_id: int, date_obj: date) -> str:
        """Gera chave de cache"""
        return f"tenant_{tenant_id}_date_{date_obj.isoformat()}"
    
    def _get_usage(self, tenant_id: int, date_obj: date = None) -> TenantUsage:
        """
        Obtém uso do tenant para uma data.
        
        Args:
            tenant_id: ID do tenant
            date_obj: Data (hoje se None)
            
        Returns:
            TenantUsage
        """
        if date_obj is None:
            date_obj = date.today()
        
        cache_key = self._get_cache_key(tenant_id, date_obj)
        
        if cache_key not in self._usage_cache:
            self._usage_cache[cache_key] = TenantUsage(
                tenant_id=tenant_id,
                date=date_obj
            )
        
        return self._usage_cache[cache_key]
    
    def check_can_proceed(
        self,
        tenant_id: int,
        estimated_tokens: int,
        estimated_cost: float
    ) -> tuple[bool, Optional[str]]:
        """
        Verifica se pode proceder com a operação.
        
        Args:
            tenant_id: ID do tenant
            estimated_tokens: Tokens estimados
            estimated_cost: Custo estimado
            
        Returns:
            (pode_proceder, mensagem_erro)
        """
        usage = self._get_usage(tenant_id)
        
        # Verificar hard limit
        if usage.is_over_limit(self.daily_limit_usd):
            msg = (
                f"Limite diário de custo excedido para tenant {tenant_id}. "
                f"Usado: ${usage.total_cost_usd:.2f} / ${self.daily_limit_usd:.2f}"
            )
            logger.warning(f"[CostController] {msg}")
            return False, msg
        
        # Verificar se a próxima operação excederia o limite
        projected_cost = usage.total_cost_usd + estimated_cost
        if projected_cost > self.daily_limit_usd:
            msg = (
                f"Operação excederia limite diário para tenant {tenant_id}. "
                f"Projetado: ${projected_cost:.2f} / ${self.daily_limit_usd:.2f}"
            )
            logger.warning(f"[CostController] {msg}")
            return False, msg
        
        # Verificar soft limit (aviso)
        if usage.is_near_limit(self.daily_limit_usd, self.warning_threshold):
            percentage = usage.get_percentage_used(self.daily_limit_usd)
            logger.warning(
                f"[CostController] Tenant {tenant_id} está em {percentage:.1f}% "
                f"do limite diário (${usage.total_cost_usd:.2f} / ${self.daily_limit_usd:.2f})"
            )
        
        return True, None
    
    def record_usage(
        self,
        tenant_id: int,
        tokens_used: int,
        cost_usd: float
    ):
        """
        Registra uso de IA.
        
        Args:
            tenant_id: ID do tenant
            tokens_used: Tokens consumidos
            cost_usd: Custo em USD
        """
        usage = self._get_usage(tenant_id)
        usage.add_usage(tokens_used, cost_usd)
        
        logger.info(
            f"[CostController] Tenant {tenant_id} - "
            f"Tokens: {tokens_used}, Custo: ${cost_usd:.4f}, "
            f"Total hoje: ${usage.total_cost_usd:.2f}"
        )
    
    def get_usage_summary(self, tenant_id: int) -> dict:
        """
        Retorna resumo de uso do tenant.
        
        Args:
            tenant_id: ID do tenant
            
        Returns:
            Dicionário com estatísticas
        """
        usage = self._get_usage(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "date": usage.date.isoformat(),
            "total_tokens": usage.total_tokens,
            "total_cost": usage.total_cost_usd,  # Alias
            "total_cost_usd": usage.total_cost_usd,
            "request_count": usage.request_count,
            "limit_usd": self.daily_limit_usd,
            "usage_percent": usage.get_percentage_used(self.daily_limit_usd),  # Alias
            "percentage_used": usage.get_percentage_used(self.daily_limit_usd),
            "is_over_limit": usage.is_over_limit(self.daily_limit_usd),
            "is_near_limit": usage.is_near_limit(
                self.daily_limit_usd,
                self.warning_threshold
            ),
            "last_updated": usage.last_updated.isoformat()
        }
    
    def reset_usage(self, tenant_id: int, date_obj: date = None):
        """
        Reseta uso de um tenant (útil para testes).
        
        Args:
            tenant_id: ID do tenant
            date_obj: Data (hoje se None)
        """
        if date_obj is None:
            date_obj = date.today()
        
        cache_key = self._get_cache_key(tenant_id, date_obj)
        if cache_key in self._usage_cache:
            del self._usage_cache[cache_key]
        
        logger.info(f"[CostController] Reset de uso para tenant {tenant_id}")
    
    def cleanup_old_entries(self, days_to_keep: int = 7):
        """
        Limpa entradas antigas do cache.
        
        Em produção, isso seria feito pelo Redis com TTL.
        
        Args:
            days_to_keep: Quantos dias manter
        """
        today = date.today()
        keys_to_remove = []
        
        for key, usage in self._usage_cache.items():
            age_days = (today - usage.date).days
            if age_days > days_to_keep:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._usage_cache[key]
        
        if keys_to_remove:
            logger.info(
                f"[CostController] Removidas {len(keys_to_remove)} entradas antigas"
            )


# Instância singleton (em produção, injetar via DI)
_cost_controller_instance: Optional[CostController] = None


def get_cost_controller() -> CostController:
    """
    Retorna instância singleton do controlador de custo.
    
    Returns:
        CostController
    """
    global _cost_controller_instance
    if _cost_controller_instance is None:
        _cost_controller_instance = CostController()
    return _cost_controller_instance
