"""
Exemplo de uso do Motor de IA com Insights

Demonstra como usar o AIEngine para interpretar insights gerados pelo sistema.
"""

import asyncio
from datetime import datetime, timedelta

from app.ai.engine import AIEngineFactory
from app.ai.contracts import AIContext
from app.utils.logger import logger


# ============================================================================
# EXEMPLO 1: Análise de Cliente Recorrente Atrasado
# ============================================================================


async def exemplo_cliente_recorrente_atrasado():
    """
    Exemplo de análise de insight: ClienteRecorrenteAtrasado

    Demonstra como a IA interpreta dados estruturados de um insight
    e fornece uma resposta acionável.
    """
    print("=" * 80)
    logger.info("EXEMPLO 1: Cliente Recorrente Atrasado")
    print("=" * 80)

    # 1. Dados estruturados do Insight (já processados pelo sistema)
    insight_data = {
        "cliente_id": 123,
        "cliente_nome": "Maria Silva",
        "cliente_cpf": "123.456.789-00",
        "valor_devido": 450.00,
        "dias_atraso": 15,
        "total_compras_historico": 12,
        "valor_medio_compra": 380.50,
        "ultima_compra": (datetime.now() - timedelta(days=20)).isoformat(),
        "telefone": "(11) 98765-4321",
        "email": "maria.silva@email.com",
    }

    # 2. Contexto estruturado
    context = {
        "tipo_insight": "ClienteRecorrenteAtrasado",
        "dados_insight": insight_data,
        "prioridade": "ALTA",
        "categoria": "Cobrança",
    }

    # 3. Objetivo do usuário
    objetivo = (
        "Como devo abordar este cliente para aumentar as chances "
        "de regularização do pagamento?"
    )

    # 4. Cria instância do Motor de IA
    ai_engine = AIEngineFactory.create_mock_engine()

    # 5. Gera resposta
    response = await ai_engine.generate_response(
        context=context,
        objetivo=objetivo,
        tenant_id=1,  # Multi-tenant obrigatório
    )

    # 6. Exibe resultado
    logger.info("\n📊 CONTEXTO FORNECIDO:")
    logger.info(f"   Cliente: {insight_data['cliente_nome']}")
    logger.info(f"   Valor devido: R$ {insight_data['valor_devido']:.2f}")
    logger.info(f"   Dias de atraso: {insight_data['dias_atraso']}")
    logger.info(f"   Histórico: {insight_data['total_compras_historico']} compras")

    logger.info("\n❓ OBJETIVO:")
    logger.info(f"   {objetivo}")

    logger.info("\n🤖 RESPOSTA DA IA:")
    logger.info(f"   {response.resposta}")

    logger.info("\n💡 EXPLICAÇÃO:")
    logger.info(f"   {response.explicacao}")

    logger.info("\n📋 FONTE DOS DADOS:")
    for fonte in response.fonte_dados:
        logger.info(f"   - {fonte}")

    logger.info(f"\n📊 CONFIANÇA: {response.confianca * 100:.1f}%")
    logger.info(f"⏰ TIMESTAMP: {response.timestamp.isoformat()}")
    logger.info(f"🏢 TENANT: {response.tenant_id}")

    print("\n" + "=" * 80)

    return response


# ============================================================================
# EXEMPLO 2: Uso com AIContext
# ============================================================================


async def exemplo_com_ai_context():
    """
    Exemplo usando AIContext para estruturar a consulta.

    AIContext é a forma recomendada de enviar dados ao Motor de IA.
    """
    print("=" * 80)
    logger.info("EXEMPLO 2: Uso com AIContext")
    print("=" * 80)

    # 1. Cria AIContext estruturado
    ai_context = AIContext(
        tenant_id=1,
        objetivo="Quais ações devo tomar com clientes recorrentes atrasados?",
        dados_estruturados={
            "total_clientes_atrasados": 15,
            "valor_total_devido": 6750.00,
            "clientes_recorrentes": 8,
            "clientes_novos": 7,
            "media_dias_atraso": 18,
            "maior_valor_devido": 890.00,
        },
        metadados={
            "periodo_analise": "últimos_30_dias",
            "categoria": "Gestão Financeira",
        },
    )

    # 2. Cria engine e gera resposta
    ai_engine = AIEngineFactory.create_mock_engine()
    response = await ai_engine.generate_response_from_ai_context(ai_context)

    # 3. Exibe resultado
    logger.info("\n📊 DADOS ANALISADOS:")
    for key, value in ai_context.dados_estruturados.items():
        logger.info(f"   {key}: {value}")

    logger.info("\n🤖 RESPOSTA DA IA:")
    logger.info(f"   {response.resposta}")

    logger.info("\n💡 EXPLICAÇÃO:")
    logger.info(f"   {response.explicacao}")

    print("\n" + "=" * 80)

    return response


# ============================================================================
# EXEMPLO 3: Múltiplos Insights
# ============================================================================


async def exemplo_multiplos_insights():
    """
    Exemplo de análise de múltiplos insights simultaneamente.

    Demonstra como a IA pode correlacionar diferentes insights.
    """
    print("=" * 80)
    logger.info("EXEMPLO 3: Análise de Múltiplos Insights")
    print("=" * 80)

    # Múltiplos insights
    context = {
        "total_insights": 3,
        "insights": [
            {
                "tipo": "ClienteRecorrenteAtrasado",
                "quantidade": 8,
                "valor_total": 3400.00,
            },
            {
                "tipo": "EstoqueBaixoCritico",
                "quantidade": 5,
                "produtos_afetados": ["Ração Premium", "Coleira XL", "Brinquedo"],
            },
            {"tipo": "VendasAcimaMedia", "quantidade": 12, "aumento_percentual": 25.5},
        ],
        "periodo": "últimos_7_dias",
    }

    objetivo = (
        "Qual a prioridade de ação entre estes insights e como eles se relacionam?"
    )

    ai_engine = AIEngineFactory.create_mock_engine()
    response = await ai_engine.generate_response(
        context=context, objetivo=objetivo, tenant_id=1
    )

    logger.info("\n📊 INSIGHTS ANALISADOS:")
    for insight in context["insights"]:
        logger.info(f"   - {insight['tipo']}: {insight['quantidade']} ocorrências")

    logger.info("\n🤖 RESPOSTA DA IA:")
    logger.info(f"   {response.resposta}")

    logger.info("\n💡 EXPLICAÇÃO:")
    logger.info(f"   {response.explicacao}")

    print("\n" + "=" * 80)

    return response


# ============================================================================
# Executar todos os exemplos
# ============================================================================


async def main():
    """Executa todos os exemplos."""
    logger.info("\n🚀 EXEMPLOS DE USO DO MOTOR DE IA\n")

    # Exemplo 1
    await exemplo_cliente_recorrente_atrasado()
    await asyncio.sleep(1)

    # Exemplo 2
    await exemplo_com_ai_context()
    await asyncio.sleep(1)

    # Exemplo 3
    await exemplo_multiplos_insights()

    logger.info("\n✅ Todos os exemplos executados com sucesso!\n")


if __name__ == "__main__":
    asyncio.run(main())
