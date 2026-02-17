"""
Exemplos de Uso - Integração OpenAI

Demonstra como usar o sistema de IA com diferentes providers.

EXECUÇÃO:
1. Mock (padrão):
   python exemplos_integracao_openai.py

2. OpenAI (requer API key):
   export AI_PROVIDER=openai
   export OPENAI_API_KEY=sk-...
   python exemplos_integracao_openai.py

3. Com controle de custo:
   export DAILY_COST_LIMIT_USD=1.00
   python exemplos_integracao_openai.py
"""

import asyncio
import os
from typing import Dict, Any

# Configurar ENV antes de importar (para testes)
os.environ.setdefault("AI_PROVIDER", "mock")
os.environ.setdefault("MAX_TOKENS", "300")
os.environ.setdefault("TIMEOUT_SECONDS", "5")

from backend.app.ai.engine import AIEngine, AIEngineFactory
from backend.app.ai.settings import AISettings
from backend.app.ai.cost_control import get_cost_controller
from app.utils.logger import logger


# ============================================================================
# EXEMPLO 1: Uso Básico com Provider Configurado
# ============================================================================

async def exemplo_1_uso_basico():
    """Exemplo básico: gerar resposta com provider configurado"""
    
    print("\n" + "=" * 70)
    logger.info("EXEMPLO 1: Uso Básico")
    print("=" * 70)
    
    # Criar engine de produção (usa AISettings.PROVIDER)
    engine = AIEngineFactory.create_production_engine()
    
    # Preparar contexto (dados já processados)
    context = {
        "origem": "operator_chat",
        "tipo_consulta": "cliente",
        "dados_cliente": {
            "nome": "João Silva",
            "total_compras": 15,
            "valor_total": 2500.00,
            "ultima_compra": "2024-01-15"
        }
    }
    
    # Gerar resposta
    response = await engine.generate_response(
        context=context,
        objetivo="Resumir histórico do cliente João Silva",
        tenant_id=1
    )
    
    # Exibir resultado
    logger.info(f"\n📊 Resposta:")
    logger.info(f"   {response.resposta}\n")
    logger.info(f"💡 Explicação:")
    logger.info(f"   {response.explicacao}\n")
    logger.info(f"📚 Fonte de Dados: {response.fonte_dados}")
    logger.info(f"🎯 Confiança: {response.confianca:.0%}")
    
    # Metadados (auditoria)
    logger.info(f"\n🔍 Metadados:")
    logger.info(f"   Provider: {response.metadata.get('provider', 'N/A')}")
    logger.info(f"   Modelo: {response.metadata.get('model', 'N/A')}")
    logger.info(f"   Tokens: {response.metadata.get('tokens', 0)}")
    logger.info(f"   Custo: ${response.metadata.get('cost_usd', 0):.4f}")
    logger.info(f"   Latência: {response.metadata.get('latency_ms', 0)}ms")
    logger.info(f"   Fallback usado: {response.metadata.get('fallback_used', False)}")


# ============================================================================
# EXEMPLO 2: Controle de Custo
# ============================================================================

async def exemplo_2_controle_custo():
    """Demonstra controle de custo por tenant"""
    
    print("\n" + "=" * 70)
    logger.info("EXEMPLO 2: Controle de Custo")
    print("=" * 70)
    
    # Obter cost controller
    cost_controller = get_cost_controller()
    
    # Verificar limite antes de processar
    tenant_id = 1
    can_proceed, reason = cost_controller.check_can_proceed(tenant_id)
    
    logger.info(f"\n💰 Status do Limite de Custo:")
    logger.info(f"   Pode processar: {can_proceed}")
    logger.info(f"   Razão: {reason}")
    
    if can_proceed:
        # Processar com engine
        engine = AIEngineFactory.create_production_engine()
        
        context = {
            "origem": "pdv",
            "tipo_consulta": "venda",
            "dados_venda": {
                "valor": 150.00,
                "produtos": ["Ração Premium", "Shampoo Pet"]
            }
        }
        
        response = await engine.generate_response(
            context=context,
            objetivo="Sugerir produtos complementares",
            tenant_id=tenant_id
        )
        
        logger.info(f"\n✅ Resposta gerada com sucesso")
        logger.info(f"   Custo desta operação: ${response.metadata.get('cost_usd', 0):.4f}")
        
        # Obter resumo de uso
        usage_summary = cost_controller.get_usage_summary(tenant_id)
        logger.info(f"\n📊 Uso Acumulado do Dia:")
        logger.info(f"   Total de tokens: {usage_summary['total_tokens']}")
        logger.info(f"   Total de custo: ${usage_summary['total_cost']:.4f}")
        logger.info(f"   Requisições: {usage_summary['request_count']}")
        logger.info(f"   Limite diário: ${usage_summary['limit_usd']:.2f}")
        logger.info(f"   Percentual usado: {usage_summary['usage_percent']:.1f}%")
    else:
        logger.info("\n⚠️ Limite de custo excedido - operação bloqueada")


# ============================================================================
# EXEMPLO 3: Fallback Automático
# ============================================================================

async def exemplo_3_fallback():
    """Demonstra fallback para mock em caso de erro"""
    
    print("\n" + "=" * 70)
    logger.info("EXEMPLO 3: Fallback Automático")
    print("=" * 70)
    
    # Simular situação de erro (API key inválida)
    logger.info("\n🔧 Simulando falha no provider principal...")
    logger.info(f"   Provider configurado: {AISettings.PROVIDER.value}")
    logger.info(f"   Fallback habilitado: {AISettings.ENABLE_FALLBACK}")
    
    # Criar engine
    engine = AIEngineFactory.create_production_engine()
    
    context = {
        "origem": "insight_explainer",
        "tipo_insight": "ClienteRecorrente",
        "dados_insight": {
            "cliente_nome": "Maria Santos",
            "valor_devido": 450.00,
            "dias_atraso": 15
        }
    }
    
    try:
        response = await engine.generate_response(
            context=context,
            objetivo="Explicar porque este cliente foi identificado",
            tenant_id=1
        )
        
        # Verificar se fallback foi usado
        if response.metadata.get("fallback_used", False):
            logger.info("\n⚠️ Fallback ativado!")
            logger.info(f"   Erro original: {response.metadata.get('original_provider_error', 'N/A')}")
            logger.info(f"   Provider usado: {response.metadata.get('provider', 'N/A')}")
        else:
            logger.info("\n✅ Provider principal funcionou normalmente")
        
        logger.info(f"\n📊 Resposta:")
        logger.info(f"   {response.resposta}")
        
    except Exception as e:
        logger.info(f"\n❌ Erro sem fallback: {e}")


# ============================================================================
# EXEMPLO 4: Comparação Mock vs OpenAI
# ============================================================================

async def exemplo_4_comparacao():
    """Compara resultados de mock vs OpenAI (se disponível)"""
    
    print("\n" + "=" * 70)
    logger.info("EXEMPLO 4: Comparação Mock vs Real")
    print("=" * 70)
    
    context = {
        "origem": "operator_chat",
        "tipo_consulta": "estoque",
        "dados_estoque": {
            "produto": "Ração Premium 15kg",
            "quantidade_atual": 5,
            "quantidade_minima": 10,
            "ultima_venda": "2024-01-20"
        }
    }
    
    objetivo = "Analisar situação do estoque e recomendar ação"
    
    # 1. Resposta com Mock
    logger.info("\n🤖 Mock Provider:")
    print("-" * 70)
    
    # Forçar mock temporariamente
    from backend.app.ai.providers import ProviderFactory, ProviderType
    ProviderFactory.reset()
    
    engine_mock = AIEngine(enable_cost_control=False)
    response_mock = await engine_mock.generate_response(
        context=context,
        objetivo=objetivo,
        tenant_id=1
    )
    
    logger.info(f"Resposta: {response_mock.resposta}")
    logger.info(f"Tokens: {response_mock.metadata.get('tokens', 0)}")
    logger.info(f"Custo: ${response_mock.metadata.get('cost_usd', 0):.4f}")
    logger.info(f"Latência: {response_mock.metadata.get('latency_ms', 0)}ms")
    
    # 2. Resposta com OpenAI (se configurado)
    if AISettings.PROVIDER == ProviderType.OPENAI and AISettings.OPENAI_API_KEY:
        logger.info("\n🧠 OpenAI Provider:")
        print("-" * 70)
        
        ProviderFactory.reset()
        engine_openai = AIEngine(enable_cost_control=True)
        
        try:
            response_openai = await engine_openai.generate_response(
                context=context,
                objetivo=objetivo,
                tenant_id=1
            )
            
            logger.info(f"Resposta: {response_openai.resposta}")
            logger.info(f"Modelo: {response_openai.metadata.get('model', 'N/A')}")
            logger.info(f"Tokens: {response_openai.metadata.get('tokens', 0)}")
            logger.info(f"Custo: ${response_openai.metadata.get('cost_usd', 0):.4f}")
            logger.info(f"Latência: {response_openai.metadata.get('latency_ms', 0)}ms")
            
        except Exception as e:
            logger.info(f"⚠️ Erro ao usar OpenAI: {e}")
    else:
        logger.info("\n⚠️ OpenAI não configurado (defina AI_PROVIDER=openai e OPENAI_API_KEY)")


# ============================================================================
# EXEMPLO 5: Múltiplas Requisições (Rate Limit)
# ============================================================================

async def exemplo_5_multiplas_requisicoes():
    """Testa comportamento com múltiplas requisições"""
    
    print("\n" + "=" * 70)
    logger.info("EXEMPLO 5: Múltiplas Requisições")
    print("=" * 70)
    
    engine = AIEngineFactory.create_production_engine()
    tenant_id = 1
    
    logger.info(f"\n🔄 Processando 5 requisições sequenciais...")
    
    for i in range(5):
        context = {
            "origem": "operator_chat",
            "numero_requisicao": i + 1
        }
        
        try:
            response = await engine.generate_response(
                context=context,
                objetivo=f"Requisição {i + 1} de teste",
                tenant_id=tenant_id
            )
            
            logger.info(f"\n   ✅ Requisição {i + 1}:")
            logger.info(f"      Tokens: {response.metadata.get('tokens', 0)}")
            logger.info(f"      Custo: ${response.metadata.get('cost_usd', 0):.4f}")
            logger.info(f"      Latência: {response.metadata.get('latency_ms', 0)}ms")
            
        except Exception as e:
            logger.info(f"\n   ❌ Requisição {i + 1} falhou: {e}")
    
    # Resumo final
    cost_controller = get_cost_controller()
    summary = cost_controller.get_usage_summary(tenant_id)
    
    logger.info(f"\n📊 Resumo Final:")
    logger.info(f"   Total de requisições: {summary['request_count']}")
    logger.info(f"   Total de tokens: {summary['total_tokens']}")
    logger.info(f"   Custo total: ${summary['total_cost']:.4f}")
    logger.info(f"   Uso do limite: {summary['usage_percent']:.1f}%")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Executa todos os exemplos"""
    
    print("\n" + "=" * 70)
    logger.info("🚀 EXEMPLOS DE INTEGRAÇÃO OPENAI")
    print("=" * 70)
    
    # Exibir configuração atual
    logger.info(f"\n⚙️ Configuração Atual:")
    logger.info(f"   Provider: {AISettings.PROVIDER.value}")
    logger.info(f"   Modelo: {AISettings.OPENAI_MODEL}")
    logger.info(f"   Max Tokens: {AISettings.MAX_TOKENS}")
    logger.info(f"   Timeout: {AISettings.TIMEOUT_SECONDS}s")
    logger.info(f"   Limite Diário: ${AISettings.DAILY_COST_LIMIT_USD:.2f}")
    logger.info(f"   Fallback: {AISettings.ENABLE_FALLBACK}")
    
    if AISettings.PROVIDER == ProviderType.OPENAI:
        api_key = AISettings.OPENAI_API_KEY
        logger.info(f"   API Key: {'Configurada ✅' if api_key else 'NÃO configurada ❌'}")
    
    # Executar exemplos
    await exemplo_1_uso_basico()
    await exemplo_2_controle_custo()
    await exemplo_3_fallback()
    await exemplo_4_comparacao()
    await exemplo_5_multiplas_requisicoes()
    
    print("\n" + "=" * 70)
    logger.info("✅ Todos os exemplos executados!")
    logger.info("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
