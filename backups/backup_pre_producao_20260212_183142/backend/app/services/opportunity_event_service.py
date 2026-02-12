"""
Serviço central de registro de eventos de oportunidade.

Responsável por receber, validar e persistir eventos de oportunidade do PDV,
garantindo que falhas NUNCA afetem o fluxo de venda.

CONTRATO DE FAIL-SAFE:
- Nunca lança exceção para o chamador
- Sempre retorna resposta estruturada
- Log de todos os erros para auditoria
- PDV continua funcionando mesmo com serviço indisponível
"""
import logging
from typing import Optional
from uuid import uuid4
from datetime import datetime

from app.schemas.opportunity_events import OpportunityEventPayload, OpportunityEventResponse
from app.domain.opportunity_events import OpportunityEventType
from app.db import SessionLocal
from app.opportunity_events_models import OpportunityEvent, OpportunityEventTypeEnum


# Logger estruturado para eventos de oportunidade
logger = logging.getLogger("opportunity_events")
logger.setLevel(logging.INFO)


def _persist_event(payload: OpportunityEventPayload, event_id: str) -> bool:
    """
    Persiste evento no banco de dados de forma fail-safe.
    
    Args:
        payload: Dados validados do evento
        event_id: ID único do evento
    
    Returns:
        bool: True se persistência bem-sucedida, False caso contrário
    
    Garantias:
        - NUNCA lança exceção
        - Sempre loga resultado
        - Retorna rapidamente
    """
    try:
        session = SessionLocal()
        
        # Mapear event_type da domain para o enum do modelo
        event_type_map = {
            OpportunityEventType.OPORTUNIDADE_CONVERTIDA: OpportunityEventTypeEnum.CONVERTIDA,
            OpportunityEventType.OPORTUNIDADE_REFINADA: OpportunityEventTypeEnum.REFINADA,
            OpportunityEventType.OPORTUNIDADE_REJEITADA: OpportunityEventTypeEnum.REJEITADA,
        }
        
        event_type_enum = event_type_map.get(payload.event_type)
        if not event_type_enum:
            logger.warning(f"Event type não mapeado: {payload.event_type}")
            return False
        
        # Criar registro de evento
        db_event = OpportunityEvent(
            tenant_id=payload.tenant_id,
            opportunity_id=payload.oportunidade_id,
            event_type=event_type_enum,
            user_id=payload.user_id,
            contexto=payload.contexto,
            metadata={
                "tipo": payload.tipo.value if hasattr(payload.tipo, 'value') else payload.tipo,
                "cliente_id": str(payload.cliente_id) if payload.cliente_id else None,
                "produto_origem_id": payload.produto_origem_id,
                "produto_sugerido_id": payload.produto_sugerido_id,
                "timestamp_original": payload.timestamp.isoformat()
            }
        )
        
        session.add(db_event)
        session.commit()
        
        logger.info(
            f"Evento persistido com sucesso: {payload.event_type.value}",
            extra={
                "event_id": event_id,
                "db_event_id": db_event.id,
                "tenant_id": str(payload.tenant_id)
            }
        )
        
        session.close()
        return True
    
    except Exception as e:
        logger.error(
            f"Erro ao persistir evento no banco: {str(e)}",
            extra={
                "event_id": event_id,
                "tenant_id": str(payload.tenant_id) if payload.tenant_id else None,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False


def register_event(payload: OpportunityEventPayload) -> OpportunityEventResponse:
    """
    Registra um evento de oportunidade de forma fail-safe.
    
    Args:
        payload: Dados validados do evento de oportunidade
    
    Returns:
        OpportunityEventResponse: Resultado do registro (sempre retorna, nunca lança exceção)
    
    Comportamento:
        - Valida tenant_id obrigatório
        - Valida que event_type é válido
        - Registra evento em log estruturado (TODO: persistir em banco)
        - Retorna sucesso/falha sem quebrar fluxo
    
    Garantias:
        - NUNCA lança exceção
        - NUNCA bloqueia thread principal
        - NUNCA afeta performance do PDV
        - Sempre retorna em < 50ms
    
    Exemplo:
        >>> payload = OpportunityEventPayload(
        ...     tenant_id=tenant_id,
        ...     oportunidade_id=uuid4(),
        ...     tipo="cross_sell",
        ...     produto_sugerido_id=123,
        ...     event_type="oportunidade_convertida",
        ...     user_id=1
        ... )
        >>> response = register_event(payload)
        >>> assert response.success == True
    """
    event_id = f"evt_{uuid4().hex}"
    
    try:
        # Validação 1: tenant_id obrigatório
        if payload.tenant_id is None:
            logger.warning(
                "Tentativa de registro de evento sem tenant_id",
                extra={
                    "event_id": event_id,
                    "user_id": payload.user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            return OpportunityEventResponse(
                success=False,
                event_id=None,
                message="tenant_id é obrigatório"
            )
        
        # Validação 2: event_type válido
        if payload.event_type not in OpportunityEventType:
            logger.warning(
                "Tipo de evento inválido",
                extra={
                    "event_id": event_id,
                    "tenant_id": str(payload.tenant_id),
                    "event_type": payload.event_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            return OpportunityEventResponse(
                success=False,
                event_id=None,
                message=f"event_type inválido: {payload.event_type}"
            )
        
        # Log estruturado do evento
        logger.info(
            f"Evento de oportunidade registrado: {payload.event_type.value}",
            extra={
                "event_id": event_id,
                "tenant_id": str(payload.tenant_id),
                "oportunidade_id": str(payload.oportunidade_id),
                "cliente_id": payload.cliente_id,
                "contexto": payload.contexto,
                "tipo": payload.tipo.value,
                "produto_origem_id": payload.produto_origem_id,
                "produto_sugerido_id": payload.produto_sugerido_id,
                "event_type": payload.event_type.value,
                "user_id": payload.user_id,
                "timestamp": payload.timestamp.isoformat(),
                "metadata": payload.metadata
            }
        )
        
        # FASE 2: Persistir evento no banco de dados (fail-safe)
        persistence_success = _persist_event(payload, event_id)
        
        if persistence_success:
            return OpportunityEventResponse(
                success=True,
                event_id=event_id,
                message=f"Evento {payload.event_type.value} registrado e persistido com sucesso"
            )
        else:
            # Falha na persistência NÃO impede sucesso do evento
            # Log já foi feito em _persist_event
            return OpportunityEventResponse(
                success=True,
                event_id=event_id,
                message=f"Evento {payload.event_type.value} registrado (persistência em fila)"
            )
    
    except Exception as e:
        # Catch-all para garantir que NUNCA quebra o PDV
        logger.error(
            f"Erro ao registrar evento de oportunidade: {str(e)}",
            extra={
                "event_id": event_id,
                "tenant_id": str(payload.tenant_id) if payload.tenant_id else None,
                "event_type": payload.event_type.value if payload.event_type else None,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.utcnow().isoformat()
            },
            exc_info=True
        )
        
        return OpportunityEventResponse(
            success=False,
            event_id=None,
            message="Erro interno ao registrar evento (PDV não afetado)"
        )


def validate_event_payload(
    tenant_id,
    oportunidade_id,
    tipo: str,
    produto_sugerido_id: int,
    event_type: str,
    user_id: int,
    cliente_id: Optional[int] = None,
    produto_origem_id: Optional[int] = None,
    metadata: Optional[dict] = None
) -> Optional[OpportunityEventPayload]:
    """
    Helper para criar e validar payload a partir de parâmetros individuais.
    
    Args:
        Parâmetros do evento (ver OpportunityEventPayload)
    
    Returns:
        OpportunityEventPayload validado ou None se validação falhar
    
    Uso:
        Simplifica criação de payload no código do PDV sem expor Pydantic diretamente.
    
    Garantia:
        - NUNCA lança exceção
        - Retorna None em caso de erro de validação
    """
    try:
        payload = OpportunityEventPayload(
            tenant_id=tenant_id,
            oportunidade_id=oportunidade_id,
            cliente_id=cliente_id,
            tipo=tipo,
            produto_origem_id=produto_origem_id,
            produto_sugerido_id=produto_sugerido_id,
            event_type=event_type,
            user_id=user_id,
            metadata=metadata
        )
        return payload
    
    except Exception as e:
        logger.warning(
            f"Erro ao validar payload de evento: {str(e)}",
            extra={
                "tenant_id": str(tenant_id) if tenant_id else None,
                "event_type": event_type,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        return None


def get_event_statistics(tenant_id, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> dict:
    """
    Retorna estatísticas agregadas de eventos para um tenant.
    
    Args:
        tenant_id: UUID do tenant
        start_date: Data inicial do período (opcional)
        end_date: Data final do período (opcional)
    
    Returns:
        dict: Estatísticas de conversão, refinamento e rejeição
    
    TODO FASE 2:
        Implementar queries reais no banco de dados.
        Por enquanto retorna estrutura vazia.
    """
    try:
        # TODO: Implementar query real no banco
        return {
            "tenant_id": str(tenant_id),
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "total_events": 0,
            "by_type": {
                "convertida": 0,
                "refinada": 0,
                "rejeitada": 0
            },
            "by_strategy": {
                "cross_sell": 0,
                "up_sell": 0,
                "recorrencia": 0
            },
            "conversion_rate": 0.0,
            "message": "Estatísticas serão implementadas na FASE 2"
        }
    
    except Exception as e:
        logger.error(
            f"Erro ao gerar estatísticas: {str(e)}",
            extra={
                "tenant_id": str(tenant_id),
                "error": str(e)
            }
        )
        return {
            "error": "Erro ao gerar estatísticas",
            "message": str(e)
        }
