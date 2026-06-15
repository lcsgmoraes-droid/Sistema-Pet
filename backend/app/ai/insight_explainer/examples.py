"""
Exemplos de Uso do Sistema de IA Explicadora de Insights

Demonstra como usar o InsightExplanationService para transformar
insights técnicos (Sprint 5) em explicações compreensíveis.

IMPORTANTE:
- A IA NÃO cria insights
- A IA NÃO altera severidade
- A IA NÃO executa ações
- A IA apenas explica e sugere abordagem
"""

import asyncio
from datetime import datetime, timedelta

from app.insights.models import (
    Insight,
    TipoInsight,
    SeveridadeInsight,
    EntidadeInsight
)
from app.ai.insight_explainer import InsightExplanationService
from app.utils.logger import logger


# ============================================================================
# EXEMPLO 1: Cliente Recorrente Atrasado
# ============================================================================

async def exemplo_cliente_atrasado():
    """
    Explica um insight de cliente recorrente atrasado.
    
    Simula um cliente que costuma comprar a cada 15 dias
    mas está há 25 dias sem comprar.
    """
    print("=" * 80)
    logger.info("EXEMPLO 1: Cliente Recorrente Atrasado")
    print("=" * 80)
    
    # 1. Criar Insight (normalmente vem do InsightEngine do Sprint 5)
    insight = Insight(
        id="INS-20260125-001",
        tipo=TipoInsight.CLIENTE_RECORRENTE_ATRASADO,
        titulo="Maria Silva está atrasada em sua compra recorrente",
        descricao=(
            "Cliente Maria Silva (ID: 123) costuma comprar ração premium "
            "a cada 15 dias. Última compra foi há 25 dias, indicando "
            "atraso de 10 dias no padrão esperado."
        ),
        severidade=SeveridadeInsight.ATENCAO,
        entidade=EntidadeInsight.CLIENTE,
        entidade_id=123,
        dados_contexto={
            "cliente_nome": "Maria Silva",
            "cliente_id": 123,
            "frequencia_esperada_dias": 15,
            "dias_desde_ultima_compra": 25,
            "atraso_dias": 10,
            "produto_habitual": "Ração Premium Golden 15kg",
            "ticket_medio": 285.50,
            "total_compras_historico": 18,
            "valor_total_historico": 5139.00,
            "telefone": "(11) 98765-4321",
            "segmento": "Recorrente"
        },
        metricas={
            "frequencia_dias": 15.0,
            "desvio_padrao_dias": 2.5,
            "atraso_dias": 10.0,
            "probabilidade_compra_proximos_7dias": 0.75,
            "lifetime_value": 5139.00
        },
        acao_sugerida=(
            "Entre em contato via WhatsApp oferecendo promoção personalizada "
            "de 10% na ração habitual."
        ),
        user_id=1,  # Multi-tenant
        timestamp=datetime.now()
    )
    
    # 2. Criar serviço de explicação
    service = InsightExplanationService(use_mock=True)
    
    # 3. Gerar explicação
    logger.info("\n🔄 Gerando explicação com IA...")
    explicacao = await service.explicar_insight(insight, tenant_id=1)
    
    # 4. Exibir resultados
    print("\n" + "=" * 80)
    logger.info("📊 INSIGHT ORIGINAL (TÉCNICO):")
    print("=" * 80)
    logger.info(f"ID: {insight.id}")
    logger.info(f"Tipo: {insight.tipo.value}")
    logger.info(f"Título: {insight.titulo}")
    logger.info(f"Severidade: {insight.severidade.value}")
    logger.info(f"Descrição: {insight.descricao}")
    
    print("\n" + "=" * 80)
    logger.info("🤖 EXPLICAÇÃO DA IA (COMPREENSÍVEL):")
    print("=" * 80)
    logger.info("\n📌 TÍTULO:")
    logger.info(f"   {explicacao.titulo}")
    
    logger.info("\n💡 EXPLICAÇÃO:")
    logger.info(f"   {explicacao.explicacao}")
    
    logger.info("\n🎯 SUGESTÃO DE AÇÃO:")
    logger.info(f"   {explicacao.sugestao}")
    
    logger.info(f"\n📊 CONFIANÇA: {explicacao.confianca * 100:.1f}%")
    
    logger.info("\n📋 FONTE DOS DADOS:")
    for fonte in explicacao.fonte_dados:
        logger.info(f"   - {fonte}")
    
    logger.info(f"\n🏢 Tenant: {explicacao.tenant_id}")
    logger.info(f"⏰ Timestamp: {explicacao.timestamp.isoformat()}")
    
    print("\n" + "=" * 80)
    
    return explicacao


# ============================================================================
# EXEMPLO 2: Cliente Inativo
# ============================================================================

async def exemplo_cliente_inativo():
    """
    Explica um insight de cliente inativo.
    
    Cliente que não compra há mais de 90 dias.
    """
    print("=" * 80)
    logger.info("EXEMPLO 2: Cliente Inativo")
    print("=" * 80)
    
    insight = Insight(
        id="INS-20260125-002",
        tipo=TipoInsight.CLIENTE_INATIVO,
        titulo="João Santos está inativo há 120 dias",
        descricao=(
            "Cliente João Santos (ID: 456) não realiza compras há 120 dias. "
            "Anteriormente era cliente regular com compras mensais."
        ),
        severidade=SeveridadeInsight.ATENCAO,
        entidade=EntidadeInsight.CLIENTE,
        entidade_id=456,
        dados_contexto={
            "cliente_nome": "João Santos",
            "cliente_id": 456,
            "dias_sem_comprar": 120,
            "ultima_compra": (datetime.now() - timedelta(days=120)).isoformat(),
            "frequencia_anterior": "Mensal",
            "total_compras_historico": 8,
            "valor_total_historico": 1850.00,
            "ticket_medio": 231.25,
            "segmento_anterior": "Regular"
        },
        metricas={
            "dias_inatividade": 120.0,
            "valor_potencial_perdido": 462.50,  # 2 meses * ticket_medio
            "probabilidade_reativacao": 0.35
        },
        acao_sugerida=(
            "Campanha de reativação com desconto especial e pesquisa de satisfação."
        ),
        user_id=1,
        timestamp=datetime.now()
    )
    
    service = InsightExplanationService(use_mock=True)
    
    logger.info("\n🔄 Gerando explicação com IA...")
    explicacao = await service.explicar_insight(insight, tenant_id=1)
    
    print("\n" + "=" * 80)
    logger.info("🤖 EXPLICAÇÃO DA IA:")
    print("=" * 80)
    logger.info(f"\n💡 {explicacao.explicacao}")
    logger.info(f"\n🎯 {explicacao.sugestao}")
    logger.info(f"\n📊 Confiança: {explicacao.confianca * 100:.1f}%")
    
    print("\n" + "=" * 80)
    
    return explicacao


# ============================================================================
# EXEMPLO 3: Produtos Comprados Juntos
# ============================================================================

async def exemplo_produtos_juntos():
    """
    Explica um insight de cross-sell.
    
    Produtos frequentemente comprados juntos.
    """
    print("=" * 80)
    logger.info("EXEMPLO 3: Oportunidade de Cross-Sell")
    print("=" * 80)
    
    insight = Insight(
        id="INS-20260125-003",
        tipo=TipoInsight.PRODUTOS_COMPRADOS_JUNTOS,
        titulo="Ração + Antipulgas comprados juntos em 85% dos casos",
        descricao=(
            "Análise de 50 vendas nos últimos 30 dias mostra que clientes "
            "que compram Ração Premium também compram Antipulgas em 85% das vezes."
        ),
        severidade=SeveridadeInsight.OPORTUNIDADE,
        entidade=EntidadeInsight.PRODUTO,
        entidade_id=None,  # Múltiplos produtos
        dados_contexto={
            "produto_principal": "Ração Premium Golden 15kg",
            "produto_principal_id": 101,
            "produto_complementar": "Antipulgas Bravecto",
            "produto_complementar_id": 202,
            "correlacao_percentual": 85.0,
            "total_vendas_analisadas": 50,
            "vendas_com_ambos": 42,
            "ticket_medio_combo": 385.00,
            "ticket_medio_individual": 285.00,
            "uplift_valor": 100.00
        },
        metricas={
            "correlacao": 0.85,
            "confianca_estatistica": 0.92,
            "valor_oportunidade_mensal": 4200.00
        },
        acao_sugerida=(
            "Oferecer Antipulgas quando cliente comprar Ração Premium. "
            "Criar combo promocional."
        ),
        user_id=1,
        timestamp=datetime.now()
    )
    
    service = InsightExplanationService(use_mock=True)
    
    logger.info("\n🔄 Gerando explicação com IA...")
    explicacao = await service.explicar_insight(insight, tenant_id=1)
    
    print("\n" + "=" * 80)
    logger.info("🤖 EXPLICAÇÃO DA IA:")
    print("=" * 80)
    logger.info(f"\n💡 {explicacao.explicacao}")
    logger.info(f"\n🎯 {explicacao.sugestao}")
    logger.info(f"\n📊 Confiança: {explicacao.confianca * 100:.1f}%")
    
    print("\n" + "=" * 80)
    
    return explicacao


# ============================================================================
# EXEMPLO 4: Kit Mais Vantajoso
# ============================================================================

async def exemplo_kit_vantajoso():
    """
    Explica um insight de kit com melhor custo-benefício.
    """
    print("=" * 80)
    logger.info("EXEMPLO 4: Kit Mais Vantajoso")
    print("=" * 80)
    
    insight = Insight(
        id="INS-20260125-004",
        tipo=TipoInsight.KIT_MAIS_VANTAJOSO,
        titulo="Kit Higiene Completa economiza R$ 45 (15%)",
        descricao=(
            "Kit Higiene Completa (Shampoo + Condicionador + Escova) "
            "custa R$ 255 vs. R$ 300 comprando itens separadamente."
        ),
        severidade=SeveridadeInsight.OPORTUNIDADE,
        entidade=EntidadeInsight.KIT,
        entidade_id=501,
        dados_contexto={
            "kit_nome": "Kit Higiene Completa",
            "kit_id": 501,
            "kit_preco": 255.00,
            "itens": [
                {"nome": "Shampoo Pet Premium", "preco": 89.90},
                {"nome": "Condicionador Pet Premium", "preco": 79.90},
                {"nome": "Escova Profissional", "preco": 130.00}
            ],
            "preco_itens_separados": 300.00,
            "economia_reais": 45.00,
            "economia_percentual": 15.0,
            "vendas_kit_mes": 12,
            "vendas_itens_separados_mes": 35
        },
        metricas={
            "economia_percentual": 15.0,
            "preferencia_kit": 0.25,  # 12/(12+35)
            "valor_oportunidade": 1575.00  # 35 vendas * R$45
        },
        acao_sugerida=(
            "Destacar economia ao oferecer itens de higiene. "
            "Criar display no PDV mostrando comparativo."
        ),
        user_id=1,
        timestamp=datetime.now()
    )
    
    service = InsightExplanationService(use_mock=True)
    
    logger.info("\n🔄 Gerando explicação com IA...")
    explicacao = await service.explicar_insight(insight, tenant_id=1)
    
    print("\n" + "=" * 80)
    logger.info("🤖 EXPLICAÇÃO DA IA:")
    print("=" * 80)
    logger.info(f"\n💡 {explicacao.explicacao}")
    logger.info(f"\n🎯 {explicacao.sugestao}")
    logger.info(f"\n📊 Confiança: {explicacao.confianca * 100:.1f}%")
    
    print("\n" + "=" * 80)
    
    return explicacao


# ============================================================================
# EXEMPLO 5: Múltiplos Insights
# ============================================================================

async def exemplo_multiplos_insights():
    """
    Explica múltiplos insights em lote.
    """
    print("=" * 80)
    logger.info("EXEMPLO 5: Explicação em Lote")
    print("=" * 80)
    
    # Criar vários insights
    insights = [
        Insight(
            id=f"INS-BATCH-00{i}",
            tipo=TipoInsight.CLIENTE_RECORRENTE_ATRASADO,
            titulo=f"Cliente {i} atrasado",
            descricao=f"Cliente está há {10+i} dias atrasado",
            severidade=SeveridadeInsight.ATENCAO,
            entidade=EntidadeInsight.CLIENTE,
            entidade_id=100+i,
            dados_contexto={"dias_atraso": 10+i},
            user_id=1,
            timestamp=datetime.now()
        )
        for i in range(1, 4)
    ]
    
    service = InsightExplanationService(use_mock=True)
    
    logger.info(f"\n🔄 Explicando {len(insights)} insights em lote...")
    explicacoes = await service.explicar_multiplos_insights(insights, tenant_id=1)
    
    logger.info(f"\n✅ {len(explicacoes)} explicações geradas!")
    
    for i, explicacao in enumerate(explicacoes, 1):
        logger.info(f"\n{i}. {explicacao.titulo}")
        logger.info(f"   Confiança: {explicacao.confianca * 100:.1f}%")
    
    print("\n" + "=" * 80)
    
    return explicacoes


# ============================================================================
# Executar todos os exemplos
# ============================================================================

async def main():
    """Executa todos os exemplos."""
    logger.info("\n🚀 SISTEMA DE IA EXPLICADORA DE INSIGHTS\n")
    logger.info("Sprint 6 - Passo 2")
    logger.info("Transforma insights técnicos em explicações compreensíveis\n")
    
    # Exemplo 1
    await exemplo_cliente_atrasado()
    await asyncio.sleep(1)
    
    # Exemplo 2
    await exemplo_cliente_inativo()
    await asyncio.sleep(1)
    
    # Exemplo 3
    await exemplo_produtos_juntos()
    await asyncio.sleep(1)
    
    # Exemplo 4
    await exemplo_kit_vantajoso()
    await asyncio.sleep(1)
    
    # Exemplo 5
    await exemplo_multiplos_insights()
    
    logger.info("\n✅ Todos os exemplos executados com sucesso!\n")
    logger.info("💡 Próximos passos:")
    logger.info("   - Integrar com OpenAI (substituir mock)")
    logger.info("   - Criar endpoints REST")
    logger.info("   - Integrar com PDV")
    logger.info("   - Integrar com WhatsApp")
    print()


if __name__ == "__main__":
    asyncio.run(main())
