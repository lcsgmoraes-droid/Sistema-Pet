"""
Schemas Pydantic para eventos de oportunidade do PDV.

Define a estrutura de dados validada para registro de eventos de oportunidade,
garantindo integridade dos dados e rastreabilidade completa.

CONTRATO OFICIAL: Este schema é a fonte da verdade para eventos de oportunidade.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.domain.opportunity_events import OpportunityEventType, OpportunityType


class OpportunityEventPayload(BaseModel):
    """
    Payload completo de um evento de oportunidade no PDV.
    
    REGRAS DE VALIDAÇÃO:
    - tenant_id é OBRIGATÓRIO (multi-tenant)
    - oportunidade_id identifica unicamente a sugestão
    - contexto sempre "PDV" nesta versão
    - event_type determina qual ação o usuário tomou
    - user_id identifica quem estava operando o caixa
    - timestamp em UTC para auditoria
    
    IMPORTANTE:
    - Este payload só deve ser criado após ação explícita do usuário
    - Nunca criar payload para silêncio ou timeout
    - Falha na validação não deve quebrar o PDV
    """
    
    # Identificação
    tenant_id: UUID = Field(
        ...,
        description="UUID do tenant proprietário do evento (obrigatório)"
    )
    
    oportunidade_id: UUID = Field(
        ...,
        description="UUID único da oportunidade sugerida"
    )
    
    # Contexto da venda
    cliente_id: Optional[int] = Field(
        None,
        description="ID do cliente se houver (pode ser venda sem cadastro)"
    )
    
    contexto: str = Field(
        default="PDV",
        description="Contexto onde o evento ocorreu (sempre PDV nesta fase)"
    )
    
    # Tipo de oportunidade
    tipo: OpportunityType = Field(
        ...,
        description="Tipo de estratégia de venda (cross_sell, up_sell, recorrencia)"
    )
    
    # Produtos envolvidos
    produto_origem_id: Optional[int] = Field(
        None,
        description="ID do produto que gerou a oportunidade (pode ser nulo para recorrência)"
    )
    
    produto_sugerido_id: int = Field(
        ...,
        description="ID do produto sugerido pela IA/regra de negócio"
    )
    
    # Evento e ação do usuário
    event_type: OpportunityEventType = Field(
        ...,
        description="Tipo de evento (convertida, refinada, rejeitada)"
    )
    
    # Rastreabilidade
    user_id: int = Field(
        ...,
        description="ID do usuário (operador do caixa) que tomou a ação"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp UTC do evento"
    )
    
    # Metadados opcionais
    metadata: Optional[dict] = Field(
        None,
        description="Dados adicionais contextuais (versão da regra, score IA, etc)"
    )
    
    @field_validator('contexto')
    @classmethod
    def validate_contexto(cls, v: str) -> str:
        """
        Valida que contexto é sempre PDV nesta fase.
        Preparado para expansão futura (MOBILE, WEB, etc).
        """
        if v != "PDV":
            raise ValueError("Contexto deve ser 'PDV' nesta versão")
        return v
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp_utc(cls, v: datetime) -> datetime:
        """
        Garante que timestamp está em UTC.
        Remove timezone-aware se necessário para compatibilidade.
        """
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v
    
    class Config:
        """Configuração do schema Pydantic."""
        json_schema_extra = {
            "example": {
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "oportunidade_id": "660e8400-e29b-41d4-a716-446655440001",
                "cliente_id": 123,
                "contexto": "PDV",
                "tipo": "cross_sell",
                "produto_origem_id": 456,
                "produto_sugerido_id": 789,
                "event_type": "oportunidade_convertida",
                "user_id": 1,
                "timestamp": "2026-01-27T15:30:00",
                "metadata": {
                    "version": "1.0",
                    "confidence_score": 0.85
                }
            }
        }


class OpportunityEventResponse(BaseModel):
    """
    Resposta do serviço de registro de evento.
    
    Usado para confirmar sucesso/falha sem quebrar fluxo do PDV.
    """
    success: bool = Field(
        ...,
        description="True se evento foi registrado com sucesso"
    )
    
    event_id: Optional[str] = Field(
        None,
        description="ID do evento registrado (se sucesso)"
    )
    
    message: Optional[str] = Field(
        None,
        description="Mensagem de status ou erro (não crítico)"
    )
    
    class Config:
        """Configuração do schema Pydantic."""
        json_schema_extra = {
            "example": {
                "success": True,
                "event_id": "evt_770e8400e29b41d4a716446655440002",
                "message": "Evento registrado com sucesso"
            }
        }
