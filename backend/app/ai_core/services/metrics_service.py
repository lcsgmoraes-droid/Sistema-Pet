"""
MetricsService - Cálculo e gerenciamento de métricas de IA

Responsável por:
- Calcular métricas de performance
- Atualizar snapshots (Read Models)
- Fornecer métricas agregadas
- Calcular tendências
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case
import logging

from ..domain.metrics import (
    AIPerformanceMetrics,
    MetricPeriod,
    MetricTrend
)
from ..domain.events import DecisionReviewedEvent
from ..models.decision_log import (
    DecisionLog,
    ReviewQueueModel,
    FeedbackLog,
    AIMetricsSnapshotModel
)

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Serviço de cálculo de métricas de performance da IA.
    
    CQRS Pattern:
    - Write: Atualiza snapshots incrementalmente quando evento ocorre
    - Read: Consulta snapshots pré-calculados
    
    Granularidade:
    - tenant_id: Isolamento multi-tenant
    - decision_type: Por módulo (extrato, vendas, etc)
    - period: daily, weekly, monthly, all_time
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== READ (CONSULTAS) ====================
    
    def get_metrics(
        self,
        tenant_id: int,
        decision_type: Optional[str] = None,
        period: MetricPeriod = MetricPeriod.ALL_TIME
    ) -> Optional[AIPerformanceMetrics]:
        """
        Consulta métricas pré-calculadas de um snapshot.
        
        Args:
            tenant_id: ID do tenant
            decision_type: Tipo de decisão (None = todas)
            period: Período de agregação
        
        Returns:
            AIPerformanceMetrics ou None se não existir
        """
        # Calcular datas do período
        period_start, period_end = self._get_period_dates(period)
        
        # Buscar snapshot
        snapshot = self.db.query(AIMetricsSnapshotModel).filter(
            and_(
                AIMetricsSnapshotModel.tenant_id == tenant_id,
                AIMetricsSnapshotModel.decision_type == decision_type,
                AIMetricsSnapshotModel.period == period.value,
                AIMetricsSnapshotModel.period_start == period_start
            )
        ).first()
        
        if not snapshot:
            # Snapshot não existe, calcular sob demanda
            logger.info(f"Snapshot não encontrado, calculando métricas sob demanda...")
            return self.calculate_metrics_realtime(
                tenant_id=tenant_id,
                decision_type=decision_type,
                period_start=period_start,
                period_end=period_end,
                period=period
            )
        
        # Converter snapshot para domain model
        return self._snapshot_to_domain(snapshot)
    
    def calculate_metrics_realtime(
        self,
        tenant_id: int,
        decision_type: Optional[str],
        period_start: date,
        period_end: date,
        period: MetricPeriod
    ) -> AIPerformanceMetrics:
        """
        Calcula métricas diretamente dos dados (sem cache).
        
        Usado quando snapshot não existe ou para recalcular.
        """
        # Base query
        query = self.db.query(DecisionLog).filter(
            and_(
                DecisionLog.user_id == tenant_id,
                DecisionLog.created_at >= period_start,
                DecisionLog.created_at <= period_end
            )
        )
        
        if decision_type:
            query = query.filter(DecisionLog.decision_type == decision_type)
        
        decisions = query.all()
        
        # Volumetria
        total_decisions = len(decisions)
        decisions_reviewed = sum(1 for d in decisions if d.was_reviewed)
        decisions_auto_executed = sum(1 for d in decisions if d.was_applied and not d.was_reviewed)
        
        # Distribuição por confiança
        very_high = sum(1 for d in decisions if d.confidence >= 90)
        high = sum(1 for d in decisions if 80 <= d.confidence < 90)
        medium = sum(1 for d in decisions if 60 <= d.confidence < 80)
        low = sum(1 for d in decisions if 40 <= d.confidence < 60)
        very_low = sum(1 for d in decisions if d.confidence < 40)
        
        # Buscar feedbacks
        decision_ids = [d.id for d in decisions]
        feedbacks = self.db.query(FeedbackLog).filter(
            FeedbackLog.decision_id.in_(decision_ids)
        ).all() if decision_ids else []
        
        reviews_approved = sum(1 for f in feedbacks if f.feedback_type == "aprovado")
        reviews_corrected = sum(1 for f in feedbacks if f.feedback_type == "corrigido")
        reviews_rejected = sum(1 for f in feedbacks if f.feedback_type == "rejeitado")
        
        # Confiança média
        avg_confidence_all = sum(d.confidence for d in decisions) / total_decisions if total_decisions > 0 else 0.0
        
        approved_decisions = [d for d in decisions if any(f.decision_id == d.id and f.feedback_type == "aprovado" for f in feedbacks)]
        corrected_decisions = [d for d in decisions if any(f.decision_id == d.id and f.feedback_type == "corrigido" for f in feedbacks)]
        
        avg_confidence_approved = (
            sum(d.confidence for d in approved_decisions) / len(approved_decisions)
            if approved_decisions else 0.0
        )
        
        avg_confidence_corrected = (
            sum(d.confidence for d in corrected_decisions) / len(corrected_decisions)
            if corrected_decisions else 0.0
        )
        
        # Tempo médio
        avg_processing_time = (
            sum(d.processing_time_ms for d in decisions) / total_decisions
            if total_decisions > 0 else 0.0
        )
        
        # Tempo de revisão (da ReviewQueue)
        review_queue_entries = self.db.query(ReviewQueueModel).filter(
            and_(
                ReviewQueueModel.tenant_id == tenant_id,
                ReviewQueueModel.reviewed_at.isnot(None),
                ReviewQueueModel.created_at >= period_start,
                ReviewQueueModel.created_at <= period_end
            )
        ).all()
        
        if review_queue_entries:
            review_times = [
                (r.reviewed_at - r.created_at).total_seconds() / 60
                for r in review_queue_entries
            ]
            avg_review_time = sum(review_times) / len(review_times)
        else:
            avg_review_time = 0.0
        
        # Criar métricas
        return AIPerformanceMetrics(
            tenant_id=tenant_id,
            decision_type=decision_type,
            period=period,
            period_start=period_start,
            period_end=period_end,
            total_decisions=total_decisions,
            decisions_reviewed=decisions_reviewed,
            decisions_auto_executed=decisions_auto_executed,
            decisions_very_high=very_high,
            decisions_high=high,
            decisions_medium=medium,
            decisions_low=low,
            decisions_very_low=very_low,
            reviews_approved=reviews_approved,
            reviews_corrected=reviews_corrected,
            reviews_rejected=reviews_rejected,
            avg_confidence_all=round(avg_confidence_all, 2),
            avg_confidence_approved=round(avg_confidence_approved, 2),
            avg_confidence_corrected=round(avg_confidence_corrected, 2),
            avg_processing_time_ms=round(avg_processing_time, 2),
            avg_review_time_minutes=round(avg_review_time, 2)
        )
    
    def get_trends(
        self,
        tenant_id: int,
        decision_type: Optional[str] = None,
        metric_names: Optional[List[str]] = None
    ) -> List[MetricTrend]:
        """
        Calcula tendências comparando período atual vs anterior.
        
        Args:
            tenant_id: ID do tenant
            decision_type: Tipo de decisão
            metric_names: Métricas específicas (None = todas)
        
        Returns:
            Lista de MetricTrend
        """
        # Métricas padrão
        if metric_names is None:
            metric_names = [
                "approval_rate",
                "correction_rate",
                "rejection_rate",
                "automation_rate",
                "confidence_accuracy_gap",
                "review_pressure"
            ]
        
        # Buscar snapshots dos últimos 2 períodos
        snapshots = self.db.query(AIMetricsSnapshotModel).filter(
            and_(
                AIMetricsSnapshotModel.tenant_id == tenant_id,
                AIMetricsSnapshotModel.decision_type == decision_type,
                AIMetricsSnapshotModel.period == MetricPeriod.MONTHLY.value
            )
        ).order_by(
            AIMetricsSnapshotModel.period_start.desc()
        ).limit(2).all()
        
        if len(snapshots) < 2:
            logger.warning(f"Não há dados suficientes para calcular tendências")
            return []
        
        current = snapshots[0]
        previous = snapshots[1]
        
        trends = []
        for metric_name in metric_names:
            current_value = getattr(current, metric_name, 0.0)
            previous_value = getattr(previous, metric_name, 0.0)
            
            if previous_value == 0:
                change_percent = 0.0
            else:
                change_percent = ((current_value - previous_value) / previous_value) * 100
            
            # Determinar tendência
            if abs(change_percent) < 2:
                trend = "stable"
            elif change_percent > 0:
                trend = "improving" if metric_name in ["approval_rate", "automation_rate"] else "declining"
            else:
                trend = "declining" if metric_name in ["approval_rate", "automation_rate"] else "improving"
            
            trends.append(MetricTrend(
                metric_name=metric_name,
                current_value=round(current_value, 2),
                previous_value=round(previous_value, 2),
                change_percent=round(change_percent, 2),
                trend=trend
            ))
        
        return trends
    
    # ==================== WRITE (ATUALIZAÇÃO) ====================
    
    def update_metrics_from_event(self, event: DecisionReviewedEvent):
        """
        Atualiza snapshots incrementalmente quando DecisionReviewedEvent ocorre.
        
        Este é o handler do evento de revisão humana.
        Atualiza múltiplos snapshots (daily, weekly, monthly, all_time).
        
        Args:
            event: DecisionReviewedEvent recém-publicado
        """
        logger.info(f"📊 Atualizando métricas para decisão {event.decision_id}")
        
        # Buscar decisão original
        decision_log = self.db.query(DecisionLog).filter(
            DecisionLog.id == event.decision_log_id
        ).first()
        
        if not decision_log:
            logger.error(f"DecisionLog #{event.decision_log_id} não encontrado")
            return
        
        # Atualizar snapshots para todos os períodos
        for period in [MetricPeriod.DAILY, MetricPeriod.WEEKLY, MetricPeriod.MONTHLY, MetricPeriod.ALL_TIME]:
            self._update_snapshot_incremental(
                tenant_id=event.tenant_id,
                decision_type=event.decision_type,
                period=period,
                decision_log=decision_log,
                action_taken=event.action_taken,
                confidence_original=event.confidence_score_original
            )
        
        # Atualizar snapshot global (decision_type=None)
        for period in [MetricPeriod.DAILY, MetricPeriod.WEEKLY, MetricPeriod.MONTHLY, MetricPeriod.ALL_TIME]:
            self._update_snapshot_incremental(
                tenant_id=event.tenant_id,
                decision_type=None,  # Global
                period=period,
                decision_log=decision_log,
                action_taken=event.action_taken,
                confidence_original=event.confidence_score_original
            )
        
        self.db.commit()
        logger.info(f"✅ Métricas atualizadas para {event.decision_id}")
    
    def _update_snapshot_incremental(
        self,
        tenant_id: int,
        decision_type: Optional[str],
        period: MetricPeriod,
        decision_log: DecisionLog,
        action_taken: str,
        confidence_original: int
    ):
        """
        Atualiza ou cria snapshot incrementalmente.
        """
        period_start, period_end = self._get_period_dates(period)
        
        # Buscar ou criar snapshot
        snapshot = self.db.query(AIMetricsSnapshotModel).filter(
            and_(
                AIMetricsSnapshotModel.tenant_id == tenant_id,
                AIMetricsSnapshotModel.decision_type == decision_type,
                AIMetricsSnapshotModel.period == period.value,
                AIMetricsSnapshotModel.period_start == period_start
            )
        ).first()
        
        if not snapshot:
            # Criar novo snapshot
            snapshot = AIMetricsSnapshotModel(
                tenant_id=tenant_id,
                decision_type=decision_type,
                period=period.value,
                period_start=period_start,
                period_end=period_end
            )
            self.db.add(snapshot)
        
        # Atualizar contadores
        snapshot.decisions_reviewed += 1
        
        if action_taken == "aprovado":
            snapshot.reviews_approved += 1
        elif action_taken == "corrigido":
            snapshot.reviews_corrected += 1
        elif action_taken == "rejeitado":
            snapshot.reviews_rejected += 1
        
        # Recalcular métricas derivadas
        self._recalculate_derived_metrics(snapshot)
    
    def _recalculate_derived_metrics(self, snapshot: AIMetricsSnapshotModel):
        """Recalcula métricas derivadas de um snapshot."""
        if snapshot.decisions_reviewed > 0:
            snapshot.approval_rate = (snapshot.reviews_approved / snapshot.decisions_reviewed) * 100
            snapshot.correction_rate = (snapshot.reviews_corrected / snapshot.decisions_reviewed) * 100
            snapshot.rejection_rate = (snapshot.reviews_rejected / snapshot.decisions_reviewed) * 100
        
        if snapshot.total_decisions > 0:
            snapshot.automation_rate = (snapshot.decisions_auto_executed / snapshot.total_decisions) * 100
            snapshot.review_pressure = (snapshot.decisions_reviewed / snapshot.total_decisions) * 100
        
        snapshot.confidence_accuracy_gap = abs(snapshot.avg_confidence_all - snapshot.approval_rate)
    
    # ==================== HELPERS ====================
    
    def _get_period_dates(self, period: MetricPeriod) -> tuple[date, date]:
        """Calcula datas de início e fim do período."""
        today = date.today()
        
        if period == MetricPeriod.DAILY:
            return today, today
        
        elif period == MetricPeriod.WEEKLY:
            start = today - timedelta(days=today.weekday())  # Segunda
            end = start + timedelta(days=6)  # Domingo
            return start, end
        
        elif period == MetricPeriod.MONTHLY:
            start = today.replace(day=1)
            if today.month == 12:
                end = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(today.year, today.month + 1, 1) - timedelta(days=1)
            return start, end
        
        elif period == MetricPeriod.ALL_TIME:
            return date(2020, 1, 1), date(2030, 12, 31)  # Range amplo
        
        return today, today
    
    def _snapshot_to_domain(self, snapshot: AIMetricsSnapshotModel) -> AIPerformanceMetrics:
        """Converte AIMetricsSnapshotModel para AIPerformanceMetrics (domain)."""
        return AIPerformanceMetrics(
            tenant_id=snapshot.tenant_id,
            decision_type=snapshot.decision_type,
            period=MetricPeriod(snapshot.period),
            period_start=snapshot.period_start,
            period_end=snapshot.period_end,
            total_decisions=snapshot.total_decisions,
            decisions_reviewed=snapshot.decisions_reviewed,
            decisions_auto_executed=snapshot.decisions_auto_executed,
            decisions_very_high=snapshot.decisions_very_high,
            decisions_high=snapshot.decisions_high,
            decisions_medium=snapshot.decisions_medium,
            decisions_low=snapshot.decisions_low,
            decisions_very_low=snapshot.decisions_very_low,
            reviews_approved=snapshot.reviews_approved,
            reviews_corrected=snapshot.reviews_corrected,
            reviews_rejected=snapshot.reviews_rejected,
            avg_confidence_all=snapshot.avg_confidence_all,
            avg_confidence_approved=snapshot.avg_confidence_approved,
            avg_confidence_corrected=snapshot.avg_confidence_corrected,
            avg_processing_time_ms=snapshot.avg_processing_time_ms,
            avg_review_time_minutes=snapshot.avg_review_time_minutes,
            calculated_at=snapshot.calculated_at
        )
