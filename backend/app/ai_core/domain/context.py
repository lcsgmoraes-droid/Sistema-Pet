"""
DecisionContext - Input unificado para decisões de IA
"""
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from .types import DecisionType


class DecisionContext(BaseModel):
    """
    Contexto unificado para qualquer decisão de IA.
    
    Exemplo de uso:
        context = DecisionContext(
            user_id=123,
            decision_type=DecisionType.CATEGORIZAR_LANCAMENTO,
            primary_data={"descricao": "PIX ENERGISA", "valor": -150.00},
            additional_data={"historico_ultimos_30d": [...]}
        )
    """
    # Identificação
    user_id: int = Field(..., description="Tenant ID (obrigatório)")
    decision_type: DecisionType = Field(..., description="Tipo de decisão esperada")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Dados primários (o que precisa ser decidido)
    primary_data: Dict[str, Any] = Field(
        ..., 
        description="Dados principais (ex: descrição do lançamento, produto sendo vendido)"
    )
    
    # Dados auxiliares (contexto extra)
    additional_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Dados de contexto (histórico, estatísticas, configurações)"
    )
    
    # Constraints (restrições)
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Restrições (ex: max_confidence_threshold, allowed_categories)"
    )
    
    # Metadados
    source: Optional[str] = Field(None, description="Origem da requisição (api, scheduler, webhook)")
    user_agent: Optional[str] = None
    
    class Config:
        use_enum_values = True
