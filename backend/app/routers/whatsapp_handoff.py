"""
WhatsApp Human Handoff API Routes - Sprint 4

Endpoints para gerenciamento de transferências para atendimento humano:
- CRUD de agents (atendentes)
- Handoffs (transferências)
- Chat dashboard
- Bot assist
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime

from app.db import get_session as get_db
from app.auth import get_current_user
from app.models import User
from app.whatsapp.models_handoff import WhatsAppAgent, WhatsAppHandoff, WhatsAppInternalNote
from app.whatsapp.schemas_handoff import (
    WhatsAppAgentCreate,
    WhatsAppAgentUpdate,
    WhatsAppAgentResponse,
    WhatsAppHandoffResponse,
    WhatsAppHandoffAssign,
    WhatsAppInternalNoteCreate,
    WhatsAppInternalNoteResponse,
    HandoffDashboardResponse,
    HandoffStats
)
from app.whatsapp.sentiment import SentimentAnalyzer
from app.whatsapp.handoff_manager import HandoffManager
from app.whatsapp.websocket import (
    emit_new_handoff, emit_handoff_assigned, 
    emit_handoff_resolved, emit_agent_status_change
)

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp Handoff - Sprint 4"])


# ========================================
# AGENTS (Atendentes)
# ========================================

@router.post("/agents", response_model=WhatsAppAgentResponse, status_code=201)
async def create_agent(
    agent_data: WhatsAppAgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Criar novo agente (atendente humano)
    """
    # Verificar se email já existe
    existing = db.query(WhatsAppAgent).filter(
        and_(
            WhatsAppAgent.tenant_id == current_user.tenant_id,
            WhatsAppAgent.email == agent_data.email
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Agent with this email already exists")
    
    # Criar agent
    agent = WhatsAppAgent(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,  # Adicionar user_id
        name=agent_data.name,
        email=agent_data.email,
        status=agent_data.status,
        max_concurrent_chats=agent_data.max_concurrent_chats or 5
    )
    
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    return agent


@router.get("/agents", response_model=List[WhatsAppAgentResponse])
async def list_agents(
    status: Optional[str] = Query(None, description="Filtrar por status: available, busy, offline"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar todos os agentes
    """
    query = db.query(WhatsAppAgent).filter(
        WhatsAppAgent.tenant_id == current_user.tenant_id
    )
    
    if status:
        query = query.filter(WhatsAppAgent.status == status)
    
    agents = query.order_by(WhatsAppAgent.name).all()
    return agents


@router.get("/agents/{agent_id}", response_model=WhatsAppAgentResponse)
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Buscar agente por ID
    """
    agent = db.query(WhatsAppAgent).filter(
        and_(
            WhatsAppAgent.id == agent_id,
            WhatsAppAgent.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent


@router.put("/agents/{agent_id}", response_model=WhatsAppAgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: WhatsAppAgentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atualizar dados do agente
    """
    agent = db.query(WhatsAppAgent).filter(
        and_(
            WhatsAppAgent.id == agent_id,
            WhatsAppAgent.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Atualizar campos
    for field, value in agent_data.dict(exclude_unset=True).items():
        setattr(agent, field, value)
    
    db.commit()
    db.refresh(agent)
    
    # Emit agent status change event if status changed
    if 'status' in agent_data.dict(exclude_unset=True):
        await emit_agent_status_change({
            "id": str(agent.id),
            "name": agent.name,
            "status": agent.status,
            "current_chats": agent.current_chats
        }, db)
    
    return agent


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletar agente
    """
    agent = db.query(WhatsAppAgent).filter(
        and_(
            WhatsAppAgent.id == agent_id,
            WhatsAppAgent.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Verificar se tem handoffs ativos
    active_handoffs = db.query(WhatsAppHandoff).filter(
        and_(
            WhatsAppHandoff.assigned_agent_id == agent_id,
            WhatsAppHandoff.status.in_(["pending", "active"])
        )
    ).count()
    
    if active_handoffs > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete agent with {active_handoffs} active handoffs"
        )
    
    db.delete(agent)
    db.commit()
    
    return None


# ========================================
# HANDOFFS (Transferências)
# ========================================

@router.get("/handoffs", response_model=List[WhatsAppHandoffResponse])
async def list_handoffs(
    status: Optional[str] = Query(None, description="pending, active, resolved, cancelled"),
    priority: Optional[str] = Query(None, description="low, medium, high, urgent"),
    agent_id: Optional[str] = Query(None, description="Filtrar por agente atribuído"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar handoffs (transferências para humano)
    """
    query = db.query(WhatsAppHandoff).filter(
        WhatsAppHandoff.tenant_id == current_user.tenant_id
    )
    
    if status:
        query = query.filter(WhatsAppHandoff.status == status)
    
    if priority:
        query = query.filter(WhatsAppHandoff.priority == priority)
    
    if agent_id:
        query = query.filter(WhatsAppHandoff.assigned_agent_id == agent_id)
    
    handoffs = query.order_by(
        WhatsAppHandoff.priority.desc(),
        WhatsAppHandoff.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return handoffs


@router.get("/handoffs/pending", response_model=List[WhatsAppHandoffResponse])
async def list_pending_handoffs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar apenas handoffs pendentes (aguardando atendimento)
    """
    handoffs = db.query(WhatsAppHandoff).filter(
        and_(
            WhatsAppHandoff.tenant_id == current_user.tenant_id,
            WhatsAppHandoff.status == "pending"
        )
    ).order_by(
        WhatsAppHandoff.priority.desc(),
        WhatsAppHandoff.created_at.asc()
    ).offset(skip).limit(limit).all()
    
    return handoffs


@router.get("/handoffs/{handoff_id}", response_model=WhatsAppHandoffResponse)
async def get_handoff(
    handoff_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Buscar handoff por ID
    """
    handoff = db.query(WhatsAppHandoff).filter(
        and_(
            WhatsAppHandoff.id == handoff_id,
            WhatsAppHandoff.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    
    return handoff


@router.post("/handoffs/{handoff_id}/assign", response_model=WhatsAppHandoffResponse)
async def assign_handoff(
    handoff_id: str,
    assign_data: WhatsAppHandoffAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atribuir handoff para um agente
    """
    handoff = db.query(WhatsAppHandoff).filter(
        and_(
            WhatsAppHandoff.id == handoff_id,
            WhatsAppHandoff.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    
    if handoff.status not in ["pending", "active"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot assign handoff with status: {handoff.status}"
        )
    
    # Verificar se agente existe e está disponível
    agent = db.query(WhatsAppAgent).filter(
        and_(
            WhatsAppAgent.id == assign_data.agent_id,
            WhatsAppAgent.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent.status == "offline":
        raise HTTPException(status_code=400, detail="Agent is offline")
    
    # Verificar capacidade do agente
    active_count = db.query(WhatsAppHandoff).filter(
        and_(
            WhatsAppHandoff.assigned_agent_id == agent.id,
            WhatsAppHandoff.status == "active"
        )
    ).count()
    
    if active_count >= agent.max_concurrent_chats:
        raise HTTPException(
            status_code=400, 
            detail=f"Agent has reached max concurrent chats ({agent.max_concurrent_chats})"
        )
    
    # Atribuir
    handoff.assigned_agent_id = agent.id
    handoff.status = "active"
    handoff.assigned_at = datetime.utcnow()
    
    # Atualizar status do agente
    if active_count + 1 >= agent.max_concurrent_chats:
        agent.status = "busy"
    
    db.commit()
    db.refresh(handoff)
    
    # Emit WebSocket event
    await emit_handoff_assigned({
        "id": str(handoff.id),
        "session_id": handoff.session_id,
        "phone_number": handoff.phone_number,
        "customer_name": handoff.customer_name,
        "status": handoff.status,
        "assigned_agent_id": str(handoff.assigned_agent_id),
        "priority": handoff.priority
    }, str(agent.id))
    
    return handoff


@router.post("/handoffs/{handoff_id}/resolve", response_model=WhatsAppHandoffResponse)
async def resolve_handoff(
    handoff_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marcar handoff como resolvido
    """
    handoff = db.query(WhatsAppHandoff).filter(
        and_(
            WhatsAppHandoff.id == handoff_id,
            WhatsAppHandoff.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    
    handoff.status = "resolved"
    handoff.resolved_at = datetime.utcnow()
    
    # Liberar capacidade do agente
    if handoff.assigned_agent_id:
        agent = db.query(WhatsAppAgent).filter(
            WhatsAppAgent.id == handoff.assigned_agent_id
        ).first()
        
        if agent:
            active_count = db.query(WhatsAppHandoff).filter(
                and_(
                    WhatsAppHandoff.assigned_agent_id == agent.id,
                    WhatsAppHandoff.status == "active",
                    WhatsAppHandoff.id != handoff_id
                )
            ).count()
            
            if active_count < agent.max_concurrent_chats and agent.status == "busy":
                agent.status = "available"
    
    db.commit()
    db.refresh(handoff)
    
    # Emit WebSocket event
    await emit_handoff_resolved(handoff_id, db)
    
    return handoff


# ========================================
# INTERNAL NOTES (Notas Internas)
# ========================================

@router.post("/handoffs/{handoff_id}/notes", response_model=WhatsAppInternalNoteResponse, status_code=201)
async def create_note(
    handoff_id: str,
    note_data: WhatsAppInternalNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Adicionar nota interna ao handoff
    """
    handoff = db.query(WhatsAppHandoff).filter(
        and_(
            WhatsAppHandoff.id == handoff_id,
            WhatsAppHandoff.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    
    note = WhatsAppInternalNote(
        handoff_id=handoff_id,
        author_id=note_data.author_id,
        content=note_data.content,
        note_type=note_data.note_type or "info"
    )
    
    db.add(note)
    db.commit()
    db.refresh(note)
    
    return note


@router.get("/handoffs/{handoff_id}/notes", response_model=List[WhatsAppInternalNoteResponse])
async def list_notes(
    handoff_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar notas de um handoff
    """
    # Verificar se handoff existe
    handoff = db.query(WhatsAppHandoff).filter(
        and_(
            WhatsAppHandoff.id == handoff_id,
            WhatsAppHandoff.tenant_id == current_user.tenant_id
        )
    ).first()
    
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    
    notes = db.query(WhatsAppInternalNote).filter(
        WhatsAppInternalNote.handoff_id == handoff_id
    ).order_by(WhatsAppInternalNote.created_at).all()
    
    return notes


# ========================================
# DASHBOARD & STATS
# ========================================

@router.get("/handoffs/dashboard/stats", response_model=HandoffStats)
async def get_handoff_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Estatísticas do dashboard de handoffs
    """
    tenant_id = current_user.tenant_id
    
    # Total de handoffs
    total_handoffs = db.query(WhatsAppHandoff).filter(
        WhatsAppHandoff.tenant_id == tenant_id
    ).count()
    
    # Pendentes
    pending_count = db.query(WhatsAppHandoff).filter(
        and_(
            WhatsAppHandoff.tenant_id == tenant_id,
            WhatsAppHandoff.status == "pending"
        )
    ).count()
    
    # Ativos
    active_count = db.query(WhatsAppHandoff).filter(
        and_(
            WhatsAppHandoff.tenant_id == tenant_id,
            WhatsAppHandoff.status == "active"
        )
    ).count()
    
    # Resolvidos
    resolved_count = db.query(WhatsAppHandoff).filter(
        and_(
            WhatsAppHandoff.tenant_id == tenant_id,
            WhatsAppHandoff.status == "resolved"
        )
    ).count()
    
    # Agentes disponíveis
    available_agents = db.query(WhatsAppAgent).filter(
        and_(
            WhatsAppAgent.tenant_id == tenant_id,
            WhatsAppAgent.status == "available"
        )
    ).count()
    
    # Tempo médio de resposta (simplificado)
    avg_response_time = 120  # TODO: Calcular real
    
    return HandoffStats(
        total_handoffs=total_handoffs,
        pending_count=pending_count,
        active_count=active_count,
        resolved_count=resolved_count,
        available_agents=available_agents,
        avg_response_time_seconds=avg_response_time
    )


# ========================================
# SENTIMENT TESTING (Debug)
# ========================================

@router.post("/test-sentiment")
async def test_sentiment(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Testar análise de sentimento (debug)
    """
    message = data.get("message", "")
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze(message)
    
    return {
        "message": message,
        "score": float(result["score"]),
        "label": result["label"],
        "confidence": result["confidence"],
        "emotions": result["emotions"],
        "keywords_found": result["triggers"],
        "should_handoff": result["should_handoff"],
        "handoff_reason": result["handoff_reason"]
    }
