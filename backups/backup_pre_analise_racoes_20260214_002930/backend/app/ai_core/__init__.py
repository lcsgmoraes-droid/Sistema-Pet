"""
AI CORE - Núcleo Centralizado de Inteligência Artificial
=========================================================

Sistema unificado para todas as decisões inteligentes do sistema:
- Categorização de extratos
- Sugestões em vendas
- Detecção de intenção (WhatsApp)
- Otimização de entregas
- Previsões e recomendações

Princípios:
- IA nunca executa, apenas sugere
- Toda decisão é explicável
- Multi-tenant por design
- Aprendizado contínuo com feedback humano
- Human-in-the-Loop para decisões MEDIUM/LOW
"""

__version__ = "1.1.0"

# Exports principais
from .services.decision_service import DecisionService
from .services.review_service import ReviewService
from .services.learning_service import LearningService
from .domain.decision import DecisionResult
from .domain.review import (
    ReviewQueueEntry,
    DecisionReviewStatus,
    HumanReviewFeedback
)
from .domain.events import DecisionReviewedEvent

__all__ = [
    "DecisionService",
    "ReviewService",
    "LearningService",
    "DecisionResult",
    "ReviewQueueEntry",
    "DecisionReviewStatus",
    "HumanReviewFeedback",
    "DecisionReviewedEvent",
]
