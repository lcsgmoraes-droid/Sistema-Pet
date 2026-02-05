"""
DecisionPolicy - Política global de decisão baseada em confiança.

Este é o ÚNICO lugar que define o que o sistema faz com base na confiança.
Todas as decisões de IA do AI CORE passam por esta política.

TABELA DE POLÍTICAS (0-100):

Confiança ≥ 90  → VERY_HIGH → Executar automaticamente
Confiança 80-89 → HIGH      → Executar + log de auditoria detalhado
Confiança 60-79 → MEDIUM    → Exigir revisão humana antes
Confiança 40-59 → LOW       → Apenas sugerir, não executar
Confiança < 40  → VERY_LOW  → Ignorar ou pedir mais dados

A IA NUNCA executa ações diretamente.
Ela retorna: decisão + confiança + explicação + evidências.
Esta policy decide o que fazer.
"""
from enum import Enum
from typing import Dict, Optional, List
from dataclasses import dataclass
from ..domain.types import ConfidenceLevel
import logging

logger = logging.getLogger(__name__)


class DecisionAction(str, Enum):
    """
    Ações que o sistema pode tomar com base na confiança.
    
    A IA retorna a decisão + confiança.
    A policy decide qual ação tomar.
    """
    EXECUTE = "execute"                  # Executar automaticamente
    EXECUTE_WITH_AUDIT = "execute_with_audit"  # Executar + auditoria detalhada
    REQUIRE_REVIEW = "require_review"    # Enviar para revisão humana
    SUGGEST_ONLY = "suggest_only"        # Apenas mostrar sugestão
    IGNORE = "ignore"                    # Ignorar ou pedir mais contexto
    REQUEST_MORE_DATA = "request_more_data"  # Pedir mais informações


@dataclass
class PolicyDecision:
    """
    Resultado da análise de política.
    
    Example:
        policy_decision = PolicyDecision(
            action=DecisionAction.EXECUTE_WITH_AUDIT,
            confidence_level=ConfidenceLevel.HIGH,
            requires_human_review=False,
            audit_level="detailed",
            explanation="Confiança alta (85%), executar com log detalhado"
        )
    """
    action: DecisionAction
    confidence_level: ConfidenceLevel
    requires_human_review: bool
    audit_level: str  # "none", "basic", "detailed", "full"
    explanation: str
    suggested_next_steps: Optional[List[str]] = None


class DecisionPolicy:
    """
    Aplica política global de confiança.
    
    Uso:
        policy = DecisionPolicy()
        
        policy_result = policy.evaluate(
            confidence_score=85,
            decision_type="categorizar_lancamento"
        )
        
        if policy_result.action == DecisionAction.EXECUTE_WITH_AUDIT:
            # Executar e logar
            await execute_decision(decision)
            await audit_log.save_detailed(decision)
        
        elif policy_result.action == DecisionAction.REQUIRE_REVIEW:
            # Enviar para fila de revisão
            await review_queue.enqueue(decision)
    """
    
    # Política global - ÚNICA FONTE DE VERDADE
    GLOBAL_POLICY = {
        ConfidenceLevel.VERY_HIGH: {
            "action": DecisionAction.EXECUTE,
            "requires_review": False,
            "audit_level": "basic",
            "explanation": "Confiança muito alta (≥90%), executar automaticamente"
        },
        ConfidenceLevel.HIGH: {
            "action": DecisionAction.EXECUTE_WITH_AUDIT,
            "requires_review": False,
            "audit_level": "detailed",
            "explanation": "Confiança alta (80-89%), executar com auditoria detalhada"
        },
        ConfidenceLevel.MEDIUM: {
            "action": DecisionAction.REQUIRE_REVIEW,
            "requires_review": True,
            "audit_level": "full",
            "explanation": "Confiança média (60-79%), exige revisão humana"
        },
        ConfidenceLevel.LOW: {
            "action": DecisionAction.SUGGEST_ONLY,
            "requires_review": True,
            "audit_level": "basic",
            "explanation": "Confiança baixa (40-59%), apenas sugerir"
        },
        ConfidenceLevel.VERY_LOW: {
            "action": DecisionAction.IGNORE,
            "requires_review": False,
            "audit_level": "basic",
            "explanation": "Confiança muito baixa (<40%), ignorar ou pedir mais dados"
        }
    }
    
    # Exceções por tipo de decisão (sobrescreve política global)
    DECISION_TYPE_OVERRIDES = {
        "categorizar_lancamento": {
            # Financeiro é crítico, exigir revisão em MEDIUM
            ConfidenceLevel.MEDIUM: {
                "action": DecisionAction.REQUIRE_REVIEW,
                "requires_review": True,
                "audit_level": "full",
                "explanation": "Categorização financeira: revisão obrigatória em confiança média"
            }
        },
        "detectar_intencao": {
            # Chat pode executar com confiança menor
            ConfidenceLevel.MEDIUM: {
                "action": DecisionAction.EXECUTE_WITH_AUDIT,
                "requires_review": False,
                "audit_level": "detailed",
                "explanation": "Chat: confiança média suficiente para responder"
            }
        },
        # Adicionar outros tipos conforme necessário
    }
    
    def __init__(
        self,
        custom_policy: Optional[Dict] = None,
        strict_mode: bool = False,
        adaptive_mode: bool = False,
        metrics_service=None,
        trust_service=None,
        safety_service=None
    ):
        """
        Inicializa política.
        
        Args:
            custom_policy: Política customizada (sobrescreve global)
            strict_mode: Se True, exige revisão em HIGH também
            adaptive_mode: Se True, ajusta thresholds baseado em métricas
            metrics_service: MetricsService para políticas adaptativas
            trust_service: TrustService para recomendações
            safety_service: SafetyService para circuit breakers
        """
        self.custom_policy = custom_policy
        self.strict_mode = strict_mode
        self.adaptive_mode = adaptive_mode
        self.metrics_service = metrics_service
        self.trust_service = trust_service
        self.safety_service = safety_service
        
        # Cache de thresholds adaptativos (por tenant)
        self._adaptive_thresholds = {}
    
    def evaluate(
        self,
        confidence_score: int,
        decision_type: str,
        context: Optional[Dict] = None,
        db_session=None
    ) -> PolicyDecision:
        """
        Avalia qual ação tomar baseado na confiança.
        
        Integrado com Circuit Breaker: Se circuit aberto, força revisão.
        Se adaptive_mode=True, ajusta thresholds baseado em métricas históricas.
        
        Args:
            confidence_score: Score de confiança (0-100)
            decision_type: Tipo de decisão (ex: "categorizar_lancamento")
            context: Contexto adicional (deve conter tenant_id)
            db_session: Sessão do banco (para circuit breaker)
        
        Returns:
            PolicyDecision com ação recomendada
        """
        tenant_id = context.get("tenant_id") if context else None
        
        # 🚨 CIRCUIT BREAKER CHECK (prioridade máxima)
        if self.safety_service and db_session and tenant_id:
            circuit = self.safety_service.get_circuit_breaker(
                tenant_id=tenant_id,
                decision_type=decision_type
            )
            
            if circuit.should_block_automation():
                # Circuit aberto: FORÇAR REVISÃO independente da confiança
                return PolicyDecision(
                    action=DecisionAction.REQUIRE_REVIEW,
                    confidence_level=ConfidenceLevel.from_score(confidence_score),
                    requires_human_review=True,
                    audit_level="full",
                    explanation=f"🚨 Circuit Breaker ATIVO: Automação bloqueada por segurança (estado: {circuit.get_state().value})",
                    suggested_next_steps=[
                        "Revisar métricas de performance",
                        "Verificar alertas de segurança",
                        "Aprovar manualmente se decisão estiver correta"
                    ]
                )
            
            # Circuit em half-open: ajustar min_confidence
            if circuit.is_half_open():
                adjusted_min = circuit.get_adjusted_min_confidence()
                if confidence_score < adjusted_min:
                    return PolicyDecision(
                        action=DecisionAction.REQUIRE_REVIEW,
                        confidence_level=ConfidenceLevel.from_score(confidence_score),
                        requires_human_review=True,
                        audit_level="detailed",
                        explanation=f"Circuit Breaker em recuperação: Confiança {confidence_score}% < {adjusted_min}% (threshold ajustado)",
                        suggested_next_steps=["Revisar decisão manualmente"]
                    )
        
        # Modo adaptativo: ajustar thresholds baseado em performance
        if self.adaptive_mode and tenant_id:
            confidence_score = self._apply_adaptive_adjustment(
                confidence_score,
                tenant_id,
                decision_type
            )
        
        # Converter score em nível
        confidence_level = ConfidenceLevel.from_score(confidence_score)
        
        # Buscar política aplicável
        policy_rule = self._get_policy_rule(confidence_level, decision_type)
        
        # Aplicar strict mode se ativado
        if self.strict_mode and confidence_level == ConfidenceLevel.MEDIUM:
            policy_rule["requires_review"] = True
            policy_rule["action"] = DecisionAction.REQUIRE_REVIEW
        
        # Construir decisão de política
        decision = PolicyDecision(
            action=policy_rule["action"],
            confidence_level=confidence_level,
            requires_human_review=policy_rule["requires_review"],
            audit_level=policy_rule["audit_level"],
            explanation=policy_rule["explanation"],
            suggested_next_steps=self._get_suggested_next_steps(
                policy_rule["action"],
                decision_type
            )
        )
        
        logger.info(
            f"📋 Política aplicada: {confidence_level.value} ({confidence_score}%) → "
            f"{decision.action.value} | Revisão: {decision.requires_human_review}"
        )
        
        return decision
    
    def _get_policy_rule(
        self,
        confidence_level: ConfidenceLevel,
        decision_type: str
    ) -> Dict:
        """
        Busca regra de política aplicável.
        
        Ordem de precedência:
        1. Custom policy (se fornecida)
        2. Override por tipo de decisão
        3. Política global
        """
        # 1. Custom policy
        if self.custom_policy and confidence_level in self.custom_policy:
            return self.custom_policy[confidence_level]
        
        # 2. Override por tipo
        if decision_type in self.DECISION_TYPE_OVERRIDES:
            overrides = self.DECISION_TYPE_OVERRIDES[decision_type]
            if confidence_level in overrides:
                return overrides[confidence_level]
        
        # 3. Política global
        return self.GLOBAL_POLICY[confidence_level]
    
    def _get_suggested_next_steps(
        self,
        action: DecisionAction,
        decision_type: str
    ) -> List[str]:
        """
        Sugere próximos passos baseado na ação.
        
        Args:
            action: Ação recomendada
            decision_type: Tipo de decisão
        
        Returns:
            Lista de próximos passos sugeridos
        """
        steps_map = {
            DecisionAction.EXECUTE: [
                "Aplicar decisão automaticamente",
                "Logar em audit trail básico",
                "Notificar usuário (se configurado)"
            ],
            DecisionAction.EXECUTE_WITH_AUDIT: [
                "Aplicar decisão automaticamente",
                "Salvar log detalhado com evidências",
                "Adicionar flag para revisão posterior",
                "Atualizar métricas de acurácia"
            ],
            DecisionAction.REQUIRE_REVIEW: [
                "Enviar para fila de revisão humana",
                "Notificar usuário para validar",
                "Salvar como 'pendente' no sistema",
                "Não aplicar até aprovação"
            ],
            DecisionAction.SUGGEST_ONLY: [
                "Mostrar como sugestão na UI",
                "Não aplicar automaticamente",
                "Capturar feedback se aplicado manualmente"
            ],
            DecisionAction.IGNORE: [
                "Não aplicar decisão",
                "Solicitar mais contexto ao usuário",
                "Logar tentativa como 'insuficiente'"
            ],
            DecisionAction.REQUEST_MORE_DATA: [
                "Solicitar informações adicionais",
                "Tentar novamente com mais contexto"
            ]
        }
        
        return steps_map.get(action, [])
    
    # ==================== MODO ADAPTATIVO ====================
    
    def _apply_adaptive_adjustment(
        self,
        confidence_score: int,
        tenant_id: int,
        decision_type: str
    ) -> int:
        """
        Ajusta confidence_score baseado em performance histórica.
        
        Se IA tem histórico de alta precisão → pode relaxar thresholds
        Se IA tem histórico de baixa precisão → deve ser mais conservadora
        
        Returns:
            confidence_score ajustado
        """
        # Buscar ou calcular thresholds adaptativos
        cache_key = f"{tenant_id}_{decision_type}"
        
        if cache_key not in self._adaptive_thresholds:
            self._calculate_adaptive_thresholds(tenant_id, decision_type)
        
        adjustment = self._adaptive_thresholds.get(cache_key, {}).get("confidence_adjustment", 0)
        
        adjusted_score = confidence_score + adjustment
        adjusted_score = max(0, min(100, adjusted_score))  # Clamp 0-100
        
        if adjustment != 0:
            logger.info(
                f"🔧 Ajuste adaptativo: {confidence_score} → {adjusted_score} "
                f"(tenant:{tenant_id}, tipo:{decision_type})"
            )
        
        return adjusted_score
    
    def _calculate_adaptive_thresholds(self, tenant_id: int, decision_type: str):
        """
        Calcula ajustes adaptativos baseados em TrustReport.
        
        Estratégia:
        - approval_rate > 90% → +5 pontos (pode ser mais agressivo)
        - approval_rate 75-90% → 0 pontos (neutro)
        - approval_rate 50-75% → -5 pontos (mais conservador)
        - approval_rate < 50% → -10 pontos (muito conservador)
        """
        if not self.trust_service or not self.metrics_service:
            logger.warning("Modo adaptativo sem trust_service configurado")
            return
        
        try:
            from ..domain.metrics import MetricPeriod
            
            # Gerar trust report
            report = self.trust_service.generate_trust_report(
                tenant_id=tenant_id,
                decision_type=decision_type,
                period=MetricPeriod.MONTHLY
            )
            
            # Calcular ajuste baseado em approval_rate
            approval = report.metrics.approval_rate
            
            if approval >= 90:
                adjustment = 5  # IA muito boa, pode aumentar automação
            elif approval >= 75:
                adjustment = 0  # IA confiável, manter
            elif approval >= 50:
                adjustment = -5  # IA precisa melhorar, mais conservador
            else:
                adjustment = -10  # IA ruim, muito conservador
            
            # Ajuste adicional baseado em calibração
            if report.metrics.confidence_accuracy_gap > 20:
                adjustment -= 5  # IA mal calibrada, ser mais conservador
            
            cache_key = f"{tenant_id}_{decision_type}"
            self._adaptive_thresholds[cache_key] = {
                "confidence_adjustment": adjustment,
                "maturity_level": report.maturity_level.value,
                "approval_rate": approval,
                "calculated_at": report.generated_at
            }
            
            logger.info(
                f"📊 Thresholds adaptativos calculados | "
                f"Tenant: {tenant_id} | "
                f"Type: {decision_type} | "
                f"Ajuste: {adjustment:+d} | "
                f"Maturidade: {report.maturity_level.value}"
            )
        
        except Exception as e:
            logger.error(f"Erro ao calcular thresholds adaptativos: {e}")
            # Fallback para valores padrão
            cache_key = f"{tenant_id}_{decision_type}"
            self._adaptive_thresholds[cache_key] = {"confidence_adjustment": 0}
    
    def refresh_adaptive_thresholds(self, tenant_id: int, decision_type: Optional[str] = None):
        """
        Força recálculo de thresholds adaptativos.
        
        Deve ser chamado periodicamente (ex: diariamente) ou após
        mudanças significativas nas métricas.
        """
        if decision_type:
            cache_key = f"{tenant_id}_{decision_type}"
            if cache_key in self._adaptive_thresholds:
                del self._adaptive_thresholds[cache_key]
            self._calculate_adaptive_thresholds(tenant_id, decision_type)
        else:
            # Refresh para todos os tipos deste tenant
            keys_to_refresh = [
                k for k in self._adaptive_thresholds.keys()
                if k.startswith(f"{tenant_id}_")
            ]
            for key in keys_to_refresh:
                del self._adaptive_thresholds[key]
            
            logger.info(f"🔄 Thresholds adaptativos resetados para tenant {tenant_id}")
    
    def get_adaptive_status(self, tenant_id: int, decision_type: str) -> Dict:
        """
        Retorna status dos thresholds adaptativos para um tenant/tipo.
        """
        cache_key = f"{tenant_id}_{decision_type}"
        return self._adaptive_thresholds.get(cache_key, {
            "confidence_adjustment": 0,
            "status": "not_calculated"
        })
    
    # ==================== HELPERS ====================
    
    @staticmethod
    def can_execute_automatically(confidence_score: int) -> bool:
        """
        Verifica se pode executar automaticamente.
        
        Args:
            confidence_score: Score de confiança (0-100)
        
        Returns:
            True se pode executar sem revisão humana
        
        Example:
            if DecisionPolicy.can_execute_automatically(result.confidence_score):
                await apply_decision(result.decision)
        """
        confidence_level = ConfidenceLevel.from_score(confidence_score)
        return confidence_level in [
            ConfidenceLevel.VERY_HIGH,
            ConfidenceLevel.HIGH
        ]
    
    @staticmethod
    def requires_human_review(confidence_score: int) -> bool:
        """
        Verifica se exige revisão humana.
        
        Args:
            confidence_score: Score de confiança (0-100)
        
        Returns:
            True se exige revisão antes de executar
        
        Example:
            if DecisionPolicy.requires_human_review(result.confidence_score):
                await send_to_review_queue(result)
        """
        confidence_level = ConfidenceLevel.from_score(confidence_score)
        return confidence_level in [
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW
        ]
    
    def get_policy_summary(self) -> str:
        """
        Retorna resumo da política em texto.
        
        Returns:
            Texto formatado com resumo da política
        """
        summary = []
        summary.append("=" * 60)
        summary.append("POLÍTICA GLOBAL DE CONFIANÇA - AI CORE")
        summary.append("=" * 60)
        summary.append("")
        
        for level in ConfidenceLevel:
            rule = self.GLOBAL_POLICY[level]
            summary.append(f"{level.value.upper()}: {rule['explanation']}")
            summary.append(f"  Ação: {rule['action'].value}")
            summary.append(f"  Revisão: {rule['requires_review']}")
            summary.append(f"  Auditoria: {rule['audit_level']}")
            summary.append("")
        
        summary.append("=" * 60)
        return "\n".join(summary)
