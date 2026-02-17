"""
EXEMPLO COMPLETO - AI Trust & Performance Metrics Framework

Demonstra o fluxo completo de métricas e governança adaptativa:
1. Sistema coleta métricas de decisões e revisões
2. MetricsService calcula e agrega métricas
3. TrustService gera relatórios de confiança
4. DecisionPolicy usa métricas para ajustar thresholds
5. Automação aumenta ou diminui baseado em performance
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any

from app.ai_core.services.metrics_service import MetricsService
from app.ai_core.services.trust_service import TrustService
from app.ai_core.services.decision_policy import DecisionPolicy
from app.ai_core.domain.metrics import MetricPeriod, AIMaturityLevel
from app.utils.logger import logger


class AIGovernanceExample:
    """
    Exemplo de governança de IA com métricas.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.metrics_service = MetricsService(db)
        self.trust_service = TrustService(db, self.metrics_service)
    
    async def analise_completa_tenant(self, tenant_id: int) -> Dict[str, Any]:
        """
        Análise completa de performance da IA para um tenant.
        
        Returns:
            Relatório completo com métricas, trust report e recomendações
        """
        logger.info(f"\\n{'='*60}")
        logger.info(f"  ANÁLISE DE PERFORMANCE DA IA - Tenant {tenant_id}")
        logger.info(f"{'='*60}\\n")
        
        # 1. MÉTRICAS GERAIS
        logger.info("📊 MÉTRICAS GERAIS (Último mês)")
        print("-" * 60)
        
        metrics_monthly = self.metrics_service.get_metrics(
            tenant_id=tenant_id,
            decision_type=None,  # Todas as decisões
            period=MetricPeriod.MONTHLY
        )
        
        if metrics_monthly and metrics_monthly.total_decisions > 0:
            self._print_metrics_summary(metrics_monthly)
        else:
            logger.info("  ⚠️  Sem dados suficientes no período\\n")
        
        # 2. MÉTRICAS POR MÓDULO
        logger.info("\\n📈 MÉTRICAS POR MÓDULO")
        print("-" * 60)
        
        for decision_type in ["categorizar_lancamento", "detectar_intencao", "sugerir_produto"]:
            metrics = self.metrics_service.get_metrics(
                tenant_id=tenant_id,
                decision_type=decision_type,
                period=MetricPeriod.MONTHLY
            )
            
            if metrics and metrics.total_decisions > 0:
                logger.info(f"\\n{decision_type.upper().replace('_', ' ')}:")
                logger.info(f"  Total decisões: {metrics.total_decisions}")
                logger.info(f"  Approval rate: {metrics.approval_rate:.1f}%")
                logger.info(f"  Automation rate: {metrics.automation_rate:.1f}%")
                logger.info(f"  Confiança média: {metrics.avg_confidence_all:.1f}")
        
        # 3. TENDÊNCIAS
        logger.info("\\n\\n📉 TENDÊNCIAS (vs mês anterior)")
        print("-" * 60)
        
        trends = self.metrics_service.get_trends(
            tenant_id=tenant_id,
            decision_type=None
        )
        
        if trends:
            for trend in trends:
                emoji = "📈" if trend.is_improving else "📉"
                print(
                    f"{emoji} {trend.metric_name}: "
                    f"{trend.current_value:.1f} "
                    f"({trend.change_percent:+.1f}%) "
                    f"[{trend.trend}]"
                )
        else:
            logger.info("  ⚠️  Dados insuficientes para calcular tendências")
        
        # 4. TRUST REPORT
        logger.info("\\n\\n🎯 RELATÓRIO DE CONFIANÇA")
        print("-" * 60)
        
        trust_report = self.trust_service.generate_trust_report(
            tenant_id=tenant_id,
            period=MetricPeriod.MONTHLY
        )
        
        self._print_trust_report(trust_report)
        
        # 5. POLÍTICA ADAPTATIVA
        logger.info("\\n\\n⚙️  POLÍTICA ADAPTATIVA")
        print("-" * 60)
        
        adaptive_policy = DecisionPolicy(
            adaptive_mode=True,
            metrics_service=self.metrics_service,
            trust_service=self.trust_service
        )
        
        # Simular decisões com diferentes confianças
        for confidence in [95, 85, 75, 65, 55, 45]:
            policy_result = adaptive_policy.evaluate(
                confidence_score=confidence,
                decision_type="categorizar_lancamento",
                context={"tenant_id": tenant_id}
            )
            
            print(
                f"  Confiança {confidence}%: "
                f"{policy_result.action.value} "
                f"({'REQUER REVISÃO' if policy_result.requires_human_review else 'AUTOMÁTICO'})"
            )
        
        logger.info(f"\\n{'='*60}\\n")
        
        return {
            "metrics": metrics_monthly.dict() if metrics_monthly else None,
            "trust_report": trust_report.dict(),
            "trends": [t.dict() for t in trends]
        }
    
    async def monitorar_maturidade(self, tenant_id: int):
        """
        Monitora evolução da maturidade da IA ao longo do tempo.
        """
        logger.info(f"\\n{'='*60}")
        logger.info(f"  EVOLUÇÃO DA MATURIDADE - Tenant {tenant_id}")
        logger.info(f"{'='*60}\\n")
        
        periods = [
            (MetricPeriod.MONTHLY, "Último Mês"),
            (MetricPeriod.WEEKLY, "Última Semana"),
            (MetricPeriod.DAILY, "Hoje"),
        ]
        
        for period, label in periods:
            trust_report = self.trust_service.generate_trust_report(
                tenant_id=tenant_id,
                period=period
            )
            
            logger.info(f"{label}:")
            logger.info(f"  Maturidade: {trust_report.maturity_level.value.upper()}")
            logger.info(f"  Trust Score: {trust_report.trust_score}/100")
            logger.info(f"  Approval Rate: {trust_report.metrics.approval_rate:.1f}%")
            logger.info(f"  Sample Size: {trust_report.sample_size} decisões")
            logger.info(f"  Pode aumentar automação: {'✅ SIM' if trust_report.can_increase_automation else '❌ NÃO'}")
            print()
    
    async def recomendar_ajustes(self, tenant_id: int):
        """
        Gera recomendações de ajustes baseadas em performance.
        """
        logger.info(f"\\n{'='*60}")
        logger.info(f"  RECOMENDAÇÕES DE AJUSTES - Tenant {tenant_id}")
        logger.info(f"{'='*60}\\n")
        
        trust_report = self.trust_service.generate_trust_report(
            tenant_id=tenant_id,
            period=MetricPeriod.MONTHLY
        )
        
        logger.info("🎯 PONTOS FORTES:")
        for strength in trust_report.strengths:
            logger.info(f"  ✅ {strength}")
        
        logger.info("\\n⚠️  PONTOS FRACOS:")
        for weakness in trust_report.weaknesses:
            logger.info(f"  ⚠️  {weakness}")
        
        logger.info("\\n🚨 RISCOS:")
        for risk in trust_report.risks:
            logger.info(f"  🚨 {risk}")
        
        logger.info("\\n💡 RECOMENDAÇÕES:")
        for rec in trust_report.recommendations:
            logger.info(f"  💡 {rec}")
        
        logger.info("\\n⚙️  AJUSTES DE POLÍTICA SUGERIDOS:")
        logger.info(f"  • Confiança mínima para automação: {trust_report.suggested_min_confidence}%")
        logger.info(f"  • Threshold de revisão obrigatória: {trust_report.suggested_review_threshold}%")
        logger.info(f"  • Aumentar automação: {'✅ Recomendado' if trust_report.can_increase_automation else '❌ Não recomendado'}")
        print()
    
    def _print_metrics_summary(self, metrics):
        """Imprime resumo de métricas."""
        logger.info(f"  Total de decisões: {metrics.total_decisions}")
        logger.info(f"  Decisões revisadas: {metrics.decisions_reviewed} ({metrics.review_pressure:.1f}%)")
        logger.info(f"  Automatizadas: {metrics.decisions_auto_executed} ({metrics.automation_rate:.1f}%)")
        print()
        logger.info(f"  📊 Distribuição por confiança:")
        logger.info(f"     VERY_HIGH (90-100): {metrics.decisions_very_high}")
        logger.info(f"     HIGH (80-89): {metrics.decisions_high}")
        logger.info(f"     MEDIUM (60-79): {metrics.decisions_medium}")
        logger.info(f"     LOW (40-59): {metrics.decisions_low}")
        logger.info(f"     VERY_LOW (0-39): {metrics.decisions_very_low}")
        print()
        logger.info(f"  📈 Performance:")
        logger.info(f"     Approval rate: {metrics.approval_rate:.1f}%")
        logger.info(f"     Correction rate: {metrics.correction_rate:.1f}%")
        logger.info(f"     Rejection rate: {metrics.rejection_rate:.1f}%")
        print()
        logger.info(f"  🎯 Calibração:")
        logger.info(f"     Confiança média: {metrics.avg_confidence_all:.1f}")
        logger.info(f"     Gap confiança-acurácia: {metrics.confidence_accuracy_gap:.1f}")
        print()
    
    def _print_trust_report(self, report):
        """Imprime trust report."""
        logger.info(f"  Nível de Maturidade: {report.maturity_level.value.upper()}")
        logger.info(f"  Trust Score: {report.trust_score}/100")
        logger.info(f"  Amostra: {report.sample_size} decisões")
        logger.info(f"  Confiança estatística: {report.confidence_level}")
        print()
        
        if report.strengths:
            logger.info(f"  Pontos fortes: {len(report.strengths)}")
            for s in report.strengths[:3]:
                logger.info(f"    ✅ {s}")
        
        if report.weaknesses:
            logger.info(f"  Pontos fracos: {len(report.weaknesses)}")
            for w in report.weaknesses[:3]:
                logger.info(f"    ⚠️  {w}")


# ==================== EXEMPLOS DE USO ====================

async def exemplo_analise_tenant():
    """Exemplo: Análise completa de um tenant."""
    from app.db import get_db
    
    db = next(get_db())
    governance = AIGovernanceExample(db)
    
    await governance.analise_completa_tenant(tenant_id=1)


async def exemplo_monitorar_evolucao():
    """Exemplo: Monitorar evolução da maturidade."""
    from app.db import get_db
    
    db = next(get_db())
    governance = AIGovernanceExample(db)
    
    await governance.monitorar_maturidade(tenant_id=1)


async def exemplo_recomendar_ajustes():
    """Exemplo: Recomendar ajustes de política."""
    from app.db import get_db
    
    db = next(get_db())
    governance = AIGovernanceExample(db)
    
    await governance.recomendar_ajustes(tenant_id=1)


async def exemplo_politica_adaptativa():
    """Exemplo: Usar política adaptativa."""
    from app.db import get_db
    from app.ai_core.services.decision_service import DecisionService
    
    db = next(get_db())
    metrics_service = MetricsService(db)
    trust_service = TrustService(db, metrics_service)
    
    # Criar política adaptativa
    adaptive_policy = DecisionPolicy(
        adaptive_mode=True,
        metrics_service=metrics_service,
        trust_service=trust_service
    )
    
    # Usar no DecisionService
    decision_service = DecisionService(
        db=db,
        engines=[],  # Engines configurados
        decision_policy=adaptive_policy
    )
    
    logger.info("✅ DecisionService com política adaptativa configurado")
    logger.info("   → Thresholds ajustam automaticamente baseado em performance")


if __name__ == "__main__":
    import asyncio
    
    print("\\n" + "="*60)
    logger.info("  AI TRUST & PERFORMANCE METRICS - EXEMPLOS")
    print("="*60)
    
    asyncio.run(exemplo_analise_tenant())
