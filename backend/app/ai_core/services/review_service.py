"""
ReviewService - Gerenciamento da fila de revisão humana (HITL)

Responsável por:
- Adicionar decisões à Review Queue
- Listar decisões pendentes
- Processar feedback humano
- Publicar DecisionReviewedEvent
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import uuid

from ..domain.review import (
    ReviewQueueEntry,
    DecisionReviewStatus,
    ReviewPriority,
    HumanReviewFeedback
)
from ..domain.events import DecisionReviewedEvent
from ..models.decision_log import ReviewQueueModel, DecisionLog

logger = logging.getLogger(__name__)


class ReviewService:
    """
    Serviço de revisão humana (Human-in-the-Loop).
    
    Fluxo típico:
    1. DecisionService detecta confiança MEDIUM/LOW
    2. Chama review_service.add_to_queue(decision_result, context)
    3. Frontend consulta review_service.get_pending_reviews(tenant_id)
    4. Humano revisa e chama review_service.submit_review(feedback)
    5. ReviewService publica DecisionReviewedEvent
    6. LearningService consome evento e ajusta padrões
    
    Princípios:
    - Nunca altera estado de negócio diretamente
    - Apenas materializa fila e publica eventos
    - Multi-tenant por design
    - Auditável e rastreável
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def add_to_queue(
        self,
        request_id: str,
        decision_log_id: int,
        tenant_id: int,
        decision_type: str,
        decision_summary: str,
        confidence_score: int,
        confidence_level: str,
        context_data: Dict[str, Any],
        ai_decision: Dict[str, Any],
        ai_explanation: str
    ) -> ReviewQueueEntry:
        """
        Adiciona decisão à fila de revisão.
        
        Chamado automaticamente pelo DecisionService quando
        confiança é MEDIUM ou LOW.
        
        Args:
            request_id: ID da decisão original
            decision_log_id: ID do log de decisão
            tenant_id: ID do tenant
            decision_type: Tipo de decisão
            decision_summary: Resumo legível para o revisor
            confidence_score: Score original (0-100)
            confidence_level: MEDIUM ou LOW
            context_data: Dados contextuais para revisão
            ai_decision: Decisão sugerida pela IA
            ai_explanation: Explicação da IA
        
        Returns:
            ReviewQueueEntry criado
        """
        # Calcular prioridade
        priority = self._calculate_priority(confidence_score, confidence_level)
        
        # Criar entrada na fila
        queue_entry = ReviewQueueModel(
            request_id=request_id,
            decision_log_id=decision_log_id,
            tenant_id=tenant_id,
            decision_type=decision_type,
            decision_summary=decision_summary,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            priority=priority.value,
            context_data=context_data,
            ai_decision=ai_decision,
            ai_explanation=ai_explanation,
            status=DecisionReviewStatus.PENDING.value
        )
        
        self.db.add(queue_entry)
        self.db.commit()
        self.db.refresh(queue_entry)
        
        logger.info(
            f"✅ Decisão adicionada à fila de revisão | "
            f"ID: {request_id} | Tenant: {tenant_id} | "
            f"Confiança: {confidence_score} | Prioridade: {priority.value}"
        )
        
        return self._model_to_domain(queue_entry)
    
    def get_pending_reviews(
        self,
        tenant_id: int,
        decision_type: Optional[str] = None,
        priority: Optional[ReviewPriority] = None,
        limit: int = 50
    ) -> List[ReviewQueueEntry]:
        """
        Lista decisões pendentes de revisão para um tenant.
        
        Args:
            tenant_id: ID do tenant
            decision_type: Filtro opcional por tipo
            priority: Filtro opcional por prioridade
            limit: Limite de resultados
        
        Returns:
            Lista de ReviewQueueEntry pendentes
        """
        query = self.db.query(ReviewQueueModel).filter(
            and_(
                ReviewQueueModel.tenant_id == tenant_id,
                ReviewQueueModel.status == DecisionReviewStatus.PENDING.value
            )
        )
        
        if decision_type:
            query = query.filter(ReviewQueueModel.decision_type == decision_type)
        
        if priority:
            query = query.filter(ReviewQueueModel.priority == priority.value)
        
        # Ordenar por prioridade e data
        priority_order = {
            "urgent": 0,
            "high": 1,
            "medium": 2,
            "low": 3
        }
        
        results = query.order_by(
            ReviewQueueModel.created_at.asc()
        ).limit(limit).all()
        
        # Ordenar por prioridade manualmente (SQLAlchemy não tem CASE fácil)
        results = sorted(
            results,
            key=lambda x: (priority_order.get(x.priority, 999), x.created_at)
        )
        
        return [self._model_to_domain(r) for r in results]
    
    def submit_review(
        self,
        feedback: HumanReviewFeedback
    ) -> DecisionReviewedEvent:
        """
        Processa feedback humano sobre uma decisão.
        
        Fluxo:
        1. Atualiza ReviewQueueModel (status, reviewed_by, etc)
        2. Cria DecisionReviewedEvent
        3. Retorna evento (caller deve publicar no event bus)
        
        Args:
            feedback: HumanReviewFeedback com ação tomada
        
        Returns:
            DecisionReviewedEvent para ser publicado
        
        Raises:
            ValueError: Se decisão não existir ou já foi revisada
        """
        # Buscar entrada na fila
        queue_entry = self.db.query(ReviewQueueModel).filter(
            ReviewQueueModel.request_id == feedback.request_id
        ).first()
        
        if not queue_entry:
            raise ValueError(f"Decisão {feedback.request_id} não encontrada na fila")
        
        if queue_entry.status != DecisionReviewStatus.PENDING.value:
            raise ValueError(
                f"Decisão {feedback.request_id} já foi revisada "
                f"(status: {queue_entry.status})"
            )
        
        # Atualizar entrada na fila
        queue_entry.status = feedback.action.value
        queue_entry.reviewed_by = feedback.reviewer_id
        queue_entry.reviewed_at = feedback.review_timestamp
        queue_entry.review_action = feedback.action.value
        queue_entry.corrected_data = feedback.corrected_decision
        queue_entry.review_comment = feedback.comment
        
        # Atualizar DecisionLog também
        decision_log = self.db.query(DecisionLog).filter(
            DecisionLog.id == queue_entry.decision_log_id
        ).first()
        
        if decision_log:
            decision_log.was_reviewed = True
            decision_log.reviewed_at = feedback.review_timestamp
        
        self.db.commit()
        
        # Criar evento
        event = DecisionReviewedEvent(
            event_id=f"evt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
            decision_id=feedback.request_id,
            decision_log_id=queue_entry.decision_log_id,
            decision_type=queue_entry.decision_type,
            tenant_id=queue_entry.tenant_id,
            reviewer_id=feedback.reviewer_id,
            action_taken=feedback.action.value,
            original_decision=queue_entry.ai_decision,
            confidence_score_original=queue_entry.confidence_score,
            corrected_data=feedback.corrected_decision,
            comment=feedback.comment,
            processing_context={
                "confidence_level": queue_entry.confidence_level,
                "priority": queue_entry.priority,
                "ai_explanation": queue_entry.ai_explanation
            }
        )
        
        logger.info(
            f"✅ Revisão processada | "
            f"Decisão: {feedback.request_id} | "
            f"Ação: {feedback.action.value} | "
            f"Revisor: {feedback.reviewer_id}"
        )
        
        return event
    
    def get_review_by_request_id(
        self,
        request_id: str
    ) -> Optional[ReviewQueueEntry]:
        """
        Busca uma entrada específica na fila por request_id.
        """
        queue_entry = self.db.query(ReviewQueueModel).filter(
            ReviewQueueModel.request_id == request_id
        ).first()
        
        return self._model_to_domain(queue_entry) if queue_entry else None
    
    def get_review_stats(self, tenant_id: int) -> Dict[str, Any]:
        """
        Estatísticas da fila de revisão para um tenant.
        
        Returns:
            {
                "pending": 15,
                "approved": 45,
                "corrected": 12,
                "rejected": 3,
                "avg_review_time_minutes": 8.5
            }
        """
        from sqlalchemy import func
        
        stats = {}
        
        # Count por status
        for status in DecisionReviewStatus:
            count = self.db.query(func.count(ReviewQueueModel.id)).filter(
                and_(
                    ReviewQueueModel.tenant_id == tenant_id,
                    ReviewQueueModel.status == status.value
                )
            ).scalar()
            stats[status.value] = count
        
        # Tempo médio de revisão (em minutos)
        reviewed = self.db.query(ReviewQueueModel).filter(
            and_(
                ReviewQueueModel.tenant_id == tenant_id,
                ReviewQueueModel.reviewed_at.isnot(None)
            )
        ).all()
        
        if reviewed:
            times = [
                (r.reviewed_at - r.created_at).total_seconds() / 60
                for r in reviewed
            ]
            stats["avg_review_time_minutes"] = round(sum(times) / len(times), 2)
        else:
            stats["avg_review_time_minutes"] = 0.0
        
        return stats
    
    # ==================== PRIVADOS ====================
    
    def _calculate_priority(
        self,
        confidence_score: int,
        confidence_level: str
    ) -> ReviewPriority:
        """
        Calcula prioridade com base na confiança.
        
        - VERY_LOW (0-39): URGENT (IA muito incerta)
        - LOW (40-59): HIGH
        - MEDIUM baixo (60-69): MEDIUM
        - MEDIUM alto (70-79): LOW
        """
        if confidence_score < 40:
            return ReviewPriority.URGENT
        elif confidence_score < 60:
            return ReviewPriority.HIGH
        elif confidence_score < 70:
            return ReviewPriority.MEDIUM
        else:
            return ReviewPriority.LOW
    
    def _model_to_domain(self, model: ReviewQueueModel) -> ReviewQueueEntry:
        """Converte ReviewQueueModel para ReviewQueueEntry (domain)."""
        return ReviewQueueEntry(
            id=model.id,
            request_id=model.request_id,
            decision_log_id=model.decision_log_id,
            tenant_id=model.tenant_id,
            decision_type=model.decision_type,
            decision_summary=model.decision_summary,
            confidence_score=model.confidence_score,
            confidence_level=model.confidence_level,
            priority=ReviewPriority(model.priority),
            context_data=model.context_data,
            ai_decision=model.ai_decision,
            ai_explanation=model.ai_explanation,
            status=DecisionReviewStatus(model.status),
            reviewed_by=model.reviewed_by,
            reviewed_at=model.reviewed_at,
            review_action=model.review_action,
            corrected_data=model.corrected_data,
            review_comment=model.review_comment,
            created_at=model.created_at
        )
