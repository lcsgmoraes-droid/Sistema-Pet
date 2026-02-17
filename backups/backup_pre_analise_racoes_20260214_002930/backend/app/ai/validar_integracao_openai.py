"""
Script de Validação - Integração OpenAI

Testa todas as funcionalidades do sistema de providers.

COMO USAR:
    python validar_integracao_openai.py
"""

import asyncio
import os
import sys
from typing import List, Tuple
from pathlib import Path
from app.utils.logger import logger

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

# Configurar para usar mock nos testes
os.environ["AI_PROVIDER"] = "mock"
os.environ["ENABLE_FALLBACK"] = "true"
os.environ["MAX_TOKENS"] = "300"
os.environ["DAILY_COST_LIMIT_USD"] = "5.00"


# ============================================================================
# TESTES
# ============================================================================

async def teste_1_importacoes() -> Tuple[bool, str]:
    """Testa se todas as importações estão corretas"""
    try:
        from app.ai.providers import (
            IAIProvider,
            ProviderType,
            ProviderRequest,
            ProviderResponse,
            MockAIProvider,
            OpenAIProvider,
            ProviderFactory,
            get_provider,
        )
        from app.ai.settings import AISettings
        from app.ai.cost_control import get_cost_controller
        from app.ai.engine import AIEngine, AIEngineFactory
        
        return True, "Todas as importações OK"
    except Exception as e:
        return False, f"Erro nas importações: {e}"


async def teste_2_settings() -> Tuple[bool, str]:
    """Testa configurações"""
    try:
        from app.ai.settings import AISettings, AIProviderType
        
        # Verificar que as settings foram carregadas
        assert hasattr(AISettings, "PROVIDER")
        assert hasattr(AISettings, "MAX_TOKENS")
        assert hasattr(AISettings, "TIMEOUT_SECONDS")
        assert hasattr(AISettings, "DAILY_COST_LIMIT_USD")
        assert hasattr(AISettings, "ENABLE_FALLBACK")
        
        # Verificar que validate() existe e retorna algo
        result = AISettings.validate()
        
        return True, f"Configurações OK (provider: {AISettings.PROVIDER.value})"
    except AssertionError as e:
        return False, f"Assertion falhou: {e}"
    except Exception as e:
        return False, f"Erro nas configurações: {e}"
        return False, f"Erro nas configurações: {e}"


async def teste_3_mock_provider() -> Tuple[bool, str]:
    """Testa MockProvider"""
    try:
        from app.ai.providers import MockAIProvider, ProviderRequest, ProviderType
        
        # Criar provider
        provider = MockAIProvider()
        
        # Verificar disponibilidade
        assert provider.is_available is True
        assert provider.provider_type == ProviderType.MOCK
        
        # Fazer request
        request = ProviderRequest(
            prompt="Teste de mock",
            tenant_id=1,
            max_tokens=100,
            temperature=0.7,
            timeout_seconds=5,
            metadata={"origem": "teste"}
        )
        
        response = await provider.generate(request)
        
        # Validar response
        assert response.provider_type == ProviderType.MOCK
        assert response.texto is not None
        assert len(response.texto) > 0
        assert response.cost_estimate == 0.0
        assert response.latency_ms >= 0
        
        return True, f"MockProvider OK (latência: {response.latency_ms}ms)"
    except Exception as e:
        return False, f"Erro no MockProvider: {e}"


async def teste_4_openai_provider() -> Tuple[bool, str]:
    """Testa OpenAIProvider (sem fazer chamada real)"""
    try:
        from app.ai.providers import OpenAIProvider, ProviderType
        
        # Criar provider sem API key
        provider = OpenAIProvider(api_key=None)
        
        # Verificar tipo
        assert provider.provider_type == ProviderType.OPENAI
        
        # Verificar que não está disponível sem API key
        assert provider.is_available is False
        
        # Verificar limite de tokens
        max_tokens = provider.get_max_tokens_limit()
        assert max_tokens > 0
        
        # Testar estimativa de custo
        cost = provider.estimate_cost(prompt_tokens=100, completion_tokens=50)
        assert cost >= 0.0
        
        return True, f"OpenAIProvider OK (max tokens: {max_tokens})"
    except Exception as e:
        return False, f"Erro no OpenAIProvider: {e}"


async def teste_5_provider_factory() -> Tuple[bool, str]:
    """Testa ProviderFactory"""
    try:
        from app.ai.providers import ProviderFactory, ProviderType
        
        # Resetar factory
        ProviderFactory.reset()
        
        # Criar provider padrão (mock)
        provider = ProviderFactory.create_provider()
        assert provider is not None
        assert provider.is_available is True
        
        # Verificar cache
        provider2 = ProviderFactory.create_provider()
        assert provider2 is provider  # Deve ser mesma instância
        
        # Forçar recriação
        provider3 = ProviderFactory.create_provider(force_recreate=True)
        assert provider3 is not provider  # Deve ser nova instância
        
        return True, f"ProviderFactory OK (tipo: {provider.provider_type.value})"
    except Exception as e:
        return False, f"Erro no ProviderFactory: {e}"


async def teste_6_cost_controller() -> Tuple[bool, str]:
    """Testa CostController"""
    try:
        from app.ai.cost_control import get_cost_controller
        
        controller = get_cost_controller()
        tenant_id = 999
        
        # Verificar antes de qualquer uso (com tokens e custo estimados)
        can_proceed, reason = controller.check_can_proceed(
            tenant_id=tenant_id,
            estimated_tokens=100,
            estimated_cost=0.01
        )
        assert can_proceed is True
        
        # Registrar uso
        controller.record_usage(
            tenant_id=tenant_id,
            tokens_used=100,
            cost_usd=0.01
        )
        
        # Obter resumo
        summary = controller.get_usage_summary(tenant_id)
        assert summary["total_tokens"] == 100
        assert summary["total_cost"] == 0.01
        assert summary["request_count"] == 1
        assert 0.0 <= summary["usage_percent"] <= 100.0
        
        return True, f"CostController OK (uso: {summary['usage_percent']:.1f}%)"
    except Exception as e:
        return False, f"Erro no CostController: {e}"


async def teste_7_engine_basico() -> Tuple[bool, str]:
    """Testa AIEngine básico"""
    try:
        from app.ai.engine import AIEngineFactory
        
        # Criar engine de produção
        engine = AIEngineFactory.create_production_engine()
        
        # Gerar resposta
        context = {
            "origem": "teste",
            "dados": {"teste": True}
        }
        
        response = await engine.generate_response(
            context=context,
            objetivo="Teste básico",
            tenant_id=1
        )
        
        # Validar resposta
        assert response is not None
        assert response.resposta is not None
        assert response.explicacao is not None
        assert response.tenant_id == 1
        assert response.confianca >= 0.0
        assert response.confianca <= 1.0
        
        # Validar metadados
        assert "provider" in response.metadata
        assert "tokens" in response.metadata
        assert "cost_usd" in response.metadata
        
        return True, f"AIEngine OK (provider: {response.metadata['provider']})"
    except Exception as e:
        return False, f"Erro no AIEngine: {e}"


async def teste_8_engine_fallback() -> Tuple[bool, str]:
    """Testa fallback do engine"""
    try:
        from app.ai.engine import AIEngine
        from app.ai.prompt_builder import AIPromptBuilder
        
        # Criar engine com controle de custo
        engine = AIEngine(
            prompt_builder=AIPromptBuilder(),
            enable_cost_control=True
        )
        
        # Gerar resposta (deve funcionar com mock)
        context = {"origem": "teste_fallback"}
        
        response = await engine.generate_response(
            context=context,
            objetivo="Teste de fallback",
            tenant_id=1
        )
        
        # Verificar resposta
        assert response is not None
        
        # Se fallback foi usado, deve estar marcado
        fallback_used = response.metadata.get("fallback_used", False)
        
        return True, f"Fallback OK (usado: {fallback_used})"
    except Exception as e:
        return False, f"Erro no fallback: {e}"


async def teste_9_engine_limite_custo() -> Tuple[bool, str]:
    """Testa limite de custo"""
    try:
        from app.ai.engine import AIEngine
        from app.ai.cost_control import get_cost_controller
        
        # Criar engine
        engine = AIEngine(enable_cost_control=True)
        tenant_id = 998
        
        # Forçar limite excedido
        controller = get_cost_controller()
        controller.record_usage(
            tenant_id=tenant_id,
            tokens_used=1000000,  # Muitos tokens
            cost_usd=100.00  # Custo alto
        )
        
        # Tentar gerar resposta (deve bloquear)
        context = {"origem": "teste_limite"}
        
        response = await engine.generate_response(
            context=context,
            objetivo="Teste de limite",
            tenant_id=tenant_id
        )
        
        # Deve retornar mensagem de erro
        assert "limite" in response.resposta.lower() or "excedido" in response.resposta.lower()
        assert response.metadata.get("error") == "cost_limit_exceeded"
        
        return True, "Limite de custo OK"
    except Exception as e:
        return False, f"Erro no limite de custo: {e}"


async def teste_10_integracao_completa() -> Tuple[bool, str]:
    """Testa integração completa (Engine + Providers + CostControl)"""
    try:
        from app.ai.engine import AIEngineFactory
        from app.ai.cost_control import get_cost_controller
        
        tenant_id = 997
        engine = AIEngineFactory.create_production_engine()
        controller = get_cost_controller()
        
        # Processar 3 requisições
        for i in range(3):
            context = {
                "origem": "teste_integracao",
                "iteracao": i + 1
            }
            
            response = await engine.generate_response(
                context=context,
                objetivo=f"Teste {i + 1}",
                tenant_id=tenant_id
            )
            
            assert response is not None
        
        # Verificar uso acumulado
        summary = controller.get_usage_summary(tenant_id)
        assert summary["request_count"] == 3
        assert summary["total_tokens"] > 0
        
        return True, f"Integração OK (3 requisições, {summary['total_tokens']} tokens)"
    except Exception as e:
        return False, f"Erro na integração: {e}"


# ============================================================================
# EXECUTOR
# ============================================================================

async def executar_testes():
    """Executa todos os testes"""
    
    testes = [
        ("Importações", teste_1_importacoes),
        ("Configurações", teste_2_settings),
        ("MockProvider", teste_3_mock_provider),
        ("OpenAIProvider", teste_4_openai_provider),
        ("ProviderFactory", teste_5_provider_factory),
        ("CostController", teste_6_cost_controller),
        ("AIEngine Básico", teste_7_engine_basico),
        ("Fallback", teste_8_engine_fallback),
        ("Limite de Custo", teste_9_engine_limite_custo),
        ("Integração Completa", teste_10_integracao_completa),
    ]
    
    print("\n" + "=" * 70)
    logger.info("🧪 VALIDAÇÃO - INTEGRAÇÃO OPENAI")
    logger.info("=" * 70 + "\n")
    
    resultados = []
    
    for nome, teste in testes:
        print(f"▶ Testando: {nome}...", end=" ", flush=True)
        
        try:
            sucesso, mensagem = await teste()
            resultados.append((nome, sucesso, mensagem))
            
            if sucesso:
                logger.info(f"✅ {mensagem}")
            else:
                logger.info(f"❌ {mensagem}")
        
        except Exception as e:
            resultados.append((nome, False, f"Exceção: {e}"))
            logger.info(f"❌ Exceção: {e}")
    
    # Resumo
    print("\n" + "=" * 70)
    logger.info("📊 RESUMO")
    logger.info("=" * 70 + "\n")
    
    total = len(resultados)
    sucessos = sum(1 for _, sucesso, _ in resultados if sucesso)
    falhas = total - sucessos
    
    logger.info(f"Total de testes: {total}")
    logger.info(f"✅ Sucessos: {sucessos}")
    logger.info(f"❌ Falhas: {falhas}")
    logger.info(f"Taxa de sucesso: {(sucessos/total)*100:.1f}%")
    
    if falhas > 0:
        logger.info("\n⚠️ Testes com falha:")
        for nome, sucesso, mensagem in resultados:
            if not sucesso:
                logger.info(f"   - {nome}: {mensagem}")
    
    logger.info("\n" + "=" * 70 + "\n")
    
    return falhas == 0


if __name__ == "__main__":
    sucesso = asyncio.run(executar_testes())
    sys.exit(0 if sucesso else 1)
