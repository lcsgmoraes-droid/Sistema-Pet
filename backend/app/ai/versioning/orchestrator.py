"""
Rollout Orchestrator Service
Orquestra estratégias de rollout e monitora performance
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import UUID, uuid4
import random

from app.ai.versioning.models import (
    RolloutPlan,
    RolloutConfig,
    RolloutStrategy,
    RolloutStatus,
    VersionPerformanceSnapshot,
    VersionRegressionAlert,
)
from app.ai.versioning.events import (
    RolloutPlanCreated,
    RolloutStarted,
    RolloutStepCompleted,
    RolloutPaused,
    RolloutCompleted,
    RolloutFailed,
    VersionRegressionDetected,
    AutoRollbackTriggered,
)
from app.ai.versioning.registry import VersionRegistry


class RolloutOrchestrator:
    """
    Orquestra rollout de novas versões
    Responsabilidade: Executar estratégias de rollout com segurança
    """
    
    def __init__(
        self,
        version_registry: VersionRegistry,
        event_store,
    ):
        self.version_registry = version_registry
        self.event_store = event_store
        self._active_plans: Dict[UUID, RolloutPlan] = {}
        self._performance_snapshots: List[VersionPerformanceSnapshot] = []
    
    def create_rollout_plan(
        self,
        behavior_version_id: UUID,
        config: RolloutConfig,
        created_by: str,
    ) -> RolloutPlan:
        """Cria plano de rollout"""
        
        version = self.version_registry.get_version(behavior_version_id)
        if not version:
            raise ValueError(f"Version {behavior_version_id} not found")
        
        plan = RolloutPlan(
            behavior_version_id=behavior_version_id,
            config=config,
        )
        
        self._active_plans[plan.id] = plan
        
        # Emitir evento
        event = RolloutPlanCreated(
            event_id=uuid4(),
            aggregate_id=plan.id,
            behavior_version_id=behavior_version_id,
            strategy=config.strategy.value,
            created_by=created_by,
        )
        self.event_store.append(event)
        
        return plan
    
    def start_rollout(self, plan_id: UUID) -> RolloutPlan:
        """Inicia execução do rollout"""
        
        plan = self._active_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        if plan.status != RolloutStatus.PENDING:
            raise ValueError(f"Plan must be PENDING to start. Current: {plan.status}")
        
        # Determinar tenants iniciais baseado na estratégia
        initial_tenants = self._get_initial_tenants(plan)
        
        # Atualizar plano
        updated_plan = plan.model_copy(update={
            "status": RolloutStatus.IN_PROGRESS,
            "started_at": datetime.utcnow(),
            "current_step": 1,
            "current_tenant_ids": initial_tenants,
        })
        self._active_plans[plan_id] = updated_plan
        
        # Ativar versão nos tenants iniciais
        for tenant_id in initial_tenants:
            self.version_registry.assign_version_to_tenant(
                tenant_id=tenant_id,
                behavior_version_id=plan.behavior_version_id,
                activated_by="rollout_orchestrator",
            )
        
        # Emitir evento
        event = RolloutStarted(
            event_id=uuid4(),
            aggregate_id=plan_id,
            behavior_version_id=plan.behavior_version_id,
            strategy=plan.config.strategy.value,
            initial_tenant_ids=initial_tenants,
        )
        self.event_store.append(event)
        
        return updated_plan
    
    def _get_initial_tenants(self, plan: RolloutPlan) -> List[str]:
        """Determina tenants iniciais baseado na estratégia"""
        
        strategy = plan.config.strategy
        
        if strategy == RolloutStrategy.IMMEDIATE:
            # Todos os tenants (simulado - na prática, vem do DB)
            return self._get_all_tenant_ids()
        
        elif strategy == RolloutStrategy.CANARY:
            if plan.config.canary_tenant_ids:
                return plan.config.canary_tenant_ids
            else:
                # Selecionar percentual aleatório
                all_tenants = self._get_all_tenant_ids()
                count = max(1, int(len(all_tenants) * plan.config.canary_percentage))
                return random.sample(all_tenants, count)
        
        elif strategy == RolloutStrategy.GRADUAL:
            # Primeiro step do gradual
            all_tenants = self._get_all_tenant_ids()
            first_percentage = plan.config.gradual_steps[0]
            count = max(1, int(len(all_tenants) * first_percentage / 100))
            return random.sample(all_tenants, count)
        
        elif strategy == RolloutStrategy.TENANT_SPECIFIC:
            return plan.config.target_tenant_ids
        
        elif strategy == RolloutStrategy.BLUE_GREEN:
            # Blue-green começa vazio, espera decisão manual
            return []
        
        return []
    
    def _get_all_tenant_ids(self) -> List[str]:
        """Recupera todos os tenant IDs (mock)"""
        # Em produção, viria do banco
        return ["tenant_1", "tenant_2", "tenant_3", "tenant_4", "tenant_5"]
    
    def check_rollout_health(self, plan_id: UUID) -> Dict:
        """Verifica saúde do rollout e decide próximo passo"""
        
        plan = self._active_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        if plan.status != RolloutStatus.IN_PROGRESS:
            return {"status": plan.status.value, "action": "none"}
        
        # Coletar métricas dos tenants atuais
        metrics = self._collect_tenant_metrics(
            plan.current_tenant_ids,
            plan.behavior_version_id,
        )
        
        # Calcular agregados
        total_decisions = sum(m.decision_count for m in metrics)
        avg_success_rate = sum(m.success_rate for m in metrics) / len(metrics) if metrics else 0
        avg_fallback_rate = sum(m.fallback_rate for m in metrics) / len(metrics) if metrics else 0
        
        # Verificar condições de sucesso
        min_success = plan.config.min_success_rate
        max_fallback = plan.config.max_fallback_rate
        min_decisions = plan.config.min_decisions_before_proceed
        
        health = {
            "total_decisions": total_decisions,
            "avg_success_rate": avg_success_rate,
            "avg_fallback_rate": avg_fallback_rate,
            "meets_criteria": (
                total_decisions >= min_decisions
                and avg_success_rate >= min_success
                and avg_fallback_rate <= max_fallback
            ),
        }
        
        # Detectar regressão
        regressions = self._detect_regressions(metrics, plan)
        if regressions:
            health["regressions"] = [
                {
                    "tenant_id": r.tenant_id,
                    "metric": r.metric_name,
                    "severity": r.severity,
                }
                for r in regressions
            ]
            
            # Auto-rollback se habilitado
            if plan.config.auto_rollback_enabled:
                critical_regressions = [r for r in regressions if r.severity == "critical"]
                if critical_regressions:
                    self._trigger_auto_rollback(plan, regressions)
                    health["action"] = "auto_rollback_triggered"
                    return health
        
        # Decidir próxima ação
        if health["meets_criteria"]:
            if plan.config.strategy == RolloutStrategy.GRADUAL:
                # Avançar para próximo step
                if plan.current_step < len(plan.config.gradual_steps):
                    health["action"] = "proceed_next_step"
                else:
                    health["action"] = "complete_rollout"
            else:
                health["action"] = "complete_rollout"
        else:
            health["action"] = "wait"
        
        return health
    
    def _collect_tenant_metrics(
        self,
        tenant_ids: List[str],
        behavior_version_id: UUID,
    ) -> List[VersionPerformanceSnapshot]:
        """Coleta métricas de performance dos tenants"""
        
        snapshots = []
        
        for tenant_id in tenant_ids:
            assignment = self.version_registry.get_tenant_version(tenant_id)
            if not assignment or assignment.behavior_version_id != behavior_version_id:
                continue
            
            # Calcular métricas
            success_rate = (
                assignment.success_count / assignment.decision_count
                if assignment.decision_count > 0
                else 0.0
            )
            fallback_rate = (
                assignment.fallback_count / assignment.decision_count
                if assignment.decision_count > 0
                else 0.0
            )
            
            snapshot = VersionPerformanceSnapshot(
                tenant_id=tenant_id,
                behavior_version_id=behavior_version_id,
                decision_count=assignment.decision_count,
                success_rate=success_rate,
                fallback_rate=fallback_rate,
                avg_confidence=assignment.avg_confidence,
                avg_trust_score=assignment.avg_trust_score,
                avg_latency_ms=50.0,  # Mock
            )
            
            snapshots.append(snapshot)
            self._performance_snapshots.append(snapshot)
        
        return snapshots
    
    def _detect_regressions(
        self,
        snapshots: List[VersionPerformanceSnapshot],
        plan: RolloutPlan,
    ) -> List[VersionRegressionAlert]:
        """Detecta regressões de performance"""
        
        alerts = []
        
        for snapshot in snapshots:
            # Comparar com versão anterior se houver
            assignment = self.version_registry.get_tenant_version(snapshot.tenant_id)
            if not assignment or not assignment.previous_version_id:
                continue
            
            # Buscar baseline (versão anterior)
            baseline = self._get_baseline_snapshot(
                snapshot.tenant_id,
                assignment.previous_version_id,
            )
            if not baseline:
                continue
            
            # Verificar success_rate
            if baseline.success_rate > 0:
                delta = snapshot.success_rate - baseline.success_rate
                threshold = plan.config.auto_rollback_threshold
                
                if snapshot.success_rate < threshold:
                    alert = VersionRegressionAlert(
                        behavior_version_id=snapshot.behavior_version_id,
                        tenant_id=snapshot.tenant_id,
                        metric_name="success_rate",
                        current_value=snapshot.success_rate,
                        baseline_value=baseline.success_rate,
                        delta=delta,
                        threshold_violated=threshold,
                        severity="critical" if delta < -0.1 else "warning",
                        recommendation="rollback" if delta < -0.1 else "monitor",
                    )
                    alerts.append(alert)
                    
                    # Emitir evento
                    event = VersionRegressionDetected(
                        event_id=uuid4(),
                        aggregate_id=snapshot.behavior_version_id,
                        behavior_version_id=snapshot.behavior_version_id,
                        tenant_id=snapshot.tenant_id,
                        metric_name="success_rate",
                        current_value=snapshot.success_rate,
                        baseline_value=baseline.success_rate,
                        delta=delta,
                        severity=alert.severity,
                    )
                    self.event_store.append(event)
        
        return alerts
    
    def _get_baseline_snapshot(
        self,
        tenant_id: str,
        version_id: UUID,
    ) -> Optional[VersionPerformanceSnapshot]:
        """Recupera snapshot baseline de versão anterior"""
        for snapshot in reversed(self._performance_snapshots):
            if (
                snapshot.tenant_id == tenant_id
                and snapshot.behavior_version_id == version_id
            ):
                return snapshot
        return None
    
    def _trigger_auto_rollback(
        self,
        plan: RolloutPlan,
        regressions: List[VersionRegressionAlert],
    ):
        """Aciona rollback automático"""
        
        # Fazer rollback de todos os tenants afetados
        for tenant_id in plan.current_tenant_ids:
            try:
                self.version_registry.rollback_tenant_version(
                    tenant_id=tenant_id,
                    rolled_back_by="auto_rollback",
                    reason="Performance regression detected",
                )
            except Exception as e:
                # Log error mas continua
                pass
        
        # Atualizar plano
        updated_plan = plan.model_copy(update={
            "status": RolloutStatus.ROLLED_BACK,
            "should_proceed": False,
            "rollback_reason": f"Auto-rollback: {len(regressions)} regressions detected",
        })
        self._active_plans[plan.id] = updated_plan
        
        # Emitir evento
        event = AutoRollbackTriggered(
            event_id=uuid4(),
            aggregate_id=plan.id,
            behavior_version_id=plan.behavior_version_id,
            trigger_reason="performance_regression",
            trigger_metric="success_rate",
            trigger_value=regressions[0].current_value,
            affected_tenant_ids=plan.current_tenant_ids,
        )
        self.event_store.append(event)
    
    def proceed_next_step(self, plan_id: UUID) -> RolloutPlan:
        """Avança para próximo step do rollout"""
        
        plan = self._active_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        if plan.config.strategy != RolloutStrategy.GRADUAL:
            raise ValueError("proceed_next_step only for GRADUAL strategy")
        
        # Calcular próximos tenants
        next_step = plan.current_step + 1
        if next_step > len(plan.config.gradual_steps):
            return self.complete_rollout(plan_id)
        
        next_percentage = plan.config.gradual_steps[next_step - 1]
        all_tenants = self._get_all_tenant_ids()
        count = max(1, int(len(all_tenants) * next_percentage / 100))
        
        # Selecionar novos tenants (excluindo os já deployados)
        available = [t for t in all_tenants if t not in plan.current_tenant_ids]
        new_tenants = random.sample(available, min(count - len(plan.current_tenant_ids), len(available)))
        
        all_current = plan.current_tenant_ids + new_tenants
        
        # Ativar versão nos novos tenants
        for tenant_id in new_tenants:
            self.version_registry.assign_version_to_tenant(
                tenant_id=tenant_id,
                behavior_version_id=plan.behavior_version_id,
                activated_by="rollout_orchestrator",
            )
        
        # Atualizar plano
        updated_plan = plan.model_copy(update={
            "current_step": next_step,
            "current_tenant_ids": all_current,
        })
        self._active_plans[plan_id] = updated_plan
        
        # Emitir evento
        metrics = self._collect_tenant_metrics(new_tenants, plan.behavior_version_id)
        avg_success = sum(m.success_rate for m in metrics) / len(metrics) if metrics else 0
        avg_fallback = sum(m.fallback_rate for m in metrics) / len(metrics) if metrics else 0
        
        event = RolloutStepCompleted(
            event_id=uuid4(),
            aggregate_id=plan_id,
            step_number=next_step,
            tenant_ids=new_tenants,
            success_rate=avg_success,
            fallback_rate=avg_fallback,
        )
        self.event_store.append(event)
        
        return updated_plan
    
    def complete_rollout(self, plan_id: UUID) -> RolloutPlan:
        """Completa rollout com sucesso"""
        
        plan = self._active_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Atualizar plano
        updated_plan = plan.model_copy(update={
            "status": RolloutStatus.COMPLETED,
            "completed_at": datetime.utcnow(),
        })
        self._active_plans[plan_id] = updated_plan
        
        # Emitir evento
        event = RolloutCompleted(
            event_id=uuid4(),
            aggregate_id=plan_id,
            behavior_version_id=plan.behavior_version_id,
            total_tenants=len(plan.current_tenant_ids),
            total_decisions=plan.total_decisions,
            final_success_rate=0.98,  # Mock
        )
        self.event_store.append(event)
        
        return updated_plan
