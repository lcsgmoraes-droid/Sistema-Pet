"""
WhatsApp IA - Sprint 3 Endpoints
Core IA Features: Intent detection, AI processing, metrics
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_serializer

from app.db import get_session as get_db
from app.auth import get_current_user_and_tenant
from app.whatsapp.intents import detect_intent_with_confidence, IntentType, intent_detector
from app.whatsapp.ai_service import get_ai_service
from app.whatsapp.metrics import get_metrics_analyzer

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp IA"])


# Models
class TestMessageRequest(BaseModel):
    message: str
    phone_number: str = "+5511999887766"
    session_id: Optional[str] = None


class TestMessageResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    success: bool
    intent: str
    confidence: float
    response: str
    processing_time: float
    tokens_used: int
    model_used: str
    context_messages: int


class IntentTestRequest(BaseModel):
    message: str


class IntentTestResponse(BaseModel):
    message: str
    intent: str
    confidence: float
    all_scores: Dict[str, float]


class SessionCreateRequest(BaseModel):
    telefone: str
    nome_cliente: Optional[str] = None


class SessionResponse(BaseModel):
    id: Union[str, UUID]
    tenant_id: Union[str, UUID]
    phone_number: str
    started_at: datetime
    last_message_at: Optional[datetime] = None
    status: Optional[str] = None
    
    @field_serializer('id', 'tenant_id')
    def serialize_uuid(self, value):
        return str(value) if value else None
    
    class Config:
        from_attributes = True


class MessageRequest(BaseModel):
    session_id: str
    tipo: str = "recebida"
    texto: str
    telefone: Optional[str] = None
    query: Optional[str] = None


# Endpoints
@router.post("/test/intent", response_model=IntentTestResponse)
def test_intent_detection(
    request: IntentTestRequest,
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Testa detecção de intenção"""
    intent, confidence = detect_intent_with_confidence(request.message)
    all_scores = intent_detector.get_all_scores(request.message)
    return IntentTestResponse(
        message=request.message,
        intent=intent.value,
        confidence=confidence,
        all_scores={k.value: v for k, v in all_scores.items()}
    )


@router.post("/test/message", response_model=TestMessageResponse)
async def test_ai_message(
    request: TestMessageRequest,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Testa processamento completo com IA"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        current_user, tenant_id = user_and_tenant
        logger.info(f"📨 Testando mensagem para tenant {tenant_id}: {request.message}")
        
        ai_service = get_ai_service(db, tenant_id)
        logger.info("✅ AI Service criado")
        
        result = await ai_service.process_message(
            message=request.message,
            phone_number=request.phone_number,
            session_id=request.session_id
        )
        
        logger.info(f"📊 Resultado: success={result.get('success')}, error={result.get('error')}")
        
        if not result.get("success"):
            error_msg = result.get("error", "Erro ao processar mensagem")
            logger.error(f"❌ Erro no processamento: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        from app.whatsapp.context_manager import context_manager
        context = context_manager.get_or_create_context(
            db=db,
            phone_number=request.phone_number,
            tenant_id=tenant_id
        )
        
        logger.info(f"✅ Resposta gerada com sucesso: {result.get('tokens_used')} tokens")
        
        return TestMessageResponse(
            success=True,
            intent=result.get("intent", "desconhecido"),
            confidence=result.get("confidence", 0.0),
            response=result.get("response", ""),
            processing_time=result.get("processing_time", 0.0),
            tokens_used=result.get("tokens_used", 0),
            model_used=result.get("model_used", ""),
            context_messages=len(context.messages)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro inesperado no endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/summary")
def get_metrics_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Retorna resumo de métricas"""
    current_user, tenant_id = user_and_tenant
    analyzer = get_metrics_analyzer(db, tenant_id)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    return analyzer.get_summary(start_date, end_date)


@router.get("/metrics/intents")
def get_intent_breakdown(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Retorna breakdown de intenções"""
    current_user, tenant_id = user_and_tenant
    analyzer = get_metrics_analyzer(db, tenant_id)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    return {
        "period_days": days,
        "intents": analyzer.get_intent_breakdown(start_date, end_date)
    }


@router.get("/metrics/costs")
def get_cost_breakdown(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Retorna breakdown de custos"""
    current_user, tenant_id = user_and_tenant
    analyzer = get_metrics_analyzer(db, tenant_id)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    costs = analyzer.get_cost_breakdown(start_date, end_date)
    return {"period_days": days, **costs}


# ========================================
# SESSIONS
# ========================================

@router.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session(
    request: SessionCreateRequest,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Criar nova sessão de WhatsApp"""
    from app.whatsapp.models import WhatsAppSession
    import uuid
    
    current_user, tenant_id = user_and_tenant
    
    # Verificar se já existe sessão ativa para esse telefone
    existing_session = db.query(WhatsAppSession).filter(
        WhatsAppSession.tenant_id == tenant_id,
        WhatsAppSession.phone_number == request.telefone
    ).order_by(WhatsAppSession.started_at.desc()).first()
    
    # Se já existe e foi usada recentemente (últimas 24h), retornar a existente
    if existing_session and existing_session.last_message_at:
        time_diff = datetime.utcnow() - existing_session.last_message_at
        if time_diff.total_seconds() < 86400:  # 24 horas
            return existing_session
    
    # Criar nova sessão
    new_session = WhatsAppSession(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        phone_number=request.telefone,
        status="bot",
        started_at=datetime.utcnow(),
        last_message_at=datetime.utcnow()
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return new_session


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_whatsapp_session(
    session_id: str,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant)
):
    """Obter detalhes de uma sessão"""
    from app.whatsapp.models import WhatsAppSession
    
    current_user, tenant_id = user_and_tenant
    
    session = db.query(WhatsAppSession).filter(
        WhatsAppSession.id == session_id,
        WhatsAppSession.tenant_id == tenant_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return session


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db)
):
    """Obter mensagens de uma sessão"""
    from app.whatsapp.models import WhatsAppMessage
    
    current_user, tenant_id = user_and_tenant
    
    messages = db.query(WhatsAppMessage).filter(
        WhatsAppMessage.session_id == session_id,
        WhatsAppMessage.tenant_id == tenant_id
    ).order_by(WhatsAppMessage.created_at).all()
    
    return messages


@router.post("/messages")
async def process_message(
    request: MessageRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db)
):
    """Processar mensagem recebida do cliente"""
    from app.whatsapp.models import WhatsAppMessage
    import uuid
    
    current_user, tenant_id = user_and_tenant
    
    session_id = request.session_id
    tipo = request.tipo
    texto = request.texto
    
    # Criar mensagem recebida
    message = WhatsAppMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        tenant_id=tenant_id,
        tipo=tipo,
        conteudo=texto,
        created_at=datetime.utcnow()
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Simular resposta da IA (simplificado para teste)
    response_message = WhatsAppMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        tenant_id=tenant_id,
        tipo="enviada",
        conteudo=f"Obrigado pela mensagem: '{texto}'. Como posso ajudar?",
        created_at=datetime.utcnow()
    )
    
    db.add(response_message)
    db.commit()
    db.refresh(response_message)
    
    return {
        "id": str(response_message.id),
        "texto": response_message.conteudo,
        "tipo": response_message.tipo
    }
