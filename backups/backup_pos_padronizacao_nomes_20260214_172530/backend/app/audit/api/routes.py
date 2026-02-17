"""
API de Auditoria - Fase 5.6
============================

Endpoints REST read-only para consulta de auditoria.

SOMENTE LEITURA (GET) - SEM MUTAÇÕES
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db import get_session
from app.auth.dependencies import require_admin
from app.models import User
from app.audit.schemas import (
    PaginatedReplayResponse,
    PaginatedRebuildResponse,
    ReplayAuditResponse,
    RebuildAuditResponse,
    AuditSummary
)
from app.audit.queries import (
    get_replays,
    get_replay_by_id,
    get_rebuilds,
    get_rebuild_by_id,
    get_audit_summary
)


router = APIRouter(
    prefix="/audit",
    tags=["Auditoria (Read-Only)"],
    dependencies=[Depends(require_admin)]  # APENAS ADMIN
)


# =============================
# Endpoints de Replay
# =============================

@router.get("/replays", response_model=PaginatedReplayResponse)
def list_replays(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    start_date: Optional[datetime] = Query(None, description="Data inicial (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Data final (ISO 8601)"),
    status: Optional[str] = Query(None, pattern="^(success|failure|in_progress)$", description="Filtrar por status"),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """
    **[READ-ONLY]** Lista todos os replays de eventos com paginação.
    
    - **Requer**: Permissão de administrador
    - **Retorna**: Lista paginada de auditorias de replay
    - **Filtros**: data inicial/final, status
    
    **Casos de uso**:
    - BI/Analytics: análise de performance de replays
    - Troubleshooting: investigar falhas em replays
    - Governança: rastrear quem executou replays e quando
    """
    return get_replays(
        db=db,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        status=status
    )


@router.get("/replays/{replay_id}", response_model=ReplayAuditResponse)
def get_replay(
    replay_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """
    **[READ-ONLY]** Retorna detalhes de um replay específico.
    
    - **Requer**: Permissão de administrador
    - **Retorna**: Detalhes completos do replay (filtros, stats, erro)
    
    **Casos de uso**:
    - Análise detalhada de replay individual
    - Debug de falhas específicas
    - Extração de métricas para BI
    """
    replay = get_replay_by_id(db=db, replay_id=replay_id)
    
    if not replay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Replay com ID {replay_id} não encontrado"
        )
    
    return replay


# =============================
# Endpoints de Rebuild
# =============================

@router.get("/rebuilds", response_model=PaginatedRebuildResponse)
def list_rebuilds(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    start_date: Optional[datetime] = Query(None, description="Data inicial (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Data final (ISO 8601)"),
    status: Optional[str] = Query(None, pattern="^(success|failure)$", description="Filtrar por status"),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """
    **[READ-ONLY]** Lista todos os rebuilds de read models com paginação.
    
    - **Requer**: Permissão de administrador
    - **Retorna**: Lista paginada de auditorias de rebuild
    - **Filtros**: data inicial/final, status
    
    **Casos de uso**:
    - BI/Analytics: análise de tempo de rebuild
    - Troubleshooting: investigar falhas em schema swap
    - Governança: rastrear rebuilds completos
    """
    return get_rebuilds(
        db=db,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        status=status
    )


@router.get("/rebuilds/{rebuild_id}", response_model=RebuildAuditResponse)
def get_rebuild(
    rebuild_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """
    **[READ-ONLY]** Retorna detalhes de um rebuild específico.
    
    - **Requer**: Permissão de administrador
    - **Retorna**: Detalhes completos do rebuild (duração, eventos, tabelas, fase, erro)
    
    **Casos de uso**:
    - Análise detalhada de rebuild individual
    - Debug de falhas em schema swap
    - Extração de métricas para BI
    """
    rebuild = get_rebuild_by_id(db=db, rebuild_id=rebuild_id)
    
    if not rebuild:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rebuild com ID {rebuild_id} não encontrado"
        )
    
    return rebuild


# =============================
# Endpoint de Resumo (BI)
# =============================

@router.get("/summary", response_model=AuditSummary)
def get_summary(
    start_date: Optional[datetime] = Query(None, description="Data inicial (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Data final (ISO 8601)"),
    db: Session = Depends(get_session),
    current_user: User = Depends(require_admin)
):
    """
    **[READ-ONLY]** Retorna resumo agregado de auditoria.
    
    - **Requer**: Permissão de administrador
    - **Retorna**: Estatísticas agregadas de replays e rebuilds
    - **Filtros**: período de tempo
    
    **Casos de uso**:
    - Dashboard de BI/Analytics
    - Métricas de governança
    - Análise de tendências de performance
    
    **Métricas incluídas**:
    - Total de replays/rebuilds
    - Taxa de sucesso/falha
    - Duração média
    - Total de eventos processados
    - Última execução de cada tipo
    """
    return get_audit_summary(
        db=db,
        start_date=start_date,
        end_date=end_date
    )
