"""
Feedback humano e padrões de aprendizado
"""
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .types import FeedbackType


class HumanFeedback(BaseModel):
    """
    Feedback humano sobre uma decisão de IA.
    
    Exemplo:
        feedback = HumanFeedback(
            decision_id="dec_abc123",
            user_id=123,
            feedback_type=FeedbackType.CORRIGIDO,
            ai_decision={"categoria_id": 15},
            human_decision={"categoria_id": 18},
            reason="Na verdade era telefone, não energia"
        )
    """
    # Identificação
    decision_id: str = Field(..., description="ID da decisão original")
    user_id: int = Field(..., description="Tenant que deu feedback")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Feedback
    feedback_type: FeedbackType
    
    # Comparação
    ai_decision: Dict[str, Any] = Field(..., description="O que a IA sugeriu")
    human_decision: Optional[Dict[str, Any]] = Field(
        None, 
        description="O que o humano escolheu (se diferente)"
    )
    
    # Explicação
    reason: Optional[str] = Field(
        None,
        description="Por que o humano concordou/discordou"
    )
    
    # Metadados
    applied_at: Optional[datetime] = Field(
        None,
        description="Quando foi aplicado no sistema"
    )


class LearningPattern(BaseModel):
    """
    Padrão aprendido com feedback acumulado.
    
    Exemplo:
        pattern = LearningPattern(
            user_id=123,
            pattern_type="categoria_por_descricao",
            input_signature={"keywords": ["energisa", "cemig"]},
            output_preference={"categoria_id": 15},
            confidence_boost=15.0,
            occurrences=23
        )
    """
    user_id: int = Field(..., description="Tenant dono do padrão")
    pattern_type: str = Field(..., description="Tipo de padrão (ex: categoria_por_descricao)")
    
    # Padrão
    input_signature: Dict[str, Any] = Field(
        ...,
        description="Assinatura de entrada que ativa este padrão"
    )
    output_preference: Dict[str, Any] = Field(
        ...,
        description="Output preferido pelo usuário"
    )
    
    # Estatísticas
    confidence_boost: float = Field(
        default=10.0,
        description="Quanto este padrão aumenta a confiança (%)"
    )
    occurrences: int = Field(
        default=1,
        description="Quantas vezes este padrão foi aplicado com sucesso"
    )
    success_rate: float = Field(
        default=100.0,
        description="Taxa de acerto (0-100)"
    )
    
    # Temporalidade
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = Field(
        None,
        description="Padrões podem expirar se não forem usados"
    )
