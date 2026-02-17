"""
Example: AI Versioning Framework Usage
Demonstração completa do framework de versionamento
"""
from uuid import uuid4
from datetime import datetime

from app.ai.versioning.models import (
    ComponentType,
    ComponentVersion,
    RolloutConfig,
    RolloutStrategy,
    VersionStatus,
)
from app.ai.versioning.registry import VersionRegistry
from app.ai.versioning.orchestrator import RolloutOrchestrator
from app.ai.versioning.integration import VersionedDecisionService
from app.utils.logger import logger


# Mock Event Store
class InMemoryEventStore:
    def __init__(self):
        self.events = []
    
    def append(self, event):
        self.events.append(event)


def example_complete_workflow():
    """
    Exemplo completo: Criar versão -> Rollout Gradual -> Monitorar
    """
    
    # Setup
    event_store = InMemoryEventStore()
    registry = VersionRegistry(event_store)
    orchestrator = RolloutOrchestrator(registry, event_store)
    
    print("=" * 80)
    logger.info("AI VERSIONING & DEPLOYMENT - EXEMPLO COMPLETO")
    print("=" * 80)
    
    # ========================================
    # STEP 1: Criar nova versão
    # ========================================
    logger.info("\n[STEP 1] Criando nova versão de comportamento...")
    
    version = registry.create_version(
        version_name="v2.4.0",
        version_tag="stable",
        components={
            ComponentType.ANALYZER: ComponentVersion(
                component_type=ComponentType.ANALYZER,
                version="1.3.0",
                config={
                    "model": "gpt-4",
                    "temperature": 0.2,
                    "max_tokens": 500,
                }
            ),
            ComponentType.CONFIDENCE_FORMULA: ComponentVersion(
                component_type=ComponentType.CONFIDENCE_FORMULA,
                version="2.2.0",
                config={
                    "weights": {
                        "pattern_match": 0.4,
                        "context_relevance": 0.3,
                        "historical_success": 0.3,
                    }
                }
            ),
            ComponentType.GUARDRAIL: ComponentVersion(
                component_type=ComponentType.GUARDRAIL,
                version="1.4.0",
                config={
                    "min_confidence": 0.7,
                    "max_risk_score": 0.3,
                }
            ),
        },
        created_by="admin@petshop.com",
        description="Improved analyzer with GPT-4 and lower temperature",
        changelog="""
        - Upgraded model from GPT-3.5 to GPT-4
        - Reduced temperature from 0.3 to 0.2 for more consistent outputs
        - Updated confidence formula weights
        - Tightened guardrail thresholds
        """
    )
    
    logger.info(f"✓ Versão criada: {version.version_name}")
    logger.info(f"  ID: {version.id}")
    logger.info(f"  Status: {version.status.value}")
    logger.info(f"  Componentes: {list(version.components.keys())}")
    
    # ========================================
    # STEP 2: Promover para ACTIVE
    # ========================================
    logger.info("\n[STEP 2] Promovendo versão para ACTIVE...")
    
    # Em produção, passaria por TESTING primeiro
    version = registry.promote_version(
        version_id=version.id,
        to_status=VersionStatus.TESTING,
        promoted_by="admin@petshop.com"
    )
    logger.info(f"✓ Versão promovida para: {version.status.value}")
    
    # Depois de testes, promover para ACTIVE
    version = registry.promote_version(
        version_id=version.id,
        to_status=VersionStatus.ACTIVE,
        promoted_by="admin@petshop.com"
    )
    logger.info(f"✓ Versão promovida para: {version.status.value}")
    
    # ========================================
    # STEP 3: Criar plano de rollout GRADUAL
    # ========================================
    logger.info("\n[STEP 3] Criando plano de rollout gradual...")
    
    rollout_config = RolloutConfig(
        strategy=RolloutStrategy.GRADUAL,
        gradual_steps=[10, 25, 50, 100],  # 10% -> 25% -> 50% -> 100%
        gradual_step_duration_minutes=60,
        min_success_rate=0.95,
        max_fallback_rate=0.05,
        min_decisions_before_proceed=100,
        auto_rollback_enabled=True,
        auto_rollback_threshold=0.90,
    )
    
    plan = orchestrator.create_rollout_plan(
        behavior_version_id=version.id,
        config=rollout_config,
        created_by="admin@petshop.com"
    )
    
    logger.info(f"✓ Plano de rollout criado: {plan.id}")
    logger.info(f"  Estratégia: {plan.config.strategy.value}")
    logger.info(f"  Steps: {plan.config.gradual_steps}")
    logger.info(f"  Auto-rollback: {plan.config.auto_rollback_enabled}")
    
    # ========================================
    # STEP 4: Iniciar rollout
    # ========================================
    logger.info("\n[STEP 4] Iniciando rollout...")
    
    plan = orchestrator.start_rollout(plan.id)
    
    logger.info(f"✓ Rollout iniciado!")
    logger.info(f"  Status: {plan.status.value}")
    logger.info(f"  Step atual: {plan.current_step}")
    logger.info(f"  Tenants iniciais: {plan.current_tenant_ids}")
    
    # ========================================
    # STEP 5: Simular monitoramento
    # ========================================
    logger.info("\n[STEP 5] Monitorando rollout...")
    
    # Simular algumas decisões para gerar métricas
    for tenant_id in plan.current_tenant_ids:
        registry.update_tenant_metrics(
            tenant_id=tenant_id,
            decision_count=150,
            success_count=145,  # 96.7% success rate
            fallback_count=5,
            avg_confidence=0.89,
            avg_trust_score=0.87,
        )
    
    # Check health
    health = orchestrator.check_rollout_health(plan.id)
    
    logger.info(f"✓ Health check concluído:")
    logger.info(f"  Total decisões: {health['total_decisions']}")
    logger.info(f"  Success rate: {health['avg_success_rate']:.2%}")
    logger.info(f"  Fallback rate: {health['avg_fallback_rate']:.2%}")
    logger.info(f"  Meets criteria: {health['meets_criteria']}")
    logger.info(f"  Ação recomendada: {health['action']}")
    
    # ========================================
    # STEP 6: Avançar para próximo step
    # ========================================
    if health['action'] == 'proceed_next_step':
        logger.info("\n[STEP 6] Avançando para próximo step...")
        
        plan = orchestrator.proceed_next_step(plan.id)
        
        logger.info(f"✓ Avançado para step {plan.current_step}")
        logger.info(f"  Tenants atuais: {len(plan.current_tenant_ids)}")
        logger.info(f"  Target: {plan.config.gradual_steps[plan.current_step - 1]}%")
    
    # ========================================
    # STEP 7: Listar versões ativas
    # ========================================
    logger.info("\n[STEP 7] Versões ACTIVE no sistema:")
    
    active_versions = registry.list_versions(status=VersionStatus.ACTIVE)
    for v in active_versions:
        logger.info(f"  • {v.version_name} ({v.version_tag})")
        logger.info(f"    Criada em: {v.created_at.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"    Por: {v.created_by}")
    
    # ========================================
    # STEP 8: Exemplo de decisão com versão
    # ========================================
    logger.info("\n[STEP 8] Exemplo de decisão usando versão:")
    
    # Pegar um tenant que está usando a nova versão
    tenant_id = plan.current_tenant_ids[0]
    assignment = registry.get_tenant_version(tenant_id)
    
    if assignment:
        logger.info(f"  Tenant: {tenant_id}")
        logger.info(f"  Versão ativa: {version.version_name}")
        logger.info(f"  Ativada em: {assignment.activated_at.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"  Decisões: {assignment.decision_count}")
        logger.info(f"  Success rate: {assignment.success_count / assignment.decision_count:.2%}")
    
    # ========================================
    # RESUMO
    # ========================================
    print("\n" + "=" * 80)
    logger.info("RESUMO DO WORKFLOW")
    print("=" * 80)
    logger.info(f"✓ Versão criada: {version.version_name}")
    logger.info(f"✓ Estratégia: {plan.config.strategy.value}")
    logger.info(f"✓ Tenants em rollout: {len(plan.current_tenant_ids)}")
    logger.info(f"✓ Eventos emitidos: {len(event_store.events)}")
    logger.info("\nTipos de eventos:")
    for event in event_store.events:
        logger.info(f"  • {event.event_type}")
    
    logger.info("\n✓ Framework de versionamento funcionando corretamente!")


def example_canary_rollout():
    """
    Exemplo de rollout CANARY
    """
    
    event_store = InMemoryEventStore()
    registry = VersionRegistry(event_store)
    orchestrator = RolloutOrchestrator(registry, event_store)
    
    print("\n" + "=" * 80)
    logger.info("EXEMPLO: CANARY ROLLOUT")
    print("=" * 80)
    
    # Criar versão experimental
    version = registry.create_version(
        version_name="v2.5.0-canary",
        version_tag="canary",
        components={
            ComponentType.ANALYZER: ComponentVersion(
                component_type=ComponentType.ANALYZER,
                version="1.4.0-experimental",
                config={"model": "gpt-4-turbo", "temperature": 0.1}
            ),
        },
        created_by="dev@petshop.com",
        description="Experimental GPT-4 Turbo test",
        changelog="Testing new GPT-4 Turbo model"
    )
    
    registry.promote_version(version.id, VersionStatus.TESTING, "dev@petshop.com")
    registry.promote_version(version.id, VersionStatus.ACTIVE, "dev@petshop.com")
    
    # Rollout canary com tenants específicos
    plan = orchestrator.create_rollout_plan(
        behavior_version_id=version.id,
        config=RolloutConfig(
            strategy=RolloutStrategy.CANARY,
            canary_tenant_ids=["tenant_vip_1", "tenant_vip_2"],
            canary_percentage=0.05,
            min_success_rate=0.98,  # Mais rigoroso para canary
            auto_rollback_enabled=True,
        ),
        created_by="dev@petshop.com"
    )
    
    plan = orchestrator.start_rollout(plan.id)
    
    logger.info(f"✓ Canary iniciado em: {plan.current_tenant_ids}")
    logger.info(f"  Monitorando performance antes de expandir...")


def example_auto_rollback():
    """
    Exemplo de auto-rollback por regressão
    """
    
    event_store = InMemoryEventStore()
    registry = VersionRegistry(event_store)
    orchestrator = RolloutOrchestrator(registry, event_store)
    
    print("\n" + "=" * 80)
    logger.info("EXEMPLO: AUTO-ROLLBACK")
    print("=" * 80)
    
    # Criar versão com problema (simulado)
    version = registry.create_version(
        version_name="v2.6.0-broken",
        version_tag="testing",
        components={
            ComponentType.ANALYZER: ComponentVersion(
                component_type=ComponentType.ANALYZER,
                version="1.5.0",
                config={"model": "gpt-3.5", "temperature": 0.9}  # Muito alto!
            ),
        },
        created_by="dev@petshop.com",
        description="Version with high temperature (intentional bug for demo)",
        changelog="Testing auto-rollback"
    )
    
    registry.promote_version(version.id, VersionStatus.TESTING, "dev@petshop.com")
    registry.promote_version(version.id, VersionStatus.ACTIVE, "dev@petshop.com")
    
    plan = orchestrator.create_rollout_plan(
        behavior_version_id=version.id,
        config=RolloutConfig(
            strategy=RolloutStrategy.CANARY,
            canary_percentage=0.05,
            auto_rollback_enabled=True,
            auto_rollback_threshold=0.90,  # Rollback se < 90%
        ),
        created_by="dev@petshop.com"
    )
    
    plan = orchestrator.start_rollout(plan.id)
    
    # Simular performance ruim
    for tenant_id in plan.current_tenant_ids:
        registry.update_tenant_metrics(
            tenant_id=tenant_id,
            decision_count=100,
            success_count=85,  # 85% - abaixo do threshold!
            fallback_count=15,
            avg_confidence=0.65,  # Confiança baixa
            avg_trust_score=0.70,
        )
    
    # Check health vai detectar regressão
    health = orchestrator.check_rollout_health(plan.id)
    
    logger.info(f"✗ Performance detectada:")
    logger.info(f"  Success rate: {health['avg_success_rate']:.2%} (threshold: 90%)")
    
    if 'action' in health and health['action'] == 'auto_rollback_triggered':
        logger.info(f"\n✓ AUTO-ROLLBACK ACIONADO!")
        logger.info(f"  Tenants revertidos: {plan.current_tenant_ids}")
        logger.info(f"  Razão: {plan.rollback_reason}")
        
        # Verificar eventos
        rollback_events = [
            e for e in event_store.events
            if e.event_type == "rollout.auto_rollback_triggered"
        ]
        if rollback_events:
            logger.info(f"  Evento emitido: {rollback_events[-1].event_type}")


if __name__ == "__main__":
    # Executar exemplos
    example_complete_workflow()
    example_canary_rollout()
    example_auto_rollback()
    
    print("\n" + "=" * 80)
    logger.info("Todos os exemplos executados com sucesso! ✓")
    print("=" * 80)
