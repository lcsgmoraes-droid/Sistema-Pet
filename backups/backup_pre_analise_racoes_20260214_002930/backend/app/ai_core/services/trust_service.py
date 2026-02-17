"""
TrustService - Geração de relatórios de confiança da IA

Responsável por:
- Avaliar maturidade da IA
- Gerar recomendações automáticas
- Sugerir ajustes de política
- Identificar riscos e oportunidades
"""
from typing import Optional, List
from sqlalchemy.orm import Session
import logging

from ..domain.metrics import (
    AIPerformanceMetrics,
    AITrustReport,
    AIMaturityLevel,
    MetricPeriod
)
from .metrics_service import MetricsService

logger = logging.getLogger(__name__)


class TrustService:
    """
    Serviço de análise de confiança da IA.
    
    Gera relatórios com:
    - Nível de maturidade
    - Pontos fortes e fracos
    - Riscos identificados
    - Recomendações de ação
    - Sugestões de ajuste de política
    
    Baseado em métricas históricas reais.
    """
    
    def __init__(self, db: Session, metrics_service: Optional[MetricsService] = None):
        self.db = db
        self.metrics_service = metrics_service or MetricsService(db)
    
    def generate_trust_report(
        self,
        tenant_id: int,
        decision_type: Optional[str] = None,
        period: MetricPeriod = MetricPeriod.MONTHLY
    ) -> AITrustReport:
        """
        Gera relatório de confiança completo para um tenant/módulo.
        
        Args:
            tenant_id: ID do tenant
            decision_type: Tipo de decisão (None = todas)
            period: Período de análise
        
        Returns:
            AITrustReport com análise completa
        """
        logger.info(
            f"📊 Gerando Trust Report | "
            f"Tenant: {tenant_id} | "
            f"Type: {decision_type or 'ALL'} | "
            f"Period: {period.value}"
        )
        
        # 1. Obter métricas
        metrics = self.metrics_service.get_metrics(
            tenant_id=tenant_id,
            decision_type=decision_type,
            period=period
        )
        
        if not metrics or metrics.total_decisions == 0:
            return self._create_no_data_report(tenant_id, decision_type, period)
        
        # 2. Avaliar maturidade
        maturity_level = self._calculate_maturity(metrics)
        
        # 3. Calcular trust score
        trust_score = self._calculate_trust_score(metrics, maturity_level)
        
        # 4. Analisar pontos fortes
        strengths = self._identify_strengths(metrics)
        
        # 5. Analisar pontos fracos
        weaknesses = self._identify_weaknesses(metrics)
        
        # 6. Identificar riscos
        risks = self._identify_risks(metrics)
        
        # 7. Gerar recomendações
        recommendations = self._generate_recommendations(metrics, maturity_level)
        
        # 8. Sugerir thresholds
        suggested_min_confidence = self._suggest_min_confidence(metrics, maturity_level)
        suggested_review_threshold = self._suggest_review_threshold(metrics, maturity_level)
        
        # 9. Avaliar se pode aumentar automação
        can_increase_automation = self._can_increase_automation(metrics, maturity_level)
        
        # 10. Avaliar confiança estatística
        confidence_level = self._get_statistical_confidence(metrics.total_decisions)
        
        report = AITrustReport(
            tenant_id=tenant_id,
            decision_type=decision_type,
            period=period,
            metrics=metrics,
            maturity_level=maturity_level,
            trust_score=trust_score,
            strengths=strengths,
            weaknesses=weaknesses,
            risks=risks,
            recommendations=recommendations,
            suggested_min_confidence=suggested_min_confidence,
            suggested_review_threshold=suggested_review_threshold,
            can_increase_automation=can_increase_automation,
            sample_size=metrics.total_decisions,
            confidence_level=confidence_level
        )
        
        logger.info(
            f"✅ Trust Report gerado | "
            f"Maturidade: {maturity_level.value} | "
            f"Trust Score: {trust_score}"
        )
        
        return report
    
    # ==================== AVALIAÇÕES ====================
    
    def _calculate_maturity(self, metrics: AIPerformanceMetrics) -> AIMaturityLevel:
        """
        Calcula nível de maturidade baseado em approval_rate.
        
        Thresholds:
        - < 50%: LEARNING
        - 50-70%: DEVELOPING
        - 70-85%: RELIABLE
        - 85-95%: MATURE
        - > 95%: EXPERT
        """
        approval = metrics.approval_rate
        
        if approval < 50:
            return AIMaturityLevel.LEARNING
        elif approval < 70:
            return AIMaturityLevel.DEVELOPING
        elif approval < 85:
            return AIMaturityLevel.RELIABLE
        elif approval < 95:
            return AIMaturityLevel.MATURE
        else:
            return AIMaturityLevel.EXPERT
    
    def _calculate_trust_score(
        self,
        metrics: AIPerformanceMetrics,
        maturity: AIMaturityLevel
    ) -> int:
        """
        Calcula score de confiança (0-100) baseado em múltiplos fatores.
        
        Pesos:
        - approval_rate: 40%
        - automation_rate: 20%
        - confidence_accuracy_gap (inverso): 20%
        - rejection_rate (inverso): 10%
        - sample_size: 10%
        """
        # Approval (40 pontos)
        approval_score = (metrics.approval_rate / 100) * 40
        
        # Automation (20 pontos)
        automation_score = (metrics.automation_rate / 100) * 20
        
        # Calibração (20 pontos) - quanto menor o gap, melhor
        gap_normalized = max(0, 100 - metrics.confidence_accuracy_gap * 5)  # Gap de 20 = 0 pontos
        calibration_score = (gap_normalized / 100) * 20
        
        # Rejeição (10 pontos) - quanto menor, melhor
        rejection_normalized = max(0, 100 - metrics.rejection_rate * 10)
        rejection_score = (rejection_normalized / 100) * 10
        
        # Sample size (10 pontos)
        if metrics.total_decisions < 10:
            sample_score = 2
        elif metrics.total_decisions < 50:
            sample_score = 5
        elif metrics.total_decisions < 100:
            sample_score = 7
        else:
            sample_score = 10
        
        total = approval_score + automation_score + calibration_score + rejection_score + sample_score
        
        return int(round(total))
    
    def _identify_strengths(self, metrics: AIPerformanceMetrics) -> List[str]:
        """Identifica pontos fortes da IA."""
        strengths = []
        
        if metrics.approval_rate >= 85:
            strengths.append(f"Alta taxa de aprovação ({metrics.approval_rate:.1f}%)")
        
        if metrics.automation_rate >= 70:
            strengths.append(f"Alto nível de automação ({metrics.automation_rate:.1f}%)")
        
        if metrics.confidence_accuracy_gap < 10:
            strengths.append(f"Bem calibrada (gap de confiança: {metrics.confidence_accuracy_gap:.1f})")
        
        if metrics.rejection_rate < 5:
            strengths.append(f"Baixa taxa de rejeição ({metrics.rejection_rate:.1f}%)")
        
        if metrics.avg_processing_time_ms < 100:
            strengths.append(f"Processamento rápido ({metrics.avg_processing_time_ms:.1f}ms)")
        
        if not strengths:
            strengths.append("IA em fase de aprendizado, coletando dados")
        
        return strengths
    
    def _identify_weaknesses(self, metrics: AIPerformanceMetrics) -> List[str]:
        """Identifica pontos fracos da IA."""
        weaknesses = []
        
        if metrics.approval_rate < 50:
            weaknesses.append(f"Baixa taxa de aprovação ({metrics.approval_rate:.1f}%)")
        
        if metrics.correction_rate > 30:
            weaknesses.append(f"Alta taxa de correção ({metrics.correction_rate:.1f}%)")
        
        if metrics.rejection_rate > 10:
            weaknesses.append(f"Alta taxa de rejeição ({metrics.rejection_rate:.1f}%)")
        
        if metrics.confidence_accuracy_gap > 20:
            weaknesses.append(f"Mal calibrada (gap: {metrics.confidence_accuracy_gap:.1f})")
        
        if metrics.review_pressure > 60:
            weaknesses.append(f"Alta pressão de revisão ({metrics.review_pressure:.1f}%)")
        
        if metrics.total_decisions < 50:
            weaknesses.append(f"Amostra pequena ({metrics.total_decisions} decisões)")
        
        return weaknesses
    
    def _identify_risks(self, metrics: AIPerformanceMetrics) -> List[str]:
        """Identifica riscos operacionais."""
        risks = []
        
        if metrics.approval_rate < 50 and metrics.automation_rate > 50:
            risks.append("CRÍTICO: Automação alta com aprovação baixa - risco de erros")
        
        if metrics.rejection_rate > 20:
            risks.append("ALTO: Taxa de rejeição muito alta - IA fazendo sugestões ruins")
        
        if metrics.confidence_accuracy_gap > 25:
            risks.append("ALTO: IA mal calibrada - confiança não reflete realidade")
        
        if metrics.total_decisions < 20:
            risks.append("MÉDIO: Amostra insuficiente para decisões confiáveis")
        
        if metrics.review_pressure > 70:
            risks.append("MÉDIO: Pressão de revisão alta - gargalo operacional")
        
        if metrics.avg_confidence_corrected > 75:
            risks.append("MÉDIO: IA confiante em decisões erradas - overconfidence")
        
        if not risks:
            risks.append("Nenhum risco crítico identificado")
        
        return risks
    
    def _generate_recommendations(
        self,
        metrics: AIPerformanceMetrics,
        maturity: AIMaturityLevel
    ) -> List[str]:
        """Gera recomendações de ação."""
        recommendations = []
        
        # Recomendações por maturidade
        if maturity == AIMaturityLevel.LEARNING:
            recommendations.append("Manter revisão humana obrigatória para todas as decisões")
            recommendations.append("Coletar mais feedbacks para treinar padrões")
            recommendations.append("Não aumentar automação até approval_rate > 70%")
        
        elif maturity == AIMaturityLevel.DEVELOPING:
            recommendations.append("Continuar com revisão humana para confiança < 80%")
            recommendations.append("Revisar padrões com baixa performance")
            recommendations.append("Aumentar automação gradualmente")
        
        elif maturity == AIMaturityLevel.RELIABLE:
            recommendations.append("Pode executar automaticamente decisões com confiança > 85%")
            recommendations.append("Manter revisão para confiança 60-85%")
            recommendations.append("Monitorar tendências de performance")
        
        elif maturity == AIMaturityLevel.MATURE:
            recommendations.append("Considerar aumentar threshold de automação para 80%")
            recommendations.append("Focar em otimizar casos de baixa confiança")
            recommendations.append("IA pronta para escalar automação")
        
        elif maturity == AIMaturityLevel.EXPERT:
            recommendations.append("IA altamente confiável - pode maximizar automação")
            recommendations.append("Manter monitoramento para detectar drift")
            recommendations.append("Revisar apenas casos de confiança < 70%")
        
        # Recomendações específicas
        if metrics.confidence_accuracy_gap > 15:
            recommendations.append(f"Recalibrar modelo - gap de {metrics.confidence_accuracy_gap:.1f} é alto")
        
        if metrics.correction_rate > 25:
            recommendations.append("Analisar padrões mais corrigidos e ajustar engines")
        
        if metrics.rejection_rate > 15:
            recommendations.append("Revisar lógica de engines - muitas sugestões inadequadas")
        
        return recommendations
    
    def _suggest_min_confidence(
        self,
        metrics: AIPerformanceMetrics,
        maturity: AIMaturityLevel
    ) -> int:
        """Sugere confiança mínima para automação."""
        maturity_thresholds = {
            AIMaturityLevel.LEARNING: 95,      # Quase nunca automatizar
            AIMaturityLevel.DEVELOPING: 90,    # Apenas VERY_HIGH
            AIMaturityLevel.RELIABLE: 85,      # HIGH e VERY_HIGH
            AIMaturityLevel.MATURE: 80,        # A partir de 80%
            AIMaturityLevel.EXPERT: 75         # Pode baixar threshold
        }
        
        base_threshold = maturity_thresholds.get(maturity, 85)
        
        # Ajustes baseados em métricas
        if metrics.confidence_accuracy_gap > 20:
            base_threshold += 5  # Mais conservador se mal calibrado
        
        if metrics.rejection_rate > 10:
            base_threshold += 5  # Mais conservador se muitas rejeições
        
        return min(base_threshold, 95)
    
    def _suggest_review_threshold(
        self,
        metrics: AIPerformanceMetrics,
        maturity: AIMaturityLevel
    ) -> int:
        """Sugere threshold para revisão obrigatória."""
        maturity_thresholds = {
            AIMaturityLevel.LEARNING: 100,     # Revisar tudo
            AIMaturityLevel.DEVELOPING: 85,    # Revisar < 85%
            AIMaturityLevel.RELIABLE: 75,      # Revisar < 75%
            AIMaturityLevel.MATURE: 70,        # Revisar < 70%
            AIMaturityLevel.EXPERT: 65         # Revisar < 65%
        }
        
        return maturity_thresholds.get(maturity, 80)
    
    def _can_increase_automation(
        self,
        metrics: AIPerformanceMetrics,
        maturity: AIMaturityLevel
    ) -> bool:
        """Avalia se pode aumentar automação com segurança."""
        return (
            maturity in [AIMaturityLevel.RELIABLE, AIMaturityLevel.MATURE, AIMaturityLevel.EXPERT]
            and metrics.approval_rate >= 75
            and metrics.rejection_rate < 10
            and metrics.confidence_accuracy_gap < 15
            and metrics.total_decisions >= 50
        )
    
    def _get_statistical_confidence(self, sample_size: int) -> str:
        """Retorna nível de confiança estatística."""
        if sample_size < 30:
            return "low"
        elif sample_size < 100:
            return "medium"
        else:
            return "high"
    
    def _create_no_data_report(
        self,
        tenant_id: int,
        decision_type: Optional[str],
        period: MetricPeriod
    ) -> AITrustReport:
        """Cria relatório quando não há dados."""
        empty_metrics = AIPerformanceMetrics(
            tenant_id=tenant_id,
            decision_type=decision_type,
            period=period,
            period_start=datetime.today().date(),
            period_end=datetime.today().date()
        )
        
        return AITrustReport(
            tenant_id=tenant_id,
            decision_type=decision_type,
            period=period,
            metrics=empty_metrics,
            maturity_level=AIMaturityLevel.LEARNING,
            trust_score=0,
            strengths=[],
            weaknesses=["Sem dados suficientes para análise"],
            risks=["Não há histórico de decisões"],
            recommendations=[
                "Começar a usar IA para gerar dados",
                "Fornecer feedback em todas as decisões",
                "Aguardar pelo menos 30 decisões antes de ajustar políticas"
            ],
            suggested_min_confidence=95,
            suggested_review_threshold=100,
            can_increase_automation=False,
            sample_size=0,
            confidence_level="low"
        )
