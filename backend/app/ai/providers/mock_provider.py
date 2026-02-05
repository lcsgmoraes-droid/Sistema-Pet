"""
Mock Provider - Provider Mock para Desenvolvimento

Provider simulado que não consome APIs externas.
Útil para desenvolvimento, testes e fallback.

CARACTERÍSTICAS:
- Sem custo
- Resposta instantânea
- Determin

ístico
- Sempre disponível
"""

import logging
import time
from typing import Dict, Any

from .base import (
    IAIProvider,
    ProviderType,
    ProviderRequest,
    ProviderResponse,
)


logger = logging.getLogger(__name__)


class MockAIProvider(IAIProvider):
    """
    Provider mock que simula respostas de IA.
    
    Não consome APIs externas. Útil para:
    - Desenvolvimento
    - Testes
    - Fallback quando IA real falha
    """
    
    def __init__(self):
        """Inicializa o provider mock"""
        logger.info("[MockAIProvider] Inicializado")
    
    @property
    def provider_type(self) -> ProviderType:
        """Retorna tipo do provider"""
        return ProviderType.MOCK
    
    @property
    def is_available(self) -> bool:
        """Mock está sempre disponível"""
        return True
    
    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        """
        Gera resposta mock.
        
        Args:
            request: Request padronizado
            
        Returns:
            ProviderResponse simulado
        """
        start_time = time.time()
        
        logger.info(
            f"[MockAIProvider] Gerando resposta mock para tenant {request.tenant_id}"
        )
        
        # Simular pequeno delay (10-50ms)
        await self._simulate_delay()
        
        # Gerar resposta baseada no prompt
        texto = self._generate_mock_response(request.prompt, request.metadata)
        
        # Calcular latência
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Estimar tokens (simplificado: ~4 chars = 1 token)
        prompt_tokens = len(request.prompt) // 4
        completion_tokens = len(texto) // 4
        total_tokens = prompt_tokens + completion_tokens
        
        return ProviderResponse(
            texto=texto,
            provider_type=ProviderType.MOCK,
            model_used="mock-v1",
            tokens_used=total_tokens,
            cost_estimate=0.0,  # Mock não tem custo
            latency_ms=latency_ms,
            metadata={
                **request.metadata,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "mode": "mock"
            },
            fallback_used=False
        )
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Mock não tem custo"""
        return 0.0
    
    def get_max_tokens_limit(self) -> int:
        """Mock suporta até 10000 tokens"""
        return 10000
    
    async def _simulate_delay(self):
        """Simula pequeno delay para realismo"""
        import asyncio
        await asyncio.sleep(0.02)  # 20ms
    
    def _generate_mock_response(self, prompt: str, metadata: Dict[str, Any]) -> str:
        """
        Gera resposta mock baseada no prompt.
        
        Args:
            prompt: Prompt recebido
            metadata: Metadados da requisição
            
        Returns:
            Resposta simulada
        """
        # Detectar origem da requisição
        origem = metadata.get("origem", "desconhecida")
        
        # Respostas específicas por origem
        if origem == "operator_chat":
            return self._generate_operator_chat_response(prompt, metadata)
        elif origem == "pdv":
            return self._generate_pdv_response(prompt, metadata)
        elif origem == "insight_explainer":
            return self._generate_insight_response(prompt, metadata)
        else:
            return self._generate_generic_response(prompt)
    
    def _generate_operator_chat_response(
        self,
        prompt: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Resposta mock para operator chat"""
        intencao = metadata.get("intencao", "generica")
        
        responses = {
            "cliente": (
                "Baseado no histórico do cliente, identifico um padrão de compras "
                "consistente nas categorias mencionadas. Recomendo manter o "
                "relacionamento e oferecer produtos complementares."
            ),
            "produto": (
                "Este produto tem boa aceitação no mercado. Considere destacar "
                "suas características principais e oferecer produtos complementares "
                "para aumentar o ticket médio."
            ),
            "kit": (
                "Identifico oportunidade de kit. Os produtos selecionados são "
                "frequentemente comprados juntos. Um kit poderia proporcionar "
                "economia de 10-15% para o cliente."
            ),
            "venda": (
                "A venda está progredindo bem. Recomendo verificar se há produtos "
                "complementares que agregariam valor ao cliente."
            ),
        }
        
        return responses.get(
            intencao,
            "Analisando sua pergunta, posso fornecer orientações baseadas "
            "nos dados disponíveis. Como posso ajudar especificamente?"
        )
    
    def _generate_pdv_response(self, prompt: str, metadata: Dict[str, Any]) -> str:
        """Resposta mock para PDV"""
        return (
            "Sugestão: Baseado na análise da venda atual, identifiquei "
            "oportunidades de produtos complementares que poderiam interessar "
            "ao cliente. Considere oferecer kits ou produtos relacionados."
        )
    
    def _generate_insight_response(
        self,
        prompt: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Resposta mock para insight explainer"""
        return (
            "Este insight foi gerado com base na análise de padrões históricos "
            "e eventos recentes do sistema. Os dados indicam uma oportunidade "
            "que merece atenção prioritária."
        )
    
    def _generate_generic_response(self, prompt: str) -> str:
        """Resposta mock genérica"""
        # Análise básica do prompt
        prompt_lower = prompt.lower()
        
        if "cliente" in prompt_lower:
            return (
                "Baseado nos dados do cliente, posso fornecer insights sobre "
                "histórico de compras, padrões de comportamento e oportunidades "
                "de relacionamento."
            )
        elif "produto" in prompt_lower:
            return (
                "Analisando os produtos mencionados, posso fornecer informações "
                "sobre desempenho, complementos e oportunidades de venda."
            )
        elif "venda" in prompt_lower:
            return (
                "Sobre a venda em questão, posso analisar o contexto atual e "
                "sugerir ações para otimizar o resultado."
            )
        else:
            return (
                "Entendo sua pergunta. Com base nos dados disponíveis, posso "
                "fornecer análise contextualizada e sugestões práticas."
            )
