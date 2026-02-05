"""
Interface base para motores de decisão
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from ..domain.context import DecisionContext
from ..domain.decision import DecisionResult


class DecisionEngine(ABC):
    """
    Interface base para motores de decisão.
    
    Cada motor implementa uma estratégia diferente:
    - RuleEngine: if/else rápido
    - StatisticalEngine: ML/estatística
    - LLMEngine: Chamada externa para LLM
    - HybridEngine: Combina múltiplos
    """
    
    def __init__(self, name: str, tier: int = 2):
        """
        Args:
            name: Nome do motor (ex: "rule_engine")
            tier: Performance tier (1=rápido, 2=médio, 3=lento)
        """
        self.name = name
        self.tier = tier
    
    @abstractmethod
    async def decide(
        self, 
        context: DecisionContext,
        user_patterns: Optional[List] = None
    ) -> DecisionResult:
        """
        Toma uma decisão baseado no contexto.
        
        Args:
            context: Contexto unificado
            user_patterns: Padrões aprendidos do usuário (opcional)
        
        Returns:
            DecisionResult com decisão + explicação
        """
        pass
    
    @abstractmethod
    def can_handle(self, decision_type: str) -> bool:
        """
        Verifica se este motor pode lidar com este tipo de decisão.
        
        Returns:
            True se pode processar, False caso contrário
        """
        pass
