"""
Event Store - Persistência de Eventos de Domínio
=================================================

Implementa o padrão Event Store para event sourcing.

RESPONSABILIDADES:
- Persistir eventos de domínio de forma imutável
- Gerar sequence_number automaticamente
- Garantir ordenação monotônica
- Permitir queries de replay eficientes

FASE 5.2 - Event Store Enhanced:
- Sequence number global e monotônico
- Rastreabilidade via correlation_id e causation_id
- Índices otimizados para replay
"""

import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from .base import DomainEvent

logger = logging.getLogger(__name__)


class EventStore:
    """
    Armazena eventos de domínio de forma append-only.
    
    GARANTIAS:
    - Imutabilidade: Apenas INSERT, nunca UPDATE/DELETE
    - Ordenação: sequence_number monotônico
    - Atomicidade: Eventos são salvos em transação
    - Isolamento: Multi-tenant via user_id
    
    Exemplo:
        store = EventStore(db)
        evento = VendaCriada(...)
        store.append(evento, user_id=1, aggregate_type='venda')
    """
    
    def __init__(self, db: Session):
        """
        Inicializa event store com sessão do banco.
        
        Args:
            db: Sessão SQLAlchemy
        """
        self.db = db
    
    def append(
        self,
        event: DomainEvent,
        user_id: int,
        aggregate_type: str,
        aggregate_id: Optional[str] = None
    ) -> DomainEvent:
        """
        Adiciona evento ao event store.
        
        IMPORTANTE: sequence_number é gerado automaticamente pelo banco.
        
        Args:
            event: Evento de domínio a persistir
            user_id: ID do tenant (multi-tenancy)
            aggregate_type: Tipo do agregado ('venda', 'pagamento', etc)
            aggregate_id: ID do agregado (usa event_id se não fornecido)
        
        Returns:
            Evento com sequence_number preenchido
            
        Raises:
            Exception: Se falhar ao persistir
        """
        try:
            # Preparar dados
            aggregate_id = aggregate_id or event.event_id
            payload = json.dumps(event.to_dict(), default=str)
            metadata = json.dumps({
                'source': 'application',
                'version': '1.0',
            })
            
            # Gerar próximo sequence_number
            result = self.db.execute(text("""
                SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM domain_events
            """))
            next_sequence = result.fetchone()[0]
            
            # Inserir evento com sequence_number calculado
            query = text("""
                INSERT INTO domain_events (
                    id, sequence_number, event_type, aggregate_id, aggregate_type,
                    user_id, correlation_id, causation_id,
                    payload, metadata, created_at
                ) VALUES (
                    :id, :sequence_number, :event_type, :aggregate_id, :aggregate_type,
                    :user_id, :correlation_id, :causation_id,
                    :payload, :metadata, :created_at
                )
            """)
            
            self.db.execute(query, {
                'id': event.event_id,
                'sequence_number': next_sequence,
                'event_type': event.event_type,
                'aggregate_id': aggregate_id,
                'aggregate_type': aggregate_type,
                'user_id': user_id,
                'correlation_id': event.correlation_id,
                'causation_id': event.causation_id,
                'payload': payload,
                'metadata': metadata,
                'created_at': event.timestamp.isoformat(),
            })
            
            logger.debug(
                f"📝 Evento persistido: {event.event_type} "
                f"(seq={next_sequence}, id={event.event_id})"
            )
            
            # Retornar evento com sequence_number preenchido
            # Remove event_type do dict pois é uma @property, não um field
            event_dict = event.to_dict()
            event_dict.pop('event_type', None)  # Remover event_type (é @property)
            event_dict['sequence_number'] = next_sequence
            return event.__class__(**event_dict)
            
        except Exception as e:
            logger.error(f"❌ Erro ao persistir evento: {str(e)}", exc_info=True)
            raise
    
    def append_batch(
        self,
        events: List[DomainEvent],
        user_id: int,
        aggregate_type: str
    ) -> List[DomainEvent]:
        """
        Adiciona múltiplos eventos de forma atômica.
        
        Args:
            events: Lista de eventos
            user_id: ID do tenant
            aggregate_type: Tipo do agregado
        
        Returns:
            Lista de eventos com sequence_number preenchido
        """
        persisted_events = []
        
        for event in events:
            persisted_event = self.append(event, user_id, aggregate_type)
            persisted_events.append(persisted_event)
        
        return persisted_events
    
    def get_events(
        self,
        user_id: Optional[int] = None,
        event_type: Optional[str] = None,
        aggregate_id: Optional[str] = None,
        from_sequence: Optional[int] = None,
        to_sequence: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca eventos com filtros (para replay).
        
        Args:
            user_id: Filtrar por tenant
            event_type: Filtrar por tipo de evento
            aggregate_id: Filtrar por agregado específico
            from_sequence: A partir de qual sequence_number
            to_sequence: Até qual sequence_number
            limit: Limite de resultados
        
        Returns:
            Lista de eventos (como dicionários)
            
        Exemplo:
            # Replay de todos eventos de um tenant
            events = store.get_events(user_id=1)
            
            # Replay incremental (apenas novos eventos)
            events = store.get_events(from_sequence=1000)
            
            # Replay de vendas de um período
            events = store.get_events(
                event_type='VendaCriada',
                from_sequence=500,
                to_sequence=1000
            )
        """
        try:
            # Construir query dinamicamente
            query = "SELECT * FROM domain_events WHERE 1=1"
            params = {}
            
            if user_id is not None:
                query += " AND user_id = :user_id"
                params['user_id'] = user_id
            
            if event_type is not None:
                query += " AND event_type = :event_type"
                params['event_type'] = event_type
            
            if aggregate_id is not None:
                query += " AND aggregate_id = :aggregate_id"
                params['aggregate_id'] = aggregate_id
            
            if from_sequence is not None:
                query += " AND sequence_number >= :from_sequence"
                params['from_sequence'] = from_sequence
            
            if to_sequence is not None:
                query += " AND sequence_number <= :to_sequence"
                params['to_sequence'] = to_sequence
            
            # SEMPRE ordenar por sequence_number
            query += " ORDER BY sequence_number ASC"
            
            if limit is not None:
                query += " LIMIT :limit"
                params['limit'] = limit
            
            result = self.db.execute(text(query), params)
            
            # Converter rows para dicionários
            events = []
            for row in result:
                event_dict = {
                    'id': row[0],
                    'sequence_number': row[1],
                    'event_type': row[2],
                    'aggregate_id': row[3],
                    'aggregate_type': row[4],
                    'user_id': row[5],
                    'correlation_id': row[6],
                    'causation_id': row[7],
                    'payload': json.loads(row[8]),
                    'metadata': json.loads(row[9]) if row[9] else {},
                    'created_at': row[10],
                }
                events.append(event_dict)
            
            logger.debug(f"🔍 Encontrados {len(events)} eventos com filtros fornecidos")
            return events
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar eventos: {str(e)}", exc_info=True)
            raise
    
    def get_last_sequence_number(self) -> int:
        """
        Retorna o último sequence_number no event store.
        
        Útil para:
        - Checkpoints de replay
        - Validar se há novos eventos
        - Monitoramento
        """
        try:
            result = self.db.execute(text("""
                SELECT MAX(sequence_number) FROM domain_events
            """))
            row = result.fetchone()
            return row[0] if row and row[0] else 0
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar último sequence_number: {str(e)}")
            return 0
    
    def count_events(self, user_id: Optional[int] = None) -> int:
        """
        Conta total de eventos (opcionalmente por tenant).
        """
        try:
            if user_id:
                result = self.db.execute(text("""
                    SELECT COUNT(*) FROM domain_events WHERE user_id = :user_id
                """), {'user_id': user_id})
            else:
                result = self.db.execute(text("""
                    SELECT COUNT(*) FROM domain_events
                """))
            
            row = result.fetchone()
            return row[0] if row else 0
            
        except Exception as e:
            logger.error(f"❌ Erro ao contar eventos: {str(e)}")
            return 0
    
    def validate_sequence_integrity(self) -> Dict[str, Any]:
        """
        Valida integridade da sequência de eventos.
        
        Verifica:
        - Sem gaps na sequência
        - Sem duplicatas
        - Ordem correta
        
        Returns:
            Dicionário com resultado da validação
        """
        try:
            # Buscar estatísticas da sequência
            result = self.db.execute(text("""
                SELECT 
                    MIN(sequence_number) as min_seq,
                    MAX(sequence_number) as max_seq,
                    COUNT(*) as total_events,
                    COUNT(DISTINCT sequence_number) as distinct_seqs
                FROM domain_events
            """))
            
            row = result.fetchone()
            
            if not row or row[2] == 0:
                return {
                    'valid': True,
                    'message': 'Nenhum evento no store',
                    'total_events': 0
                }
            
            min_seq, max_seq, total_events, distinct_seqs = row
            
            # Validar
            expected_count = max_seq - min_seq + 1
            has_gaps = total_events != expected_count
            has_duplicates = total_events != distinct_seqs
            
            if has_gaps or has_duplicates:
                return {
                    'valid': False,
                    'has_gaps': has_gaps,
                    'has_duplicates': has_duplicates,
                    'min_sequence': min_seq,
                    'max_sequence': max_seq,
                    'total_events': total_events,
                    'distinct_sequences': distinct_seqs,
                    'expected_count': expected_count,
                }
            
            return {
                'valid': True,
                'min_sequence': min_seq,
                'max_sequence': max_seq,
                'total_events': total_events,
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao validar integridade: {str(e)}")
            return {
                'valid': False,
                'error': str(e)
            }
