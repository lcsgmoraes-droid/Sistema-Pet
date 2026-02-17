"""
Módulo de Auditoria - Fase 5.6
================================

API read-only para consulta de auditoria de replays e rebuilds.
"""

from .schemas import (
    ReplayAuditResponse,
    RebuildAuditResponse,
    PaginatedReplayResponse,
    PaginatedRebuildResponse,
    AuditSummary
)
from .queries import (
    get_replays,
    get_replay_by_id,
    get_rebuilds,
    get_rebuild_by_id,
    get_audit_summary
)
from .api import router

__all__ = [
    # Schemas
    'ReplayAuditResponse',
    'RebuildAuditResponse',
    'PaginatedReplayResponse',
    'PaginatedRebuildResponse',
    'AuditSummary',
    
    # Queries
    'get_replays',
    'get_replay_by_id',
    'get_rebuilds',
    'get_rebuild_by_id',
    'get_audit_summary',
    
    # Router
    'router'
]
