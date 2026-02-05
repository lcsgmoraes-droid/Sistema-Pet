"""
DecisionResult - Output unificado de decisões de IA
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from .types import ConfidenceLevel


class Evidence(BaseModel):
    """Evidência que embasou a decisão"""
    source: str = Field(..., description="Fonte (ex: 'historico_usuario', 'regra_padrao')")
    value: Any = Field(..., description="Valor que contribuiu")
    weight: float = Field(..., description="Peso na decisão final (0.0-1.0)")
    explanation: str = Field(..., description="Como este dado foi usado")


class Alternative(BaseModel):
    """Alternativa considerada mas não escolhida"""
    option: str = Field(..., description="Opção alternativa")
    confidence: float = Field(..., description="Score desta alternativa (0-100)")
    reason_rejected: str = Field(..., description="Por que foi rejeitada")


class DecisionResult(BaseModel):
    """
    Resultado de uma decisão de IA - FRAMEWORK GLOBAL DE CONFIANÇA.
    
    A IA NUNCA executa ações diretamente. Ela apenas retorna:
    - decisão sugerida
    - confiança (0-100)
    - explicação clara
    - evidências auditáveis
    
    O SISTEMA decide o que fazer com base na confiança.
    
    Exemplo:
        result = DecisionResult(
            decision={"categoria_id": 15, "categoria_nome": "Energia Elétrica"},
            confidence_score=92,
            confidence_level=ConfidenceLevel.VERY_HIGH,
            explanation="Palavra-chave 'ENERGISA' com 95% de acerto em 23 casos",
            reasons=[
                "Palavra-chave 'ENERGISA' detectada no histórico",
                "Padrão similar aplicado 23 vezes nos últimos 30 dias"
            ],
            evidence=[...],
            alternatives=[...]
        )
    """
    # Identificação
    request_id: str = Field(..., description="ID do contexto original")
    decision_type: str = Field(..., description="Tipo de decisão tomada")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Decisão principal
    decision: Dict[str, Any] = Field(
        ..., 
        description="A decisão sugerida (estrutura varia por tipo)"
    )
    
    # Confiança - FRAMEWORK GLOBAL
    confidence_score: int = Field(
        ..., 
        ge=0, 
        le=100,
        description="Score de confiança (0-100) - ÚNICO no sistema"
    )
    confidence_level: ConfidenceLevel = Field(
        ...,
        description="Nível categórico (VERY_LOW, LOW, MEDIUM, HIGH, VERY_HIGH)"
    )
    
    # Explicabilidade obrigatória
    explanation: str = Field(
        ...,
        min_length=10,
        description="Explicação clara em uma frase do por que desta decisão"
    )
    reasons: List[str] = Field(
        ..., 
        min_items=1,
        description="Razões detalhadas em linguagem natural (mínimo 1)"
    )
    evidence: List[Evidence] = Field(
        default_factory=list,
        description="Evidências auditáveis que embasaram a decisão"
    )
    alternatives: List[Alternative] = Field(
        default_factory=list,
        description="Outras opções consideradas mas não escolhidas"
    )
    
    # Compatibilidade retroativa (deprecated)
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="DEPRECATED: Use confidence_score (mantido por compatibilidade)"
    )
    
    # Motor que gerou
    engine_used: str = Field(..., description="Motor usado (rule_engine, llm_engine, etc)")
    processing_time_ms: float = Field(..., description="Tempo de processamento")
    
    # Ações sugeridas
    suggested_actions: Optional[List[str]] = Field(
        None,
        description="Ações que o sistema pode tomar (se confiança permitir)"
    )
    requires_human_review: bool = Field(
        default=False,
        description="Se True, deve passar por validação humana"
    )
    
    # Debugging
    debug_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Informações técnicas (apenas em dev/debug)"
    )
    
    class Config:
        use_enum_values = True
