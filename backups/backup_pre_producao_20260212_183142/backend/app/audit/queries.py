"""
Queries de Auditoria - Fase 5.6
================================

Funções de consulta read-only ao log de auditoria.
"""

from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import Session
import json

from app.models import AuditLog
from app.audit.schemas import (
    ReplayAuditResponse,
    RebuildAuditResponse,
    PaginationMetadata,
    PaginatedReplayResponse,
    PaginatedRebuildResponse,
    AuditSummary
)


# =============================
# Constantes
# =============================

REPLAY_ACTIONS = ['replay_start', 'replay_end']
REBUILD_ACTIONS = [
    'rebuild_start',
    'rebuild_read_models_success',
    'rebuild_read_models_failure',
    'schema_swap_success',
    'schema_swap_failure'
]


# =============================
# Queries de Replay
# =============================

def get_replays(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None
) -> PaginatedReplayResponse:
    """
    Retorna replays com paginação e filtros.
    
    Args:
        db: Sessão do banco
        page: Número da página (1-indexed)
        page_size: Itens por página (max 100)
        start_date: Filtro de data inicial
        end_date: Filtro de data final
        status: Filtro por status ('success', 'failure', 'in_progress')
    
    Returns:
        PaginatedReplayResponse com replays e metadados
    """
    # Query base
    query = db.query(AuditLog).filter(
        AuditLog.action.in_(REPLAY_ACTIONS)
    )
    
    # Aplicar filtros
    filters = []
    if start_date:
        filters.append(AuditLog.timestamp >= start_date)
    if end_date:
        filters.append(AuditLog.timestamp <= end_date)
    if status:
        # Inferir status baseado no action
        if status == 'success':
            filters.append(AuditLog.action == 'replay_end')
        elif status == 'failure':
            filters.append(and_(
                AuditLog.action == 'replay_end',
                AuditLog.details.like('%error%')
            ))
        elif status == 'in_progress':
            # Replays sem "replay_end" correspondente
            pass  # Lógica mais complexa, implementar se necessário
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Total de itens
    total_items = query.count()
    
    # Calcular paginação
    total_pages = (total_items + page_size - 1) // page_size
    offset = (page - 1) * page_size
    
    # Buscar itens
    items = query.order_by(desc(AuditLog.timestamp))\
                 .limit(page_size)\
                 .offset(offset)\
                 .all()
    
    # Converter para response
    replay_items = []
    for item in items:
        details = json.loads(item.details) if item.details else {}
        
        # Determinar status
        item_status = 'in_progress'
        if item.action == 'replay_end':
            item_status = 'failure' if details.get('error') else 'success'
        
        replay_items.append(ReplayAuditResponse(
            id=item.id,
            action=item.action,
            timestamp=item.timestamp,
            status=item_status,
            filters=details.get('filters'),
            stats=details.get('stats'),
            error=details.get('error')
        ))
    
    # Metadados
    metadata = PaginationMetadata(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )
    
    return PaginatedReplayResponse(items=replay_items, metadata=metadata)


def get_replay_by_id(db: Session, replay_id: int) -> Optional[ReplayAuditResponse]:
    """
    Retorna um replay específico por ID.
    
    Args:
        db: Sessão do banco
        replay_id: ID do log de auditoria
    
    Returns:
        ReplayAuditResponse ou None se não encontrado
    """
    item = db.query(AuditLog)\
             .filter(AuditLog.id == replay_id)\
             .filter(AuditLog.action.in_(REPLAY_ACTIONS))\
             .first()
    
    if not item:
        return None
    
    details = json.loads(item.details) if item.details else {}
    
    # Determinar status
    status = 'in_progress'
    if item.action == 'replay_end':
        status = 'failure' if details.get('error') else 'success'
    
    return ReplayAuditResponse(
        id=item.id,
        action=item.action,
        timestamp=item.timestamp,
        status=status,
        filters=details.get('filters'),
        stats=details.get('stats'),
        error=details.get('error')
    )


# =============================
# Queries de Rebuild
# =============================

def get_rebuilds(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None
) -> PaginatedRebuildResponse:
    """
    Retorna rebuilds com paginação e filtros.
    
    Args:
        db: Sessão do banco
        page: Número da página (1-indexed)
        page_size: Itens por página (max 100)
        start_date: Filtro de data inicial
        end_date: Filtro de data final
        status: Filtro por status ('success', 'failure')
    
    Returns:
        PaginatedRebuildResponse com rebuilds e metadados
    """
    # Query base
    query = db.query(AuditLog).filter(
        AuditLog.action.in_(REBUILD_ACTIONS)
    )
    
    # Aplicar filtros
    filters = []
    if start_date:
        filters.append(AuditLog.timestamp >= start_date)
    if end_date:
        filters.append(AuditLog.timestamp <= end_date)
    if status:
        if status == 'success':
            filters.append(AuditLog.action.in_([
                'rebuild_read_models_success',
                'schema_swap_success'
            ]))
        elif status == 'failure':
            filters.append(AuditLog.action.in_([
                'rebuild_read_models_failure',
                'schema_swap_failure'
            ]))
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Total de itens
    total_items = query.count()
    
    # Calcular paginação
    total_pages = (total_items + page_size - 1) // page_size
    offset = (page - 1) * page_size
    
    # Buscar itens
    items = query.order_by(desc(AuditLog.timestamp))\
                 .limit(page_size)\
                 .offset(offset)\
                 .all()
    
    # Converter para response
    rebuild_items = []
    for item in items:
        details = json.loads(item.details) if item.details else {}
        
        # Determinar status
        item_status = 'success' if 'success' in item.action else 'failure'
        
        rebuild_items.append(RebuildAuditResponse(
            id=item.id,
            action=item.action,
            timestamp=item.timestamp,
            status=item_status,
            duration_seconds=details.get('duration_seconds'),
            events_processed=details.get('events_processed'),
            tables_updated=details.get('tables_updated'),
            phase_reached=details.get('phase_reached'),
            error=details.get('error')
        ))
    
    # Metadados
    metadata = PaginationMetadata(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )
    
    return PaginatedRebuildResponse(items=rebuild_items, metadata=metadata)


def get_rebuild_by_id(db: Session, rebuild_id: int) -> Optional[RebuildAuditResponse]:
    """
    Retorna um rebuild específico por ID.
    
    Args:
        db: Sessão do banco
        rebuild_id: ID do log de auditoria
    
    Returns:
        RebuildAuditResponse ou None se não encontrado
    """
    item = db.query(AuditLog)\
             .filter(AuditLog.id == rebuild_id)\
             .filter(AuditLog.action.in_(REBUILD_ACTIONS))\
             .first()
    
    if not item:
        return None
    
    details = json.loads(item.details) if item.details else {}
    
    # Determinar status
    status = 'success' if 'success' in item.action else 'failure'
    
    return RebuildAuditResponse(
        id=item.id,
        action=item.action,
        timestamp=item.timestamp,
        status=status,
        duration_seconds=details.get('duration_seconds'),
        events_processed=details.get('events_processed'),
        tables_updated=details.get('tables_updated'),
        phase_reached=details.get('phase_reached'),
        error=details.get('error')
    )


# =============================
# Query de Resumo (BI)
# =============================

def get_audit_summary(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> AuditSummary:
    """
    Retorna resumo de auditoria para BI/Analytics.
    
    Args:
        db: Sessão do banco
        start_date: Data inicial do período
        end_date: Data final do período
    
    Returns:
        AuditSummary com estatísticas agregadas
    """
    # Filtros de data
    filters = []
    if start_date:
        filters.append(AuditLog.timestamp >= start_date)
    if end_date:
        filters.append(AuditLog.timestamp <= end_date)
    
    # Query base com filtros
    base_query = db.query(AuditLog)
    if filters:
        base_query = base_query.filter(and_(*filters))
    
    # Contar replays
    total_replays = base_query.filter(
        AuditLog.action.in_(REPLAY_ACTIONS)
    ).count()
    
    successful_replays = base_query.filter(
        and_(
            AuditLog.action == 'replay_end',
            ~AuditLog.details.like('%error%')
        )
    ).count()
    
    failed_replays = base_query.filter(
        and_(
            AuditLog.action == 'replay_end',
            AuditLog.details.like('%error%')
        )
    ).count()
    
    # Contar rebuilds
    total_rebuilds = base_query.filter(
        AuditLog.action.in_(REBUILD_ACTIONS)
    ).count()
    
    successful_rebuilds = base_query.filter(
        AuditLog.action.in_([
            'rebuild_read_models_success',
            'schema_swap_success'
        ])
    ).count()
    
    failed_rebuilds = base_query.filter(
        AuditLog.action.in_([
            'rebuild_read_models_failure',
            'schema_swap_failure'
        ])
    ).count()
    
    # Calcular durações médias (extrair do JSON details)
    avg_replay_duration = None
    avg_rebuild_duration = None
    
    # Total de eventos processados
    total_events = 0
    replay_ends = base_query.filter(AuditLog.action == 'replay_end').all()
    for log in replay_ends:
        if log.details:
            details = json.loads(log.details)
            stats = details.get('stats', {})
            total_events += stats.get('total_events', 0)
    
    # Última operação de cada tipo
    last_replay = base_query.filter(
        AuditLog.action.in_(REPLAY_ACTIONS)
    ).order_by(desc(AuditLog.timestamp)).first()
    
    last_rebuild = base_query.filter(
        AuditLog.action.in_(REBUILD_ACTIONS)
    ).order_by(desc(AuditLog.timestamp)).first()
    
    return AuditSummary(
        total_replays=total_replays,
        total_rebuilds=total_rebuilds,
        successful_replays=successful_replays,
        failed_replays=failed_replays,
        successful_rebuilds=successful_rebuilds,
        failed_rebuilds=failed_rebuilds,
        average_replay_duration=avg_replay_duration,
        average_rebuild_duration=avg_rebuild_duration,
        total_events_processed=total_events,
        last_replay_at=last_replay.timestamp if last_replay else None,
        last_rebuild_at=last_rebuild.timestamp if last_rebuild else None
    )
