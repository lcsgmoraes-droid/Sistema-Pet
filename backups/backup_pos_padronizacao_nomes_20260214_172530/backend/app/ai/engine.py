"""
AIEngine - Motor de IA

Motor responsável por gerar respostas baseadas em contexto estruturado.
Usa sistema de providers plugável (mock, OpenAI, Anthropic).
"""

from typing import Dict, Any, List
from datetime import datetime
import logging

from app.ai.contracts import IAIEngine, AIResponse, AIContext
from app.ai.prompt_builder import AIPromptBuilder
from app.ai.providers import (
    get_provider,
    ProviderRequest,
    ProviderException,
    ProviderTimeoutException,
    ProviderRateLimitException,
    ProviderCostLimitException,
    MockAIProvider
)
from app.ai.settings import AISettings
from app.ai.cost_control import get_cost_controller


logger = logging.getLogger(__name__)


class AIEngine(IAIEngine):
    """
    Motor de IA com sistema de providers.
    
    Usa providers plugáveis (mock, OpenAI, Anthropic) com:
    - Controle de custo por tenant
    - Fallback automático para mock
    - Timeout configurável
    - Auditoria completa
    """
    
    def __init__(
        self,
        prompt_builder: AIPromptBuilder = None,
        enable_cost_control: bool = True
    ):
        """
        Inicializa o motor de IA.
        
        Args:
            prompt_builder: Construtor de prompts (opcional)
            enable_cost_control: Habilita controle de custo
        """
        self.prompt_builder = prompt_builder or AIPromptBuilder()
        self.enable_cost_control = enable_cost_control
        
        # Obter cost controller se habilitado
        self.cost_controller = get_cost_controller() if enable_cost_control else None
        
        logger.info(
            f"[AIEngine] Inicializado com provider: {AISettings.PROVIDER.value}, "
            f"Controle de custo: {enable_cost_control}"
        )
    
    async def generate_response(
        self,
        context: Dict[str, Any],
        objetivo: str,
        tenant_id: int
    ) -> AIResponse:
        """
        Gera uma resposta baseada no contexto.
        
        Args:
            context: Dados estruturados (NÃO faz queries no banco)
            objetivo: O que o usuário quer saber
            tenant_id: ID do tenant (multi-tenant)
            
        Returns:
            AIResponse estruturado e auditável
        """
        # Log da operação
        logger.info(f"[AIEngine] Gerando resposta para tenant {tenant_id}")
        logger.debug(f"[AIEngine] Objetivo: {objetivo}")
        
        # Verificar limite de custo (se habilitado)
        if self.cost_controller:
            # Estimativa inicial conservadora (assumir GPT-4)
            estimated_tokens = AISettings.MAX_TOKENS
            estimated_cost = (estimated_tokens / 1000) * AISettings.OPENAI_GPT4_PRICE_PER_1K_OUTPUT
            
            can_proceed, reason = self.cost_controller.check_can_proceed(
                tenant_id, estimated_tokens, estimated_cost
            )
            if not can_proceed:
                logger.warning(f"[AIEngine] Limite de custo excedido para tenant {tenant_id}: {reason}")
                # Retornar resposta de erro
                return AIResponse(
                    resposta=f"⚠️ Limite de uso diário excedido. {reason}",
                    explicacao="O limite diário de consultas à IA foi atingido. Tente novamente amanhã.",
                    fonte_dados="Sistema de Controle de Custo",
                    confianca=1.0,
                    timestamp=datetime.now(),
                    tenant_id=tenant_id,
                    metadata={
                        "error": "cost_limit_exceeded",
                        "reason": reason,
                    }
                )
        
        # Construir o prompt
        prompt = self.prompt_builder.build_prompt(context, objetivo)
        
        # Tentar com provider configurado
        try:
            return await self._generate_with_provider(
                prompt=prompt,
                context=context,
                objetivo=objetivo,
                tenant_id=tenant_id
            )
        
        except (ProviderException, ProviderTimeoutException, ProviderRateLimitException) as e:
            logger.error(f"[AIEngine] Erro no provider: {e}")
            
            # Se fallback habilitado, usar mock
            if AISettings.ENABLE_FALLBACK:
                logger.info("[AIEngine] Usando fallback para MockProvider")
                return await self._generate_with_fallback(
                    prompt=prompt,
                    context=context,
                    objetivo=objetivo,
                    tenant_id=tenant_id,
                    original_error=str(e)
                )
            else:
                # Re-lançar exceção se fallback desabilitado
                raise
    
    async def _generate_with_provider(
        self,
        prompt: str,
        context: Dict[str, Any],
        objetivo: str,
        tenant_id: int
    ) -> AIResponse:
        """
        Gera resposta usando provider configurado.
        
        Args:
            prompt: Prompt construído
            context: Contexto original
            objetivo: Objetivo da consulta
            tenant_id: ID do tenant
            
        Returns:
            AIResponse do provider
        """
        # Obter provider
        provider = get_provider()
        
        logger.debug(f"[AIEngine] Usando provider: {provider.provider_type.value}")
        
        # Preparar request
        request = ProviderRequest(
            prompt=prompt,
            tenant_id=tenant_id,
            max_tokens=AISettings.MAX_TOKENS,
            temperature=AISettings.TEMPERATURE,
            timeout_seconds=AISettings.TIMEOUT_SECONDS,
            metadata={
                "objetivo": objetivo,
                "origem": context.get("origem", "unknown"),
                "prompt_version": AISettings.DEFAULT_PROMPT_VERSION,
            }
        )
        
        # Gerar resposta
        provider_response = await provider.generate(request)
        
        # Registrar custo (se habilitado)
        if self.cost_controller:
            self.cost_controller.record_usage(
                tenant_id=tenant_id,
                tokens_used=provider_response.tokens_used,
                cost_usd=provider_response.cost_estimate
            )
        
        # Converter para AIResponse
        return self._convert_provider_response(
            provider_response=provider_response,
            context=context,
            tenant_id=tenant_id
        )
    
    async def _generate_with_fallback(
        self,
        prompt: str,
        context: Dict[str, Any],
        objetivo: str,
        tenant_id: int,
        original_error: str
    ) -> AIResponse:
        """
        Gera resposta usando fallback (MockProvider).
        
        Args:
            prompt: Prompt construído
            context: Contexto original
            objetivo: Objetivo da consulta
            tenant_id: ID do tenant
            original_error: Erro original do provider
            
        Returns:
            AIResponse do mock com indicação de fallback
        """
        logger.warning(f"[AIEngine] Usando fallback devido a erro: {original_error}")
        
        # Criar mock provider
        mock_provider = MockAIProvider()
        
        # Preparar request
        request = ProviderRequest(
            prompt=prompt,
            tenant_id=tenant_id,
            max_tokens=AISettings.MAX_TOKENS,
            temperature=AISettings.TEMPERATURE,
            timeout_seconds=AISettings.TIMEOUT_SECONDS,
            metadata={
                "objetivo": objetivo,
                "origem": context.get("origem", "unknown"),
                "prompt_version": AISettings.DEFAULT_PROMPT_VERSION,
                "fallback": True,
                "original_error": original_error,
            }
        )
        
        # Gerar resposta mock
        provider_response = await mock_provider.generate(request)
        
        # Converter para AIResponse
        ai_response = self._convert_provider_response(
            provider_response=provider_response,
            context=context,
            tenant_id=tenant_id
        )
        
        # Adicionar aviso de fallback na resposta
        ai_response.metadata["fallback_used"] = True
        ai_response.metadata["original_provider_error"] = original_error
        
        return ai_response
    
    def _convert_provider_response(
        self,
        provider_response,
        context: Dict[str, Any],
        tenant_id: int
    ) -> AIResponse:
        """
        Converte ProviderResponse em AIResponse.
        
        Args:
            provider_response: Resposta do provider
            context: Contexto original
            tenant_id: ID do tenant
            
        Returns:
            AIResponse formatado
        """
        # Extrair fonte de dados e confiança do contexto
        fonte_dados = self._extract_data_sources(context)
        confianca = self._calculate_confidence_mock(context)
        
        return AIResponse(
            resposta=provider_response.texto,
            explicacao=f"Resposta gerada por {provider_response.provider_type.value} usando {provider_response.model_used}",
            fonte_dados=", ".join(fonte_dados),
            confianca=confianca,
            timestamp=datetime.now(),
            tenant_id=tenant_id,
            metadata={
                **provider_response.metadata,
                "provider": provider_response.provider_type.value,
                "model": provider_response.model_used,
                "tokens": provider_response.tokens_used,
                "cost_usd": provider_response.cost_estimate,
                "latency_ms": provider_response.latency_ms,
                "fallback_used": provider_response.fallback_used,
            }
        )
    
    async def _generate_mock_response(
        self,
        prompt: str,
        context: Dict[str, Any],
        objetivo: str,
        tenant_id: int
    ) -> AIResponse:
        """
        Gera uma resposta mock para testes.
        
        Args:
            prompt: Prompt construído
            context: Contexto original
            objetivo: Objetivo da consulta
            tenant_id: ID do tenant
            
        Returns:
            AIResponse mockado
        """
        # Analisa o contexto para gerar resposta relevante
        resposta = self._analyze_context_mock(context, objetivo)
        explicacao = self._generate_explanation_mock(context, objetivo)
        fonte_dados = self._extract_data_sources(context)
        confianca = self._calculate_confidence_mock(context)
        
        return AIResponse(
            resposta=resposta,
            explicacao=explicacao,
            fonte_dados=fonte_dados,
            confianca=confianca,
            timestamp=datetime.now(),
            tenant_id=tenant_id,
            metadata={
                "prompt_length": len(prompt),
                "context_keys": list(context.keys()),
                "mode": "mock",
                "objetivo": objetivo
            }
        )
    
    def _analyze_context_mock(
        self,
        context: Dict[str, Any],
        objetivo: str
    ) -> str:
        """
        Analisa o contexto e gera uma resposta mock relevante.
        
        Args:
            context: Contexto estruturado
            objetivo: Objetivo da consulta
            
        Returns:
            Resposta em linguagem natural
        """
        # Identifica o tipo de contexto
        if "tipo_insight" in context:
            insight_type = context.get("tipo_insight", "")
            dados = context.get("dados_insight", {})
            
            # Resposta específica para insights
            if "ClienteRecorrente" in insight_type:
                cliente = dados.get("cliente_nome", "Cliente")
                valor = dados.get("valor_devido", 0)
                dias = dados.get("dias_atraso", 0)
                
                return (
                    f"Identifiquei que o cliente {cliente} é um cliente recorrente "
                    f"com {dias} dias de atraso no valor de R$ {valor:.2f}. "
                    f"Recomendo entrar em contato prioritariamente, pois clientes "
                    f"recorrentes têm maior probabilidade de regularização."
                )
        
        # Resposta genérica
        return (
            "Analisando o contexto fornecido, identifiquei os principais pontos "
            "relevantes para sua consulta. A situação requer atenção e "
            "acompanhamento próximo."
        )
    
    def _generate_explanation_mock(
        self,
        context: Dict[str, Any],
        objetivo: str
    ) -> str:
        """
        Gera explicação de como a conclusão foi alcançada.
        
        Args:
            context: Contexto estruturado
            objetivo: Objetivo da consulta
            
        Returns:
            Explicação do raciocínio
        """
        fonte_dados = self._extract_data_sources(context)
        
        return (
            f"Esta análise foi baseada em {len(fonte_dados)} fonte(s) de dados: "
            f"{', '.join(fonte_dados)}. "
            f"Considerei o objetivo '{objetivo}' e processei os dados estruturados "
            f"fornecidos para gerar insights acionáveis."
        )
    
    def _extract_data_sources(self, context: Dict[str, Any]) -> List[str]:
        """
        Extrai as fontes de dados do contexto.
        
        Args:
            context: Contexto estruturado
            
        Returns:
            Lista de fontes de dados
        """
        sources = []
        
        # Identifica fontes baseado nas chaves do contexto
        if "tipo_insight" in context:
            sources.append(f"Insight:{context['tipo_insight']}")
        
        if "dados_insight" in context:
            sources.append("ReadModel:Insights")
        
        if "read_models" in context:
            for rm in context["read_models"]:
                sources.append(f"ReadModel:{rm}")
        
        if not sources:
            sources = ["ContextoEstruturado"]
        
        return sources
    
    def _calculate_confidence_mock(self, context: Dict[str, Any]) -> float:
        """
        Calcula o nível de confiança da resposta (mock).
        
        Futuramente pode usar análise mais sofisticada.
        
        Args:
            context: Contexto estruturado
            
        Returns:
            Confiança entre 0.0 e 1.0
        """
        # Lógica simples: mais dados = maior confiança
        num_keys = len(context)
        
        if num_keys >= 5:
            return 0.9
        elif num_keys >= 3:
            return 0.75
        elif num_keys >= 1:
            return 0.6
        else:
            return 0.4
    
    async def generate_response_from_ai_context(
        self,
        ai_context: AIContext
    ) -> AIResponse:
        """
        Gera resposta a partir de um AIContext estruturado.
        
        Args:
            ai_context: Contexto estruturado
            
        Returns:
            AIResponse
        """
        return await self.generate_response(
            context=ai_context.dados_estruturados,
            objetivo=ai_context.objetivo,
            tenant_id=ai_context.tenant_id
        )


class AIEngineFactory:
    """
    Factory para criação de instâncias de AIEngine.
    
    Facilita testes e permite trocar implementações facilmente.
    """
    
    @staticmethod
    def create_mock_engine() -> AIEngine:
        """
        Cria um motor de IA em modo mock.
        
        Returns:
            AIEngine configurado para mock (sem controle de custo)
        """
        return AIEngine(
            prompt_builder=AIPromptBuilder(),
            enable_cost_control=False  # Mock não precisa controle de custo
        )
    
    @staticmethod
    def create_production_engine() -> AIEngine:
        """
        Cria um motor de IA para produção.
        
        Usa provider configurado em AISettings.PROVIDER com controle de custo.
        
        Returns:
            AIEngine configurado para produção
        """
        logger.info(
            f"[AIEngineFactory] Criando engine de produção com provider: {AISettings.PROVIDER.value}"
        )
        return AIEngine(
            prompt_builder=AIPromptBuilder(),
            enable_cost_control=True  # Produção usa controle de custo
        )
