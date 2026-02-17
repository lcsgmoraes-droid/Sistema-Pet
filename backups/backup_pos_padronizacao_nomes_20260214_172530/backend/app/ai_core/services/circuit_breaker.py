"""
AI Circuit Breaker
==================

Proteção automática contra regressão de IA.
Bloqueia automação quando guardrails são violados.

Pattern: Circuit Breaker (Hystrix-like)
- CLOSED: IA funcionando normalmente
- OPEN: IA bloqueada (force review)
- HALF_OPEN: IA em teste (permite algumas decisões)
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.ai_core.domain.guardrails import GuardrailSeverity
from app.ai_core.models.safety_log import AICircuitBreakerLog


class CircuitState(str, Enum):
    """Estados do circuit breaker"""
    CLOSED = "closed"        # Normal - IA funcionando
    OPEN = "open"            # Bloqueado - sem automação
    HALF_OPEN = "half_open"  # Teste - algumas decisões permitidas


class AICircuitBreaker:
    """
    Circuit Breaker para proteção de IA.
    
    Bloqueia automação automaticamente quando:
    - Guardrails CRITICAL violados
    - Guardrails EMERGENCY violados
    - Múltiplas violações WARNING em sequência
    
    Comportamento por severidade:
    - WARNING: Incrementa contador de falhas
    - CRITICAL: Abre circuit breaker imediatamente
    - EMERGENCY: Abre circuit breaker + marca tenant
    
    Auto-recuperação:
    - Após timeout, entra em HALF_OPEN
    - Se decisões OK em HALF_OPEN, fecha circuit
    - Se decisões ruins em HALF_OPEN, reabre circuit
    """
    
    def __init__(
        self,
        db: Session,
        tenant_id: int,
        decision_type: Optional[str] = None,
        failure_threshold: int = 3,           # Warnings antes de abrir
        half_open_timeout_minutes: int = 60,  # Tempo até tentar HALF_OPEN
        half_open_success_threshold: int = 5  # Sucessos para fechar
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.decision_type = decision_type
        self.failure_threshold = failure_threshold
        self.half_open_timeout = timedelta(minutes=half_open_timeout_minutes)
        self.half_open_success_threshold = half_open_success_threshold
        
        # Estado em memória (cache)
        self._state: Optional[CircuitState] = None
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_opened_at: Optional[datetime] = None
    
    def get_state(self) -> CircuitState:
        """
        Retorna estado atual do circuit breaker.
        
        Consulta banco se necessário e aplica lógica de timeout.
        """
        # Buscar último log do banco
        last_log = (
            self.db.query(AICircuitBreakerLog)
            .filter(
                AICircuitBreakerLog.tenant_id == self.tenant_id,
                AICircuitBreakerLog.decision_type == self.decision_type
            )
            .order_by(AICircuitBreakerLog.created_at.desc())
            .first()
        )
        
        if not last_log:
            return CircuitState.CLOSED
        
        state = CircuitState(last_log.state)
        
        # Se OPEN e timeout passou, mudar para HALF_OPEN
        if state == CircuitState.OPEN and last_log.opened_at:
            time_since_open = datetime.utcnow() - last_log.opened_at
            if time_since_open >= self.half_open_timeout:
                self._transition_to_half_open(last_log)
                return CircuitState.HALF_OPEN
        
        self._state = state
        return state
    
    def is_open(self) -> bool:
        """Circuit está aberto (bloqueando automação)?"""
        return self.get_state() == CircuitState.OPEN
    
    def is_half_open(self) -> bool:
        """Circuit está em teste?"""
        return self.get_state() == CircuitState.HALF_OPEN
    
    def should_block_automation(self) -> bool:
        """
        IA deve ser bloqueada?
        
        Returns:
            True se automação deve ser bloqueada (OPEN ou HALF_OPEN conservador)
        """
        state = self.get_state()
        
        if state == CircuitState.OPEN:
            return True
        
        if state == CircuitState.HALF_OPEN:
            # Em HALF_OPEN, bloqueia decisões de baixa/média confiança
            # Permite apenas VERY_HIGH
            return False  # DecisionPolicy vai ajustar thresholds
        
        return False
    
    def record_violation(
        self,
        severity: GuardrailSeverity,
        violation_event_id: str,
        reason: str
    ) -> CircuitState:
        """
        Registra violação de guardrail e atualiza estado.
        
        Args:
            severity: Severidade da violação
            violation_event_id: ID do AIAlertEvent
            reason: Descrição da violação
        
        Returns:
            Novo estado do circuit breaker
        """
        current_state = self.get_state()
        
        if severity == GuardrailSeverity.EMERGENCY:
            # EMERGENCY: Abre imediatamente
            return self._open_circuit(violation_event_id, reason, emergency=True)
        
        elif severity == GuardrailSeverity.CRITICAL:
            # CRITICAL: Abre imediatamente
            return self._open_circuit(violation_event_id, reason, emergency=False)
        
        elif severity == GuardrailSeverity.WARNING:
            # WARNING: Incrementa contador
            self._failure_count += 1
            
            if self._failure_count >= self.failure_threshold:
                # Muitas warnings: abre circuit
                return self._open_circuit(
                    violation_event_id,
                    f"Múltiplas violações WARNING ({self._failure_count})",
                    emergency=False
                )
        
        return current_state
    
    def record_success(self) -> CircuitState:
        """
        Registra decisão bem-sucedida.
        
        Em HALF_OPEN, sucessos podem fechar o circuit.
        """
        current_state = self.get_state()
        
        if current_state == CircuitState.HALF_OPEN:
            self._success_count += 1
            
            if self._success_count >= self.half_open_success_threshold:
                # Sucessos suficientes: fecha circuit
                return self._close_circuit("Decisões bem-sucedidas em HALF_OPEN")
        
        # Reset failure count em CLOSED
        if current_state == CircuitState.CLOSED:
            self._failure_count = 0
        
        return current_state
    
    def force_open(self, reason: str) -> CircuitState:
        """
        Força abertura manual do circuit (operação administrativa).
        """
        return self._open_circuit(None, f"Manual: {reason}", emergency=False)
    
    def force_close(self, reason: str) -> CircuitState:
        """
        Força fechamento manual do circuit (operação administrativa).
        """
        return self._close_circuit(f"Manual: {reason}")
    
    def _open_circuit(
        self,
        violation_event_id: Optional[str],
        reason: str,
        emergency: bool
    ) -> CircuitState:
        """
        Abre circuit breaker (bloqueia automação).
        """
        now = datetime.utcnow()
        
        log = AICircuitBreakerLog(
            tenant_id=self.tenant_id,
            decision_type=self.decision_type,
            state=CircuitState.OPEN.value,
            reason=reason,
            violation_event_ids=[violation_event_id] if violation_event_id else [],
            opened_at=now,
            previous_min_confidence=85,  # Threshold atual
            new_min_confidence=95 if not emergency else 100  # Aumenta threshold
        )
        
        self.db.add(log)
        self.db.commit()
        
        self._state = CircuitState.OPEN
        self._last_opened_at = now
        self._failure_count = 0
        self._success_count = 0
        
        return CircuitState.OPEN
    
    def _close_circuit(self, reason: str) -> CircuitState:
        """
        Fecha circuit breaker (restaura automação).
        """
        log = AICircuitBreakerLog(
            tenant_id=self.tenant_id,
            decision_type=self.decision_type,
            state=CircuitState.CLOSED.value,
            reason=reason,
            closed_at=datetime.utcnow(),
            new_min_confidence=85  # Restaura threshold normal
        )
        
        self.db.add(log)
        self.db.commit()
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        
        return CircuitState.CLOSED
    
    def _transition_to_half_open(self, last_log: AICircuitBreakerLog) -> None:
        """
        Transição de OPEN para HALF_OPEN (tentativa de recuperação).
        """
        log = AICircuitBreakerLog(
            tenant_id=self.tenant_id,
            decision_type=self.decision_type,
            state=CircuitState.HALF_OPEN.value,
            reason="Timeout atingido, testando recuperação",
            new_min_confidence=90  # Threshold conservador para teste
        )
        
        self.db.add(log)
        self.db.commit()
        
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
    
    def get_adjusted_min_confidence(self) -> int:
        """
        Retorna min_confidence ajustado baseado no estado do circuit.
        
        Returns:
            Threshold de confiança mínima para automação:
            - CLOSED: 85 (normal)
            - HALF_OPEN: 90 (conservador)
            - OPEN: 100 (bloqueado)
        """
        state = self.get_state()
        
        if state == CircuitState.CLOSED:
            return 85
        elif state == CircuitState.HALF_OPEN:
            return 90
        else:  # OPEN
            return 100  # Impossível atingir, bloqueia tudo
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status completo do circuit breaker.
        """
        state = self.get_state()
        
        return {
            "tenant_id": self.tenant_id,
            "decision_type": self.decision_type,
            "state": state.value,
            "is_blocking": self.should_block_automation(),
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "adjusted_min_confidence": self.get_adjusted_min_confidence(),
            "last_opened_at": self._last_opened_at.isoformat() if self._last_opened_at else None
        }
