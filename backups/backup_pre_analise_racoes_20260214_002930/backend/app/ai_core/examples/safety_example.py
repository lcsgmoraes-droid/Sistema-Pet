"""
Exemplo: AI Guardrails & Safety Framework
==========================================

Demonstra sistema completo de proteção contra regressão de IA.
"""

from datetime import datetime
from sqlalchemy.orm import Session

from app.ai_core.services.metrics_service import MetricsService
from app.ai_core.services.trust_service import TrustService
from app.ai_core.services.safety_service import SafetyService
from app.ai_core.services.circuit_breaker import AICircuitBreaker
from app.ai_core.services.decision_policy import DecisionPolicy
from app.ai_core.domain.guardrails import AIGuardrails
from app.utils.logger import logger


class SafetyExample:
    """
    Exemplos de uso do framework de segurança.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.metrics_service = MetricsService(db)
        self.trust_service = TrustService(db, self.metrics_service)
        self.safety_service = SafetyService(db, self.metrics_service)
    
    def monitorar_seguranca_tenant(self, tenant_id: int):
        """
        CENÁRIO 1: Monitoramento contínuo de segurança.
        
        Chamado periodicamente (ex: a cada hora) para avaliar métricas.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"MONITORAMENTO DE SEGURANÇA - Tenant {tenant_id}")
        logger.info(f"{'='*60}\n")
        
        # Avaliar segurança (daily)
        alerts = self.safety_service.evaluate_safety(
            tenant_id=tenant_id,
            period="daily"
        )
        
        if not alerts:
            logger.info("✅ Tudo OK - Nenhuma violação detectada")
            return
        
        logger.info(f"🚨 {len(alerts)} ALERTA(S) DETECTADO(S)\n")
        
        for alert in alerts:
            logger.info(f"Severidade: {alert.severity.upper()}")
            logger.info(f"Guardrail: {alert.guardrail_type}")
            logger.info(f"Valor atual: {alert.current_value:.1f}")
            logger.info(f"Limite: {alert.threshold_violated:.1f}")
            logger.info(f"Ação recomendada: {alert.recommended_action}")
            logger.info(f"Circuit breaker: {'ACIONADO' if alert.circuit_breaker_triggered else 'OK'}")
            logger.info(f"\nMensagem:\n{alert.message}\n")
            print("-" * 60)
    
    def verificar_circuit_breaker(self, tenant_id: int, decision_type: str = None):
        """
        CENÁRIO 2: Verificar estado do circuit breaker.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"CIRCUIT BREAKER STATUS")
        logger.info(f"{'='*60}\n")
        
        circuit = self.safety_service.get_circuit_breaker(
            tenant_id=tenant_id,
            decision_type=decision_type
        )
        
        status = circuit.get_status()
        
        logger.info(f"Tenant: {status['tenant_id']}")
        logger.info(f"Módulo: {status['decision_type'] or 'TODOS'}")
        logger.info(f"Estado: {status['state'].upper()}")
        logger.info(f"Bloqueando automação: {'SIM' if status['is_blocking'] else 'NÃO'}")
        logger.info(f"Min confidence ajustado: {status['adjusted_min_confidence']}%")
        logger.info(f"Failure count: {status['failure_count']}")
        
        if status['last_opened_at']:
            logger.info(f"Último acionamento: {status['last_opened_at']}")
    
    def simular_regressao(self, tenant_id: int):
        """
        CENÁRIO 3: Simular regressão de IA e ver proteções acionando.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"SIMULAÇÃO: Regressão de IA detectada")
        logger.info(f"{'='*60}\n")
        
        # Métricas ruins (simuladas)
        bad_metrics = {
            'approval_rate': 42.0,        # < 50% (CRITICAL)
            'rejection_rate': 25.0,       # > 20% (CRITICAL)
            'trust_score': 35.0,          # < 40 (CRITICAL)
            'correction_rate': 35.0,
            'automation_rate': 15.0,
            'confidence_accuracy_gap': 28.0,  # > 25 (CRITICAL)
            'review_pressure': 75.0,
            'total_decisions': 120
        }
        
        guardrails = AIGuardrails()
        violations = guardrails.evaluate_all(bad_metrics)
        
        logger.info("Métricas RUINS detectadas:\n")
        logger.info(f"  • Approval rate: {bad_metrics['approval_rate']}%")
        logger.info(f"  • Rejection rate: {bad_metrics['rejection_rate']}%")
        logger.info(f"  • Trust score: {bad_metrics['trust_score']}/100")
        logger.info(f"  • Calibration gap: {bad_metrics['confidence_accuracy_gap']}")
        print()
        
        logger.info(f"🚨 {len(violations)} VIOLAÇÕES DETECTADAS:\n")
        
        for guardrail_type, severity in violations.items():
            logger.info(f"  [{severity.upper()}] {guardrail_type}")
        
        print()
        
        # Circuit breaker seria acionado
        max_severity = guardrails.get_max_severity(violations)
        logger.info(f"Severidade máxima: {max_severity.upper()}")
        
        if max_severity in ["critical", "emergency"]:
            logger.info("\n🔴 CIRCUIT BREAKER ACIONADO")
            logger.info("   → Automação BLOQUEADA")
            logger.info("   → Todas decisões vão para revisão")
            logger.info("   → Min confidence ajustado para 95-100%")
    
    def exemplo_decisao_com_circuit_aberto(self, tenant_id: int):
        """
        CENÁRIO 4: Decisão com circuit breaker aberto.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"DECISÃO COM CIRCUIT BREAKER ABERTO")
        logger.info(f"{'='*60}\n")
        
        # Criar policy com safety
        policy = DecisionPolicy(
            adaptive_mode=False,
            safety_service=self.safety_service
        )
        
        # Simular decisão de IA com alta confiança
        confidence = 92  # Normalmente seria EXECUTE
        
        logger.info(f"IA sugeriu decisão com {confidence}% confiança")
        logger.info("Normalmente: EXECUTE automaticamente\n")
        
        # Avaliar com circuit aberto (simulado)
        circuit = AICircuitBreaker(
            db=self.db,
            tenant_id=tenant_id,
            decision_type="categorizar_lancamento"
        )
        
        # Simular circuit aberto
        circuit.force_open("Simulação de regressão")
        
        # Avaliar policy
        decision = policy.evaluate(
            confidence_score=confidence,
            decision_type="categorizar_lancamento",
            context={"tenant_id": tenant_id},
            db_session=self.db
        )
        
        logger.info(f"🚨 Circuit Breaker STATUS: {circuit.get_state().value.upper()}")
        logger.info(f"\nAção determinada: {decision.action.value.upper()}")
        logger.info(f"Requer revisão: {'SIM' if decision.requires_human_review else 'NÃO'}")
        logger.info(f"Explicação: {decision.explanation}\n")
        
        if decision.suggested_next_steps:
            logger.info("Próximos passos:")
            for step in decision.suggested_next_steps:
                logger.info(f"  • {step}")
        
        # Fechar circuit
        circuit.force_close("Fim da simulação")
    
    def listar_alertas_ativos(self, tenant_id: int):
        """
        CENÁRIO 5: Listar alertas não resolvidos.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"ALERTAS ATIVOS - Tenant {tenant_id}")
        logger.info(f"{'='*60}\n")
        
        alertas = self.safety_service.get_active_alerts(tenant_id=tenant_id)
        
        if not alertas:
            logger.info("✅ Nenhum alerta ativo")
            return
        
        logger.info(f"📋 {len(alertas)} alerta(s) ativo(s):\n")
        
        for alert in alertas:
            logger.info(f"ID: {alert.id}")
            logger.info(f"Severidade: {alert.severity.upper()}")
            logger.info(f"Tipo: {alert.guardrail_type}")
            logger.info(f"Criado em: {alert.created_at}")
            logger.info(f"Circuit breaker: {'SIM' if alert.circuit_breaker_triggered else 'NÃO'}")
            logger.info(f"Mensagem: {alert.message[:100]}...")
            print("-" * 60)
    
    def exemplo_recuperacao_gradual(self, tenant_id: int):
        """
        CENÁRIO 6: Recuperação gradual após regressão.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"RECUPERAÇÃO GRADUAL (HALF-OPEN)")
        logger.info(f"{'='*60}\n")
        
        circuit = AICircuitBreaker(
            db=self.db,
            tenant_id=tenant_id,
            decision_type="categorizar_lancamento"
        )
        
        # Simular estados
        logger.info("Estado inicial: CLOSED (normal)")
        logger.info("↓")
        logger.info("Regressão detectada...")
        circuit.force_open("Métricas ruins")
        logger.info("Estado: OPEN (bloqueado)")
        logger.info("↓")
        logger.info("Aguardar 60 minutos...")
        logger.info("Estado: HALF_OPEN (teste)")
        print()
        
        logger.info("Em HALF_OPEN:")
        logger.info("  • Min confidence ajustado: 90%")
        logger.info("  • Decisões com conf < 90%: REQUIRE_REVIEW")
        logger.info("  • Decisões com conf ≥ 90%: EXECUTE (teste)")
        print()
        
        logger.info("Se 5 decisões OK:")
        logger.info("  → Estado: CLOSED")
        logger.info("  → Min confidence: 85% (normal)")
        logger.info("  → Automação restaurada")
        print()
        
        logger.info("Se decisões ruins:")
        logger.info("  → Estado: OPEN (novamente)")
        logger.info("  → Aguardar mais 60 min")
        
        # Limpar
        circuit.force_close("Fim da simulação")


def exemplo_completo_safety():
    """
    Exemplo completo do framework de segurança.
    """
    from app.db import SessionLocal
    
    db = SessionLocal()
    
    try:
        example = SafetyExample(db)
        
        # 1. Monitorar segurança
        example.monitorar_seguranca_tenant(tenant_id=1)
        
        # 2. Verificar circuit breaker
        example.verificar_circuit_breaker(tenant_id=1)
        
        # 3. Simular regressão
        example.simular_regressao(tenant_id=1)
        
        # 4. Decisão com circuit aberto
        example.exemplo_decisao_com_circuit_aberto(tenant_id=1)
        
        # 5. Listar alertas
        example.listar_alertas_ativos(tenant_id=1)
        
        # 6. Recuperação gradual
        example.exemplo_recuperacao_gradual(tenant_id=1)
        
    finally:
        db.close()


if __name__ == "__main__":
    exemplo_completo_safety()
