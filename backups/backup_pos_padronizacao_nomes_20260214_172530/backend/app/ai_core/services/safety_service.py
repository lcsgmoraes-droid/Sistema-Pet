"""
AI Safety Service
=================

Monitora métricas de IA e dispara alertas quando guardrails violados.
Aciona circuit breakers automaticamente.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.ai_core.domain.guardrails import (
    AIGuardrails,
    GuardrailSeverity,
    SafetyViolation
)
from app.ai_core.domain.events import AIAlertEvent
from app.ai_core.domain.metrics import AIPerformanceMetrics
from app.ai_core.models.safety_log import AIGuardrailViolationLog
from app.ai_core.services.circuit_breaker import AICircuitBreaker
from app.ai_core.services.metrics_service import MetricsService


class SafetyService:
    """
    Serviço de segurança para governança de IA.
    
    Responsabilidades:
    1. Avaliar métricas contra guardrails
    2. Detectar violações (regressão, riscos)
    3. Publicar AIAlertEvent
    4. Acionar circuit breakers
    5. Registrar logs de segurança
    
    Chamado periodicamente (scheduler) ou após cada métrica atualizada.
    """
    
    def __init__(
        self,
        db: Session,
        metrics_service: MetricsService,
        guardrails: Optional[AIGuardrails] = None
    ):
        self.db = db
        self.metrics_service = metrics_service
        self.guardrails = guardrails or AIGuardrails()
    
    def evaluate_safety(
        self,
        tenant_id: int,
        decision_type: Optional[str] = None,
        period: str = "daily"
    ) -> List[AIAlertEvent]:
        """
        Avalia segurança das métricas atuais.
        
        Args:
            tenant_id: Tenant a avaliar
            decision_type: Tipo de decisão (None = todos)
            period: Período das métricas (daily, weekly, monthly)
        
        Returns:
            Lista de alertas gerados
        """
        # Buscar métricas atuais
        metrics = self.metrics_service.get_metrics(
            tenant_id=tenant_id,
            decision_type=decision_type,
            period=period
        )
        
        if not metrics:
            # Sem dados suficientes
            return []
        
        # Buscar métricas anteriores (para detectar quedas)
        previous_metrics = self.metrics_service.get_metrics(
            tenant_id=tenant_id,
            decision_type=decision_type,
            period=period,
            offset_periods=1  # Período anterior
        )
        
        previous_trust_score = None
        if previous_metrics:
            from app.ai_core.services.trust_service import TrustService
            trust_service = TrustService(self.db, self.metrics_service)
            prev_report = trust_service.generate_trust_report(
                tenant_id=tenant_id,
                decision_type=decision_type,
                period=period,
                metrics=previous_metrics
            )
            previous_trust_score = prev_report.trust_score
        
        # Converter métricas para dict
        metrics_dict = {
            'approval_rate': metrics.approval_rate,
            'rejection_rate': metrics.rejection_rate,
            'correction_rate': metrics.correction_rate,
            'automation_rate': metrics.automation_rate,
            'confidence_accuracy_gap': metrics.confidence_accuracy_gap,
            'review_pressure': metrics.review_pressure,
            'total_decisions': metrics.total_decisions
        }
        
        # Adicionar trust score
        from app.ai_core.services.trust_service import TrustService
        trust_service = TrustService(self.db, self.metrics_service)
        trust_report = trust_service.generate_trust_report(
            tenant_id=tenant_id,
            decision_type=decision_type,
            period=period,
            metrics=metrics
        )
        metrics_dict['trust_score'] = trust_report.trust_score
        
        # Avaliar contra guardrails
        violations = self.guardrails.evaluate_all(
            metrics=metrics_dict,
            previous_trust_score=previous_trust_score
        )
        
        if not violations:
            # Tudo OK, registrar sucesso no circuit breaker
            circuit = AICircuitBreaker(
                db=self.db,
                tenant_id=tenant_id,
                decision_type=decision_type
            )
            circuit.record_success()
            return []
        
        # Criar alertas para cada violação
        alerts = []
        circuit = AICircuitBreaker(
            db=self.db,
            tenant_id=tenant_id,
            decision_type=decision_type
        )
        
        for guardrail_type, severity in violations.items():
            alert = self._create_alert(
                tenant_id=tenant_id,
                decision_type=decision_type,
                guardrail_type=guardrail_type,
                severity=severity,
                metrics_dict=metrics_dict,
                previous_trust_score=previous_trust_score
            )
            
            alerts.append(alert)
            
            # Registrar no banco
            self._log_violation(alert)
            
            # Acionar circuit breaker
            new_state = circuit.record_violation(
                severity=GuardrailSeverity(severity),
                violation_event_id=alert.event_id,
                reason=alert.message
            )
            
            alert.circuit_breaker_triggered = (new_state.value == "open")
        
        return alerts
    
    def _create_alert(
        self,
        tenant_id: int,
        decision_type: Optional[str],
        guardrail_type: str,
        severity: GuardrailSeverity,
        metrics_dict: Dict[str, Any],
        previous_trust_score: Optional[float]
    ) -> AIAlertEvent:
        """
        Cria AIAlertEvent a partir de violação.
        """
        # Extrair valor atual e threshold
        if guardrail_type == "approval_rate_min":
            current_value = metrics_dict['approval_rate']
            threshold = self.guardrails.approval_rate_min
        elif guardrail_type == "rejection_rate_max":
            current_value = metrics_dict['rejection_rate']
            threshold = self.guardrails.rejection_rate_max
        elif guardrail_type == "trust_score_min":
            current_value = metrics_dict['trust_score']
            threshold = self.guardrails.trust_score_min
        elif guardrail_type == "trust_score_drop":
            current_value = previous_trust_score - metrics_dict['trust_score']
            threshold = self.guardrails.trust_score_drop
        elif guardrail_type == "calibration_gap_max":
            current_value = metrics_dict['confidence_accuracy_gap']
            threshold = self.guardrails.calibration_gap_max
        elif guardrail_type == "review_pressure_max":
            current_value = metrics_dict['review_pressure']
            threshold = self.guardrails.review_pressure_max
        elif guardrail_type == "correction_rate_max":
            current_value = metrics_dict['correction_rate']
            threshold = self.guardrails.correction_rate_max
        elif guardrail_type == "automation_rate_min":
            current_value = metrics_dict['automation_rate']
            threshold = self.guardrails.automation_rate_min
        elif guardrail_type == "sample_size_min":
            current_value = metrics_dict['total_decisions']
            threshold = self.guardrails.sample_size_min
        else:
            current_value = 0
            threshold = None
        
        # Threshold violado baseado em severidade
        if severity == GuardrailSeverity.WARNING:
            threshold_value = threshold.warning_threshold
        elif severity == GuardrailSeverity.CRITICAL:
            threshold_value = threshold.critical_threshold
        else:  # EMERGENCY
            threshold_value = threshold.emergency_threshold or threshold.critical_threshold
        
        # Ação recomendada
        if severity == GuardrailSeverity.EMERGENCY:
            recommended_action = "block_all"
        elif severity == GuardrailSeverity.CRITICAL:
            recommended_action = "force_review"
        else:
            recommended_action = "investigate"
        
        # Mensagem
        metric_name = guardrail_type.replace("_", " ").title()
        message = (
            f"{severity.value.upper()}: {metric_name}\n"
            f"Tenant: {tenant_id}\n"
            f"Módulo: {decision_type or 'TODOS'}\n"
            f"Valor atual: {current_value:.1f}\n"
            f"Limite: {threshold_value:.1f}"
        )
        
        return AIAlertEvent(
            event_id=f"alert_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
            severity=severity.value,
            tenant_id=tenant_id,
            decision_type=decision_type,
            guardrail_type=guardrail_type,
            current_value=current_value,
            threshold_violated=threshold_value,
            metrics_snapshot=metrics_dict,
            recommended_action=recommended_action,
            message=message,
            previous_trust_score=previous_trust_score
        )
    
    def _log_violation(self, alert: AIAlertEvent) -> None:
        """
        Registra violação no banco para auditoria.
        """
        log = AIGuardrailViolationLog(
            event_id=alert.event_id,
            severity=alert.severity,
            tenant_id=alert.tenant_id,
            decision_type=alert.decision_type,
            guardrail_type=alert.guardrail_type,
            current_value=alert.current_value,
            threshold_violated=alert.threshold_violated,
            metrics_snapshot=alert.metrics_snapshot,
            recommended_action=alert.recommended_action,
            message=alert.message,
            circuit_breaker_triggered=alert.circuit_breaker_triggered
        )
        
        self.db.add(log)
        self.db.commit()
    
    def get_active_alerts(
        self,
        tenant_id: int,
        decision_type: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[AIGuardrailViolationLog]:
        """
        Busca alertas ativos (não resolvidos).
        """
        query = self.db.query(AIGuardrailViolationLog).filter(
            AIGuardrailViolationLog.tenant_id == tenant_id,
            AIGuardrailViolationLog.resolved == False
        )
        
        if decision_type:
            query = query.filter(AIGuardrailViolationLog.decision_type == decision_type)
        
        if severity:
            query = query.filter(AIGuardrailViolationLog.severity == severity)
        
        return query.order_by(AIGuardrailViolationLog.created_at.desc()).all()
    
    def resolve_alert(
        self,
        alert_id: int,
        resolved_by: int,
        resolution_notes: str
    ) -> None:
        """
        Marca alerta como resolvido (ação administrativa).
        """
        alert = self.db.query(AIGuardrailViolationLog).filter(
            AIGuardrailViolationLog.id == alert_id
        ).first()
        
        if alert:
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            alert.resolved_by = resolved_by
            alert.resolution_notes = resolution_notes
            self.db.commit()
    
    def get_circuit_breaker(
        self,
        tenant_id: int,
        decision_type: Optional[str] = None
    ) -> AICircuitBreaker:
        """
        Retorna circuit breaker para tenant/módulo.
        """
        return AICircuitBreaker(
            db=self.db,
            tenant_id=tenant_id,
            decision_type=decision_type
        )
