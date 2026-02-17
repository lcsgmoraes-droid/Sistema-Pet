"""
AI Guardrails - Limites de Segurança
=====================================

Define limites mínimos e máximos para métricas de IA,
protegendo contra regressão e riscos operacionais.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GuardrailSeverity(str, Enum):
    """Severidade de violação de guardrail"""
    WARNING = "warning"      # Alerta, mas não bloqueia
    CRITICAL = "critical"    # Bloqueia automação
    EMERGENCY = "emergency"  # Bloqueia TODA IA


class GuardrailType(str, Enum):
    """Tipos de guardrails"""
    APPROVAL_RATE_MIN = "approval_rate_min"              # Taxa de aprovação mínima
    REJECTION_RATE_MAX = "rejection_rate_max"            # Taxa de rejeição máxima
    TRUST_SCORE_MIN = "trust_score_min"                  # Trust score mínimo
    TRUST_SCORE_DROP = "trust_score_drop"                # Queda abrupta de trust
    CALIBRATION_GAP_MAX = "calibration_gap_max"          # Gap de calibração máximo
    REVIEW_PRESSURE_MAX = "review_pressure_max"          # Pressão de revisão máxima
    CORRECTION_RATE_MAX = "correction_rate_max"          # Taxa de correção máxima
    AUTOMATION_RATE_MIN = "automation_rate_min"          # Automação mínima
    SAMPLE_SIZE_MIN = "sample_size_min"                  # Amostra mínima


@dataclass
class GuardrailThreshold:
    """
    Limites de um guardrail específico.
    
    Estrutura:
    - WARNING: Alerta operadores, mas não bloqueia
    - CRITICAL: Bloqueia automação, força revisão
    - EMERGENCY: Bloqueia TODA IA para esse tenant/módulo
    """
    type: GuardrailType
    warning_threshold: float
    critical_threshold: float
    emergency_threshold: Optional[float] = None
    
    def evaluate(self, value: float) -> Optional[GuardrailSeverity]:
        """
        Avalia se valor viola algum limite.
        
        Retorna severidade da violação ou None se OK.
        """
        if self.emergency_threshold is not None:
            if self._violates_emergency(value):
                return GuardrailSeverity.EMERGENCY
        
        if self._violates_critical(value):
            return GuardrailSeverity.CRITICAL
        
        if self._violates_warning(value):
            return GuardrailSeverity.WARNING
        
        return None
    
    def _violates_warning(self, value: float) -> bool:
        """Verifica violação de WARNING"""
        if "min" in self.type.value:
            return value < self.warning_threshold
        else:  # max
            return value > self.warning_threshold
    
    def _violates_critical(self, value: float) -> bool:
        """Verifica violação de CRITICAL"""
        if "min" in self.type.value:
            return value < self.critical_threshold
        else:  # max
            return value > self.critical_threshold
    
    def _violates_emergency(self, value: float) -> bool:
        """Verifica violação de EMERGENCY"""
        if self.emergency_threshold is None:
            return False
        
        if "min" in self.type.value:
            return value < self.emergency_threshold
        else:  # max
            return value > self.emergency_threshold


@dataclass
class AIGuardrails:
    """
    Conjunto completo de guardrails para governança de IA.
    
    Define limites seguros de operação baseados em métricas de performance.
    """
    
    # Taxa de aprovação mínima
    approval_rate_min: GuardrailThreshold = GuardrailThreshold(
        type=GuardrailType.APPROVAL_RATE_MIN,
        warning_threshold=70.0,    # < 70% = alerta
        critical_threshold=50.0,   # < 50% = bloqueia automação
        emergency_threshold=30.0   # < 30% = bloqueia tudo
    )
    
    # Taxa de rejeição máxima
    rejection_rate_max: GuardrailThreshold = GuardrailThreshold(
        type=GuardrailType.REJECTION_RATE_MAX,
        warning_threshold=10.0,    # > 10% = alerta
        critical_threshold=20.0,   # > 20% = bloqueia automação
        emergency_threshold=30.0   # > 30% = bloqueia tudo
    )
    
    # Trust score mínimo
    trust_score_min: GuardrailThreshold = GuardrailThreshold(
        type=GuardrailType.TRUST_SCORE_MIN,
        warning_threshold=60.0,    # < 60 = alerta
        critical_threshold=40.0,   # < 40 = bloqueia automação
        emergency_threshold=20.0   # < 20 = bloqueia tudo
    )
    
    # Queda abrupta de trust (pontos em relação ao período anterior)
    trust_score_drop: GuardrailThreshold = GuardrailThreshold(
        type=GuardrailType.TRUST_SCORE_DROP,
        warning_threshold=10.0,    # -10 pts = alerta
        critical_threshold=20.0,   # -20 pts = bloqueia automação
        emergency_threshold=30.0   # -30 pts = bloqueia tudo
    )
    
    # Gap de calibração máximo
    calibration_gap_max: GuardrailThreshold = GuardrailThreshold(
        type=GuardrailType.CALIBRATION_GAP_MAX,
        warning_threshold=15.0,    # > 15 = alerta
        critical_threshold=25.0,   # > 25 = bloqueia automação
        emergency_threshold=None   # Não bloqueia tudo
    )
    
    # Pressão de revisão máxima (% de decisões revisadas)
    review_pressure_max: GuardrailThreshold = GuardrailThreshold(
        type=GuardrailType.REVIEW_PRESSURE_MAX,
        warning_threshold=60.0,    # > 60% = alerta
        critical_threshold=80.0,   # > 80% = bloqueia automação
        emergency_threshold=None
    )
    
    # Taxa de correção máxima
    correction_rate_max: GuardrailThreshold = GuardrailThreshold(
        type=GuardrailType.CORRECTION_RATE_MAX,
        warning_threshold=20.0,    # > 20% = alerta
        critical_threshold=40.0,   # > 40% = bloqueia automação
        emergency_threshold=None
    )
    
    # Automação mínima (se muito baixa, IA não está agregando valor)
    automation_rate_min: GuardrailThreshold = GuardrailThreshold(
        type=GuardrailType.AUTOMATION_RATE_MIN,
        warning_threshold=30.0,    # < 30% = alerta
        critical_threshold=10.0,   # < 10% = revisar estratégia
        emergency_threshold=None
    )
    
    # Amostra mínima para decisões (evita alarmes falsos)
    sample_size_min: GuardrailThreshold = GuardrailThreshold(
        type=GuardrailType.SAMPLE_SIZE_MIN,
        warning_threshold=30.0,    # < 30 decisões = alerta
        critical_threshold=10.0,   # < 10 decisões = dados insuficientes
        emergency_threshold=None
    )
    
    def evaluate_all(self, metrics: dict, previous_trust_score: Optional[float] = None) -> dict:
        """
        Avalia todas as métricas contra guardrails.
        
        Args:
            metrics: Dicionário com métricas atuais
            previous_trust_score: Trust score do período anterior (para calcular queda)
        
        Returns:
            Dict com violações encontradas:
            {
                'approval_rate_min': GuardrailSeverity.CRITICAL,
                'rejection_rate_max': GuardrailSeverity.WARNING,
                ...
            }
        """
        violations = {}
        
        # Avaliar cada guardrail
        if 'approval_rate' in metrics:
            severity = self.approval_rate_min.evaluate(metrics['approval_rate'])
            if severity:
                violations['approval_rate_min'] = severity
        
        if 'rejection_rate' in metrics:
            severity = self.rejection_rate_max.evaluate(metrics['rejection_rate'])
            if severity:
                violations['rejection_rate_max'] = severity
        
        if 'trust_score' in metrics:
            severity = self.trust_score_min.evaluate(metrics['trust_score'])
            if severity:
                violations['trust_score_min'] = severity
            
            # Avaliar queda de trust score
            if previous_trust_score is not None:
                drop = previous_trust_score - metrics['trust_score']
                if drop > 0:  # Só avaliar se houve queda
                    severity = self.trust_score_drop.evaluate(drop)
                    if severity:
                        violations['trust_score_drop'] = severity
        
        if 'confidence_accuracy_gap' in metrics:
            severity = self.calibration_gap_max.evaluate(metrics['confidence_accuracy_gap'])
            if severity:
                violations['calibration_gap_max'] = severity
        
        if 'review_pressure' in metrics:
            severity = self.review_pressure_max.evaluate(metrics['review_pressure'])
            if severity:
                violations['review_pressure_max'] = severity
        
        if 'correction_rate' in metrics:
            severity = self.correction_rate_max.evaluate(metrics['correction_rate'])
            if severity:
                violations['correction_rate_max'] = severity
        
        if 'automation_rate' in metrics:
            severity = self.automation_rate_min.evaluate(metrics['automation_rate'])
            if severity:
                violations['automation_rate_min'] = severity
        
        if 'total_decisions' in metrics:
            severity = self.sample_size_min.evaluate(metrics['total_decisions'])
            if severity:
                violations['sample_size_min'] = severity
        
        return violations
    
    def get_max_severity(self, violations: dict) -> Optional[GuardrailSeverity]:
        """
        Retorna a severidade máxima entre todas as violações.
        """
        if not violations:
            return None
        
        severities = list(violations.values())
        
        if GuardrailSeverity.EMERGENCY in severities:
            return GuardrailSeverity.EMERGENCY
        elif GuardrailSeverity.CRITICAL in severities:
            return GuardrailSeverity.CRITICAL
        elif GuardrailSeverity.WARNING in severities:
            return GuardrailSeverity.WARNING
        
        return None


@dataclass
class SafetyViolation:
    """
    Registro de uma violação de guardrail detectada.
    """
    guardrail_type: GuardrailType
    severity: GuardrailSeverity
    current_value: float
    threshold_violated: float
    tenant_id: int
    decision_type: Optional[str]
    context: dict  # Métricas completas, timestamps, etc.
    
    def to_alert_message(self) -> str:
        """
        Gera mensagem de alerta legível.
        """
        metric_name = self.guardrail_type.value.replace("_", " ").title()
        
        return (
            f"🚨 {self.severity.value.upper()}: {metric_name}\n"
            f"Tenant: {self.tenant_id}\n"
            f"Módulo: {self.decision_type or 'TODOS'}\n"
            f"Valor atual: {self.current_value:.1f}\n"
            f"Limite: {self.threshold_violated:.1f}\n"
        )
