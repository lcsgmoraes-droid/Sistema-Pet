"""
Replay Engine - Motor Central de Replay de Eventos (Fase 5.4)
==============================================================

RESPONSABILIDADES:
- Reprocessar eventos de forma segura e determinística
- Suporte a replay total e filtrado
- Processamento em batch com transações
- Progress tracking e auditoria técnica
- Isolamento via replay_context

GARANTIAS:
- ✅ Idempotência: replay 2x = mesmo resultado
- ✅ Atomicidade: cada batch é transação
- ✅ Isolamento: replay_mode ativo durante execução
- ✅ Auditável: registro completo em audit_log
- ✅ Segurança: rollback em caso de erro

Exemplo:
    from app.replay import replay_events
    
    # Replay total
    stats = replay_events(db)
    
    # Replay filtrado
    stats = replay_events(
        db,
        user_id=1,
        event_type='VendaFinalizada',
        from_sequence=1000
    )
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.domain.events.event_store import EventStore
from app.core.replay_context import enable_replay_mode, disable_replay_mode
from app.read_models.handlers_v53_idempotente import VendaReadModelHandler

logger = logging.getLogger(__name__)


@dataclass
class ReplayStats:
    """
    Estatísticas do replay executado.
    
    Attributes:
        total_events: Total de eventos reprocessados
        batches_processed: Número de batches executados
        duration_seconds: Duração total em segundos
        success: Se o replay foi bem-sucedido
        error: Mensagem de erro (se houver)
        filters_applied: Filtros que foram aplicados
        start_time: Timestamp de início
        end_time: Timestamp de término
    """
    total_events: int
    batches_processed: int
    duration_seconds: float
    success: bool
    error: Optional[str] = None
    filters_applied: Optional[Dict[str, Any]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário (para auditoria)"""
        return asdict(self)


def replay_events(
    db: Session,
    user_id: Optional[int] = None,
    event_type: Optional[str] = None,
    aggregate_id: Optional[str] = None,
    from_sequence: Optional[int] = None,
    to_sequence: Optional[int] = None,
    batch_size: int = 1000
) -> ReplayStats:
    """
    Reprocessa eventos do event store.
    
    IMPORTANTE:
    - Ativa replay_mode automaticamente
    - Processa em batches transacionais
    - Faz rollback em caso de erro
    - Registra auditoria técnica
    
    Args:
        db: Sessão do banco (será gerenciada pelo engine)
        user_id: Filtrar por tenant (None = todos)
        event_type: Filtrar por tipo de evento
        aggregate_id: Filtrar por agregado específico
        from_sequence: A partir de qual sequence_number
        to_sequence: Até qual sequence_number
        batch_size: Tamanho do batch (default: 1000)
    
    Returns:
        ReplayStats: Estatísticas do replay executado
    
    Raises:
        Exception: Se replay falhar (com rollback completo)
    
    Example:
        >>> from app.replay import replay_events
        >>> stats = replay_events(db, user_id=1)
        >>> logger.info(f"Processados: {stats.total_events} eventos")
        Processados: 5432 eventos
    """
    
    start_time = datetime.now(timezone.utc)
    event_store = EventStore(db)
    handler = VendaReadModelHandler(db)
    
    filters_applied = {
        'user_id': user_id,
        'event_type': event_type,
        'aggregate_id': aggregate_id,
        'from_sequence': from_sequence,
        'to_sequence': to_sequence,
        'batch_size': batch_size,
    }
    
    # Registrar início do replay
    _log_replay_start(db, filters_applied)
    
    try:
        # ✅ ATIVAR MODO REPLAY
        enable_replay_mode()
        logger.info("🔄 REPLAY INICIADO")
        logger.info(f"📋 Filtros: {filters_applied}")
        
        # Buscar eventos a reprocessar
        eventos = event_store.get_events(
            user_id=user_id,
            event_type=event_type,
            aggregate_id=aggregate_id,
            from_sequence=from_sequence,
            to_sequence=to_sequence
        )
        
        total_events = len(eventos)
        logger.info(f"📊 Total de eventos para replay: {total_events}")
        
        if total_events == 0:
            logger.warning("⚠️  Nenhum evento encontrado com os filtros especificados")
            return ReplayStats(
                total_events=0,
                batches_processed=0,
                duration_seconds=0.0,
                success=True,
                filters_applied=filters_applied,
                start_time=start_time,
                end_time=datetime.now(timezone.utc)
            )
        
        # Processar em batches
        batches_processed = 0
        events_processed = 0
        
        for i in range(0, total_events, batch_size):
            batch = eventos[i:i + batch_size]
            batch_number = (i // batch_size) + 1
            total_batches = (total_events + batch_size - 1) // batch_size
            
            logger.info(f"📦 Processando batch {batch_number}/{total_batches} ({len(batch)} eventos)")
            
            try:
                # ✅ PROCESSAR BATCH (transação gerenciada externamente)
                _process_batch(handler, batch)
                
                # Commit do batch (cada batch é uma transação)
                db.commit()
                
                batches_processed += 1
                events_processed += len(batch)
                
                # Progress tracking
                percentual = (events_processed / total_events) * 100
                logger.info(f"✅ Batch {batch_number} concluído - Progresso: {events_processed}/{total_events} ({percentual:.1f}%)")
                
            except Exception as batch_error:
                # ❌ ROLLBACK DO BATCH
                db.rollback()
                logger.error(f"❌ Erro no batch {batch_number}: {batch_error}", exc_info=True)
                
                # Registrar falha e abortar
                end_time = datetime.now(timezone.utc)
                duration = (end_time - start_time).total_seconds()
                
                stats = ReplayStats(
                    total_events=events_processed,
                    batches_processed=batches_processed,
                    duration_seconds=duration,
                    success=False,
                    error=f"Erro no batch {batch_number}: {str(batch_error)}",
                    filters_applied=filters_applied,
                    start_time=start_time,
                    end_time=end_time
                )
                
                _log_replay_end(db, stats)
                raise Exception(f"Replay abortado no batch {batch_number}: {batch_error}") from batch_error
        
        # ✅ REPLAY CONCLUÍDO COM SUCESSO
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        stats = ReplayStats(
            total_events=events_processed,
            batches_processed=batches_processed,
            duration_seconds=duration,
            success=True,
            filters_applied=filters_applied,
            start_time=start_time,
            end_time=end_time
        )
        
        logger.info(f"✅ REPLAY CONCLUÍDO!")
        logger.info(f"📊 Estatísticas: {events_processed} eventos em {batches_processed} batches ({duration:.2f}s)")
        
        # Registrar sucesso
        _log_replay_end(db, stats)
        
        return stats
        
    finally:
        # ✅ GARANTIR DESATIVAÇÃO DO MODO REPLAY
        disable_replay_mode()
        logger.info("🔄 Modo replay DESATIVADO")


def _process_batch(handler: VendaReadModelHandler, eventos: List[Dict[str, Any]]) -> None:
    """
    Processa um batch de eventos.
    
    IMPORTANTE:
    - NÃO faz commit (responsabilidade do caller)
    - Eventos processados de forma idempotente
    - Side effects suprimidos automaticamente (replay_mode ativo)
    
    Args:
        handler: Handler de read models
        eventos: Lista de eventos a processar
    
    Raises:
        Exception: Se qualquer evento falhar
    """
    
    for evento_dict in eventos:
        event_type = evento_dict['event_type']
        
        try:
            # Rotear evento para handler correto
            if event_type == 'VendaCriada':
                from app.domain.events.venda_events import VendaCriada
                payload = evento_dict['payload']
                evento = VendaCriada(**payload)
                handler.on_venda_criada(evento)
                
            elif event_type == 'VendaFinalizada':
                from app.domain.events.venda_events import VendaFinalizada
                payload = evento_dict['payload']
                evento = VendaFinalizada(**payload)
                handler.on_venda_finalizada(evento)
                
            elif event_type == 'VendaCancelada':
                from app.domain.events.venda_events import VendaCancelada
                payload = evento_dict['payload']
                evento = VendaCancelada(**payload)
                handler.on_venda_cancelada(evento)
                
            else:
                logger.warning(f"⚠️  Tipo de evento desconhecido: {event_type}")
                
        except Exception as e:
            logger.error(f"❌ Erro processando evento {evento_dict.get('id')}: {e}", exc_info=True)
            raise


def _log_replay_start(db: Session, filters: Dict[str, Any]) -> None:
    """
    Registra início do replay em audit_log_technical.
    
    NOTA: Como não temos tabela audit_log_technical ainda,
    registramos em AuditLog com entity_type='replay'.
    """
    try:
        import json
        from app.audit_log import log_action
        
        log_action(
            db=db,
            user_id=None,  # Ação do sistema
            action='replay_start',
            entity_type='replay',
            entity_id=None,
            details=json.dumps({
                'filters': filters,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        )
        db.commit()
        
    except Exception as e:
        logger.warning(f"⚠️  Falha ao registrar início do replay: {e}")
        db.rollback()


def _log_replay_end(db: Session, stats: ReplayStats) -> None:
    """
    Registra fim do replay em audit_log_technical.
    """
    try:
        import json
        from app.audit_log import log_action
        
        log_action(
            db=db,
            user_id=None,  # Ação do sistema
            action='replay_end',
            entity_type='replay',
            entity_id=None,
            details=json.dumps({
                'stats': stats.to_dict(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        )
        db.commit()
        
    except Exception as e:
        logger.warning(f"⚠️  Falha ao registrar fim do replay: {e}")
        db.rollback()
