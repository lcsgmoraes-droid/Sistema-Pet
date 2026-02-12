"""
Schemas de Auditoria - Fase 5.6
================================

Modelos Pydantic para resposta de API de auditoria.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AuditStatus(str, Enum):
    """Status de operação de auditoria"""
    SUCCESS = "success"
    FAILURE = "failure"
    IN_PROGRESS = "in_progress"


class AuditAction(str, Enum):
    """Tipos de ação auditada"""
    REPLAY_START = "replay_start"
    REPLAY_END = "replay_end"
    REBUILD_START = "rebuild_start"
    REBUILD_SUCCESS = "rebuild_read_models_success"
    REBUILD_FAILURE = "rebuild_read_models_failure"
    SCHEMA_SWAP_SUCCESS = "schema_swap_success"
    SCHEMA_SWAP_FAILURE = "schema_swap_failure"


class ReplayFilters(BaseModel):
    """Filtros aplicados em um replay"""
    user_id: Optional[int] = None
    event_type: Optional[str] = None
    aggregate_id: Optional[str] = None
    from_sequence: Optional[int] = None
    to_sequence: Optional[int] = None
    batch_size: Optional[int] = None


class ReplayStats(BaseModel):
    """Estatísticas de um replay"""
    total_events: int
    batches_processed: int
    duration_seconds: float
    events_per_second: Optional[float] = None


class ReplayAuditResponse(BaseModel):
    """Resposta de auditoria de replay"""
    id: int
    action: str
    timestamp: datetime
    status: str
    filters: Optional[Dict[str, Any]] = None
    stats: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RebuildPhase(str, Enum):
    """Fases do rebuild"""
    NOT_STARTED = "not_started"
    CREATING_TEMP_SCHEMA = "creating_temp_schema"
    REPLAYING_EVENTS = "replaying_events"
    VALIDATING_TEMP_SCHEMA = "validating_temp_schema"
    SWAPPING_SCHEMAS = "swapping_schemas"
    COMPLETED = "completed"


class RebuildAuditResponse(BaseModel):
    """Resposta de auditoria de rebuild"""
    id: int
    action: str
    timestamp: datetime
    status: str
    duration_seconds: Optional[float] = None
    events_processed: Optional[int] = None
    tables_updated: Optional[List[str]] = None
    phase_reached: Optional[str] = None
    error: Optional[str] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationMetadata(BaseModel):
    """Metadados de paginação"""
    page: int = Field(ge=1, description="Página atual")
    page_size: int = Field(ge=1, le=100, description="Itens por página")
    total_items: int = Field(ge=0, description="Total de itens")
    total_pages: int = Field(ge=0, description="Total de páginas")
    has_next: bool = Field(description="Tem próxima página")
    has_previous: bool = Field(description="Tem página anterior")


class PaginatedReplayResponse(BaseModel):
    """Resposta paginada de replays"""
    items: List[ReplayAuditResponse]
    metadata: PaginationMetadata


class PaginatedRebuildResponse(BaseModel):
    """Resposta paginada de rebuilds"""
    items: List[RebuildAuditResponse]
    metadata: PaginationMetadata


class AuditSummary(BaseModel):
    """Resumo de auditoria (para BI/Analytics)"""
    total_replays: int
    total_rebuilds: int
    successful_replays: int
    failed_replays: int
    successful_rebuilds: int
    failed_rebuilds: int
    average_replay_duration: Optional[float] = None
    average_rebuild_duration: Optional[float] = None
    total_events_processed: int
    last_replay_at: Optional[datetime] = None
    last_rebuild_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
