"""
Classe Base para Eventos de Domínio
====================================

Define a estrutura básica que todos os eventos devem seguir.

FASE 5.2 - Event Store Enhanced:
- sequence_number: Ordem global monotônica
- correlation_id: Rastrear fluxo completo
- causation_id: Evento que causou este evento
"""

from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import uuid


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """
    Classe base para todos os eventos de domínio.
    
    Eventos de domínio são fatos que aconteceram no passado
    e que outras partes do sistema podem querer reagir.
    
    Características:
    - Imutáveis (frozen=True)
    - Nomeados no passado (VendaCriada, não CriarVenda)
    - Contêm apenas dados, sem comportamento
    
    Event Sourcing (Fase 5.2):
    - sequence_number: Ordem global (preenchido ao persistir)
    - correlation_id: Rastrear fluxo completo (ex: toda uma venda)
    - causation_id: Evento que causou este evento
    """
    
    # Identificação
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Event Sourcing (Fase 5.2)
    sequence_number: Optional[int] = field(default=None)  # Preenchido ao persistir
    correlation_id: Optional[str] = field(default=None)   # Rastrear fluxo completo
    causation_id: Optional[str] = field(default=None)     # Evento que causou este
    
    @property
    def event_type(self) -> str:
        """Retorna o tipo do evento (nome da classe)"""
        return self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa o evento para dicionário"""
        data = asdict(self)
        # Adicionar event_type
        data['event_type'] = self.event_type
        # Converter datetime para string ISO
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data
    
    def with_causation(self, causation_event_id: str, correlation_id: Optional[str] = None) -> 'DomainEvent':
        """
        Cria novo evento com rastreabilidade (causation_id e correlation_id).
        
        Args:
            causation_event_id: ID do evento que causou este
            correlation_id: ID de correlação (usa o mesmo se não fornecido)
        
        Returns:
            Novo evento com rastreabilidade configurada
            
        Exemplo:
            evento_pagamento = PagamentoRecebido(...).with_causation(
                causation_event_id=evento_venda.event_id,
                correlation_id=evento_venda.correlation_id or evento_venda.event_id
            )
        """
        # Criar cópia com novos valores
        # Nota: Como dataclass é frozen, precisamos criar novo objeto
        data = asdict(self)
        data['causation_id'] = causation_event_id
        data['correlation_id'] = correlation_id or causation_event_id
        return self.__class__(**data)
    
    def __repr__(self) -> str:
        return f"{self.event_type}(event_id={self.event_id}, timestamp={self.timestamp}, seq={self.sequence_number})"


