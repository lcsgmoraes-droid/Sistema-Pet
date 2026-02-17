"""
Decision Service Integration
Integra versionamento com DecisionService existente
"""
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from app.ai.versioning.registry import VersionRegistry
from app.ai.versioning.models import AIBehaviorVersion, ComponentType


class VersionedDecisionService:
    """
    Wrapper do DecisionService que adiciona controle de versão
    """
    
    def __init__(
        self,
        base_decision_service,
        version_registry: VersionRegistry,
    ):
        self.base_service = base_decision_service
        self.version_registry = version_registry
    
    def make_decision(
        self,
        tenant_id: str,
        context: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Toma decisão usando a versão ativa do tenant
        """
        
        # 1. Recuperar versão ativa do tenant
        assignment = self.version_registry.get_tenant_version(tenant_id)
        if not assignment:
            raise ValueError(f"No active version for tenant {tenant_id}")
        
        behavior_version = self.version_registry.get_version(
            assignment.behavior_version_id
        )
        if not behavior_version:
            raise ValueError(f"Version {assignment.behavior_version_id} not found")
        
        # 2. Configurar componentes baseado na versão
        self._configure_components(behavior_version)
        
        # 3. Executar decisão
        result = self.base_service.make_decision(
            tenant_id=tenant_id,
            context=context,
            user_id=user_id,
        )
        
        # 4. Adicionar metadados de versão
        result["_version_metadata"] = {
            "behavior_version_id": str(behavior_version.id),
            "behavior_version_name": behavior_version.version_name,
            "behavior_version_tag": behavior_version.version_tag,
            "component_versions": {
                ct.value: cv.version
                for ct, cv in behavior_version.components.items()
            },
            "decision_timestamp": datetime.utcnow().isoformat(),
        }
        
        # 5. Atualizar métricas do tenant
        is_success = result.get("action") != "fallback_to_human"
        is_fallback = result.get("action") == "fallback_to_human"
        
        # Incrementar contadores (simulado - em produção seria async)
        assignment.decision_count += 1
        if is_success:
            assignment.success_count += 1
        if is_fallback:
            assignment.fallback_count += 1
        
        # Atualizar médias (simplified)
        confidence = result.get("confidence_score", 0)
        trust_score = result.get("trust_score", 0)
        
        assignment.avg_confidence = (
            (assignment.avg_confidence * (assignment.decision_count - 1) + confidence)
            / assignment.decision_count
        )
        assignment.avg_trust_score = (
            (assignment.avg_trust_score * (assignment.decision_count - 1) + trust_score)
            / assignment.decision_count
        )
        
        return result
    
    def _configure_components(self, version: AIBehaviorVersion):
        """Configura componentes do DecisionService baseado na versão"""
        
        # Analyzer
        if ComponentType.ANALYZER in version.components:
            analyzer_config = version.components[ComponentType.ANALYZER].config
            self.base_service.analyzer.configure(analyzer_config)
        
        # Confidence Formula
        if ComponentType.CONFIDENCE_FORMULA in version.components:
            formula_config = version.components[ComponentType.CONFIDENCE_FORMULA].config
            self.base_service.confidence_calculator.configure(formula_config)
        
        # Policy
        if ComponentType.POLICY in version.components:
            policy_config = version.components[ComponentType.POLICY].config
            self.base_service.policy_engine.configure(policy_config)
        
        # Guardrail
        if ComponentType.GUARDRAIL in version.components:
            guardrail_config = version.components[ComponentType.GUARDRAIL].config
            self.base_service.guardrail.configure(guardrail_config)
        
        # Prompt Template
        if ComponentType.PROMPT_TEMPLATE in version.components:
            template_config = version.components[ComponentType.PROMPT_TEMPLATE].config
            self.base_service.prompt_builder.configure(template_config)


class VersionAwareAuditService:
    """
    Serviço de auditoria que registra versões em cada decisão
    """
    
    def __init__(self, base_audit_service, version_registry: VersionRegistry):
        self.base_audit = base_audit_service
        self.version_registry = version_registry
    
    def log_decision(
        self,
        tenant_id: str,
        decision_result: Dict[str, Any],
        context: Dict[str, Any],
    ):
        """Registra decisão com metadados de versão"""
        
        # Extrair metadados de versão
        version_metadata = decision_result.get("_version_metadata", {})
        
        # Adicionar ao log de auditoria
        audit_entry = {
            **context,
            "decision": decision_result,
            "version_metadata": version_metadata,
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.base_audit.log(audit_entry)
    
    def query_by_version(
        self,
        behavior_version_id: UUID,
        limit: int = 100,
    ) -> list:
        """Consulta decisões por versão"""
        
        # Query no audit log filtrando por version_id
        return self.base_audit.query({
            "version_metadata.behavior_version_id": str(behavior_version_id),
            "limit": limit,
        })
    
    def get_version_performance_stats(
        self,
        behavior_version_id: UUID,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calcula estatísticas de performance de uma versão"""
        
        decisions = self.query_by_version(behavior_version_id)
        
        if tenant_id:
            decisions = [d for d in decisions if d["tenant_id"] == tenant_id]
        
        if not decisions:
            return {
                "total_decisions": 0,
                "success_rate": 0.0,
                "avg_confidence": 0.0,
                "avg_trust_score": 0.0,
            }
        
        total = len(decisions)
        successes = sum(
            1 for d in decisions
            if d["decision"].get("action") != "fallback_to_human"
        )
        
        avg_confidence = sum(
            d["decision"].get("confidence_score", 0) for d in decisions
        ) / total
        
        avg_trust = sum(
            d["decision"].get("trust_score", 0) for d in decisions
        ) / total
        
        return {
            "total_decisions": total,
            "success_rate": successes / total,
            "avg_confidence": avg_confidence,
            "avg_trust_score": avg_trust,
        }
