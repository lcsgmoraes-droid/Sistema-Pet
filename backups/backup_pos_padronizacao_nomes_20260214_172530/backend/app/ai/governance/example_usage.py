"""
Example: AI Change Management & Approval Flow
Demonstração completa do framework de governança
"""
from uuid import uuid4
from datetime import datetime, timedelta

from app.ai.versioning.models import ComponentType, ComponentVersion, VersionStatus
from app.ai.versioning.registry import VersionRegistry
from app.ai.governance.models import (
    ChangeCategory,
    ChangeImpactLevel,
    RiskLevel,
    ApprovalRole,
    ApprovalDecision,
)
from app.ai.governance.change_management import ChangeManagementService
from app.ai.governance.approval_service import ApprovalService
from app.ai.governance.governed_promotion import GovernedVersionPromotion
from app.utils.logger import logger


# Mock Event Store
class InMemoryEventStore:
    def __init__(self):
        self.events = []
    
    def append(self, event):
        self.events.append(event)


def example_complete_change_flow():
    """
    Fluxo completo: Criar versão -> Change Request -> Aprovações -> Produção
    """
    
    # Setup
    event_store = InMemoryEventStore()
    version_registry = VersionRegistry(event_store)
    change_management = ChangeManagementService(event_store, version_registry)
    approval_service = ApprovalService(event_store, change_management)
    governed_promotion = GovernedVersionPromotion(
        version_registry,
        change_management,
        event_store,
    )
    
    print("=" * 80)
    logger.info("AI CHANGE MANAGEMENT & APPROVAL - FLUXO COMPLETO")
    print("=" * 80)
    
    # ========================================
    # STEP 1: Developer cria nova versão
    # ========================================
    logger.info("\n[STEP 1] Developer cria nova versão de IA...")
    
    version = version_registry.create_version(
        version_name="v3.0.0",
        version_tag="stable",
        components={
            ComponentType.ANALYZER: ComponentVersion(
                component_type=ComponentType.ANALYZER,
                version="2.0.0",
                config={"model": "gpt-4-turbo", "temperature": 0.15}
            ),
            ComponentType.CONFIDENCE_FORMULA: ComponentVersion(
                component_type=ComponentType.CONFIDENCE_FORMULA,
                version="3.0.0",
                config={"algorithm": "bayesian_v2"}
            ),
        },
        created_by="dev@petshop.com",
        description="Major upgrade with GPT-4 Turbo and Bayesian confidence",
        changelog="- Upgrade to GPT-4 Turbo\n- New Bayesian confidence algorithm",
    )
    
    logger.info(f"✓ Versão criada: {version.version_name}")
    logger.info(f"  Status: {version.status.value}")
    
    # Promover para TESTING
    version = version_registry.promote_version(
        version_id=version.id,
        to_status=VersionStatus.TESTING,
        promoted_by="dev@petshop.com",
    )
    logger.info(f"✓ Promovida para: {version.status.value}")
    
    # ========================================
    # STEP 2: Developer cria Change Request
    # ========================================
    logger.info("\n[STEP 2] Developer cria Change Request...")
    
    change_request = change_management.create_change_request(
        title="Upgrade to GPT-4 Turbo with Bayesian Confidence",
        description="""
        Major upgrade of AI decision engine:
        - GPT-4 Turbo for improved accuracy
        - New Bayesian confidence algorithm for better uncertainty quantification
        """,
        category=ChangeCategory.MODEL_UPGRADE,
        impact_level=ChangeImpactLevel.HIGH,
        behavior_version_id=version.id,
        business_justification="""
        Expected to improve decision accuracy by 5-8%, reducing fallback rate
        and increasing customer satisfaction.
        """,
        technical_justification="""
        GPT-4 Turbo provides better context understanding and lower latency.
        Bayesian confidence provides more accurate uncertainty estimates.
        """,
        expected_benefits=[
            "5-8% improvement in decision accuracy",
            "15% reduction in fallback rate",
            "20% faster response times",
            "Better uncertainty quantification",
        ],
        known_risks=[
            "New model behavior needs monitoring",
            "Cost increase of ~30% per decision",
            "Potential latency variance during peak hours",
        ],
        risk_level=RiskLevel.MEDIUM,
        mitigation_plan="""
        - Gradual rollout starting with 10% of tenants
        - Auto-rollback if success rate drops below 95%
        - Cost monitoring dashboard
        - Latency alerting
        """,
        rollback_plan="""
        - Immediate rollback to v2.4.0 if critical issues
        - Rollback SLA: < 5 minutes
        - No data loss, full auditability maintained
        """,
        requested_by="dev@petshop.com",
        affected_tenants=None,  # All tenants
    )
    
    logger.info(f"✓ Change Request criado: {change_request.title}")
    logger.info(f"  ID: {change_request.id}")
    logger.info(f"  Impact Level: {change_request.impact_level.value}")
    logger.info(f"  Risk Level: {change_request.risk_level.value}")
    
    # ========================================
    # STEP 3: Quality Gates Evaluation
    # ========================================
    logger.info("\n[STEP 3] Avaliando Quality Gates...")
    
    # Simular métricas de teste
    test_metrics = {
        "success_rate": 0.97,
        "avg_confidence": 0.82,
        "avg_trust_score": 0.84,
        "avg_latency_ms": 320.0,
        "latency_p95": 450.0,
    }
    
    quality_report = change_management.evaluate_quality_gates(
        change_request_id=change_request.id,
        test_metrics=test_metrics,
        test_decisions_count=500,
        evaluation_period_start=datetime.utcnow() - timedelta(days=3),
        evaluation_period_end=datetime.utcnow(),
    )
    
    logger.info(f"✓ Quality Gates avaliados:")
    logger.info(f"  Total gates: {len(quality_report.gates_evaluated)}")
    logger.info(f"  Passed: {quality_report.total_gates_passed}")
    logger.info(f"  Failed: {quality_report.total_gates_failed}")
    logger.info(f"  All mandatory passed: {quality_report.all_mandatory_gates_passed}")
    
    for gate_name, passed in quality_report.gates_passed.items():
        value = quality_report.gates_values[gate_name]
        status = "✓" if passed else "✗"
        logger.info(f"    {status} {gate_name}: {value}")
    
    # Marcar testing como completo
    change_request = change_management._change_requests[change_request.id]
    change_request = change_request.model_copy(update={"testing_completed": True})
    change_management._change_requests[change_request.id] = change_request
    
    # ========================================
    # STEP 4: Submeter para Review
    # ========================================
    logger.info("\n[STEP 4] Submetendo para revisão...")
    
    change_request = change_management.submit_for_review(
        change_request_id=change_request.id,
        submitted_by="dev@petshop.com",
    )
    
    logger.info(f"✓ Submetido para revisão")
    logger.info(f"  Status: {change_request.status.value}")
    
    # ========================================
    # STEP 5: Criar Approval Flow
    # ========================================
    logger.info("\n[STEP 5] Criando Approval Flow...")
    
    approval_flow = approval_service.create_approval_flow(
        change_request_id=change_request.id,
    )
    
    logger.info(f"✓ Approval Flow criado")
    logger.info(f"  Required roles: {[r.value for r in approval_flow.applicable_rule.required_roles]}")
    logger.info(f"  Min approvals: {approval_flow.applicable_rule.min_approvals}")
    logger.info(f"  Require all roles: {approval_flow.applicable_rule.require_all_roles}")
    
    # ========================================
    # STEP 6: Aprovações Multi-Role
    # ========================================
    logger.info("\n[STEP 6] Aprovações multi-role...")
    
    # TECH LEAD aprova
    logger.info("\n  [6.1] Tech Lead revisa...")
    approval_service.submit_approval(
        change_request_id=change_request.id,
        approver_id="tech.lead@petshop.com",
        approver_name="Alice Tech Lead",
        approver_role=ApprovalRole.TECH_LEAD,
        decision=ApprovalDecision.APPROVED,
        comments="Technical implementation looks solid. Quality gates passed.",
        review_notes="Reviewed code, architecture, and test results.",
        metrics_reviewed=test_metrics,
    )
    logger.info("    ✓ TECH_LEAD aprovado")
    
    # OPS LEAD aprova
    logger.info("\n  [6.2] Ops Lead revisa...")
    approval_service.submit_approval(
        change_request_id=change_request.id,
        approver_id="ops.lead@petshop.com",
        approver_name="Bob Ops Lead",
        approver_role=ApprovalRole.OPS_LEAD,
        decision=ApprovalDecision.APPROVED,
        comments="Rollout plan is good. Monitoring and rollback covered.",
        review_notes="Verified rollout strategy and observability setup.",
    )
    logger.info("    ✓ OPS_LEAD aprovado")
    
    # BUSINESS OWNER aprova
    logger.info("\n  [6.3] Business Owner revisa...")
    approval_service.submit_approval(
        change_request_id=change_request.id,
        approver_id="business@petshop.com",
        approver_name="Carol Business",
        approver_role=ApprovalRole.BUSINESS_OWNER,
        decision=ApprovalDecision.APPROVED_WITH_CONDITIONS,
        comments="Approved. Monitor cost impact closely in first week.",
        conditions=[
            "Daily cost report for first week",
            "Review after 1 week with stakeholders",
        ],
    )
    logger.info("    ✓ BUSINESS_OWNER aprovado (com condições)")
    
    # ========================================
    # STEP 7: Verificar Status de Aprovação
    # ========================================
    logger.info("\n[STEP 7] Status de aprovação...")
    
    status = approval_service.get_approval_status_summary(change_request.id)
    
    logger.info(f"✓ Approval Status:")
    logger.info(f"  Complete: {status['is_complete']}")
    logger.info(f"  Approved: {status['is_approved']}")
    logger.info(f"  Approvals received: {status['approved_count']}/{status['min_approvals']}")
    logger.info(f"  Change status: {status['change_status']}")
    
    # ========================================
    # STEP 8: Promover para Produção
    # ========================================
    logger.info("\n[STEP 8] Promovendo para produção...")
    
    # Verificar se pode promover
    can_promote, reason = governed_promotion.can_promote_to_production(version.id)
    
    if can_promote:
        version = governed_promotion.promote_to_production(
            version_id=version.id,
            change_request_id=change_request.id,
            promoted_by="ops.lead@petshop.com",
        )
        
        logger.info(f"✓ Versão promovida para PRODUÇÃO")
        logger.info(f"  Version: {version.version_name}")
        logger.info(f"  Status: {version.status.value}")
        logger.info(f"  Change Request: {change_request.id}")
    else:
        logger.info(f"✗ Não pode promover: {reason}")
    
    # ========================================
    # STEP 9: Histórico de Aprovações
    # ========================================
    logger.info("\n[STEP 9] Histórico de aprovações:")
    
    history = approval_service.get_approval_history(change_request.id)
    
    for approval in history:
        logger.info(f"\n  • {approval.approver_name} ({approval.approver_role.value})")
        logger.info(f"    Decision: {approval.decision.value}")
        logger.info(f"    Comments: {approval.comments}")
        if approval.conditions:
            logger.info(f"    Conditions: {approval.conditions}")
        logger.info(f"    Timestamp: {approval.approved_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ========================================
    # RESUMO
    # ========================================
    print("\n" + "=" * 80)
    logger.info("RESUMO DO FLUXO DE GOVERNANÇA")
    print("=" * 80)
    logger.info(f"✓ Versão: {version.version_name} ({version.status.value})")
    logger.info(f"✓ Change Request: {change_request.title}")
    logger.info(f"✓ Status: {change_request.status.value}")
    logger.info(f"✓ Quality Gates: {quality_report.all_mandatory_gates_passed}")
    logger.info(f"✓ Aprovações: {len(history)}/{approval_flow.applicable_rule.min_approvals}")
    logger.info(f"✓ Eventos emitidos: {len(event_store.events)}")
    
    logger.info("\nTipos de eventos:")
    event_types = {}
    for event in event_store.events:
        event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
    
    for event_type, count in sorted(event_types.items()):
        logger.info(f"  • {event_type}: {count}x")
    
    logger.info("\n✓ Framework de governança funcionando perfeitamente!")


def example_rejection_flow():
    """
    Exemplo de fluxo com rejeição
    """
    
    event_store = InMemoryEventStore()
    version_registry = VersionRegistry(event_store)
    change_management = ChangeManagementService(event_store, version_registry)
    approval_service = ApprovalService(event_store, change_management)
    
    print("\n" + "=" * 80)
    logger.info("EXEMPLO: FLUXO COM REJEIÇÃO")
    print("=" * 80)
    
    # Criar versão
    version = version_registry.create_version(
        version_name="v2.5.0-experimental",
        version_tag="experimental",
        components={
            ComponentType.ANALYZER: ComponentVersion(
                component_type=ComponentType.ANALYZER,
                version="1.5.0",
                config={"model": "experimental-model"}
            ),
        },
        created_by="dev@petshop.com",
        description="Experimental feature",
        changelog="Testing new approach",
    )
    
    version = version_registry.promote_version(
        version_id=version.id,
        to_status=VersionStatus.TESTING,
        promoted_by="dev@petshop.com",
    )
    
    # Change request
    change_request = change_management.create_change_request(
        title="Experimental AI Model",
        description="Testing new experimental model",
        category=ChangeCategory.FEATURE,
        impact_level=ChangeImpactLevel.HIGH,
        behavior_version_id=version.id,
        business_justification="Explore new approaches",
        technical_justification="Research and development",
        expected_benefits=["Learning"],
        known_risks=["Unproven technology", "High risk"],
        risk_level=RiskLevel.CRITICAL,
        mitigation_plan="Testing only",
        rollback_plan="Immediate rollback",
        requested_by="dev@petshop.com",
    )
    
    # Quality gates com métricas ruins
    quality_report = change_management.evaluate_quality_gates(
        change_request_id=change_request.id,
        test_metrics={
            "success_rate": 0.85,  # Abaixo do threshold!
            "avg_confidence": 0.60,  # Abaixo do threshold!
            "avg_latency_ms": 800.0,  # Acima do threshold!
            "latency_p95": 1200.0,
        },
        test_decisions_count=100,
        evaluation_period_start=datetime.utcnow() - timedelta(days=1),
        evaluation_period_end=datetime.utcnow(),
    )
    
    logger.info(f"✗ Quality Gates FAILED:")
    logger.info(f"  All mandatory passed: {quality_report.all_mandatory_gates_passed}")
    logger.info(f"  Failed: {quality_report.total_gates_failed}")
    
    # Tentar submeter (vai falhar)
    try:
        change_request = change_management.submit_for_review(
            change_request_id=change_request.id,
            submitted_by="dev@petshop.com",
        )
    except ValueError as e:
        logger.info(f"\n✗ Submission REJECTED: {e}")
    
    logger.info("\n✓ Governança bloqueou mudança de baixa qualidade!")


if __name__ == "__main__":
    example_complete_change_flow()
    example_rejection_flow()
    
    print("\n" + "=" * 80)
    logger.info("Todos os exemplos executados! ✓")
    print("=" * 80)
