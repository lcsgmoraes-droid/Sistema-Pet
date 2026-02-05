"""
OpenAI Provider - Integração com OpenAI

Provider real que consome a API da OpenAI.

REQUISITOS:
- openai package instalado
- OPENAI_API_KEY configurada

CARACTERÍSTICAS:
- Suporte a GPT-4 e GPT-3.5
- Controle de custo
- Timeout configurável
- Retry automático
"""

import logging
import time
import asyncio
from typing import Optional

from .base import (
    IAIProvider,
    ProviderType,
    ProviderRequest,
    ProviderResponse,
    ProviderException,
    ProviderTimeoutException,
    ProviderRateLimitException,
    ProviderAuthException,
)
from app.ai.settings import AISettings


logger = logging.getLogger(__name__)


# Importação condicional do OpenAI
try:
    import openai
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning(
        "[OpenAIProvider] Package 'openai' não instalado. "
        "Instale com: pip install openai"
    )


class OpenAIProvider(IAIProvider):
    """
    Provider que integra com a API da OpenAI.
    
    Suporta GPT-4 e GPT-3.5 com controle de custo e timeout.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = None,
        max_retries: int = 2
    ):
        """
        Inicializa o provider OpenAI.
        
        Args:
            api_key: Chave da API (usa settings se None)
            model: Modelo a usar (usa settings se None)
            max_retries: Número máximo de tentativas
        """
        self.api_key = api_key or AISettings.OPENAI_API_KEY
        self.model = model or AISettings.OPENAI_MODEL
        self.max_retries = max_retries
        
        # Cliente OpenAI
        self.client: Optional[AsyncOpenAI] = None
        
        if OPENAI_AVAILABLE and self.api_key:
            try:
                self.client = AsyncOpenAI(api_key=self.api_key)
                logger.info(
                    f"[OpenAIProvider] Inicializado com modelo {self.model}"
                )
            except Exception as e:
                logger.error(f"[OpenAIProvider] Erro ao inicializar: {e}")
                self.client = None
        else:
            logger.warning(
                "[OpenAIProvider] Não inicializado (falta API key ou package)"
            )
    
    @property
    def provider_type(self) -> ProviderType:
        """Retorna tipo do provider"""
        return ProviderType.OPENAI
    
    @property
    def is_available(self) -> bool:
        """Verifica se está disponível"""
        return (
            OPENAI_AVAILABLE
            and self.client is not None
            and self.api_key is not None
        )
    
    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        """
        Gera resposta usando OpenAI.
        
        Args:
            request: Request padronizado
            
        Returns:
            ProviderResponse com resposta da OpenAI
            
        Raises:
            ProviderException: Em caso de erro
        """
        if not self.is_available:
            raise ProviderException(
                "OpenAI provider não está disponível (verifique API key)",
                provider_type=ProviderType.OPENAI
            )
        
        start_time = time.time()
        
        logger.info(
            f"[OpenAIProvider] Gerando resposta para tenant {request.tenant_id} "
            f"usando {self.model}"
        )
        
        try:
            # Fazer chamada à API com timeout
            response = await asyncio.wait_for(
                self._call_openai_api(request),
                timeout=request.timeout_seconds
            )
            
            # Calcular latência
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extrair dados da resposta
            texto = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            
            # Calcular custo
            cost = self._calculate_cost(prompt_tokens, completion_tokens)
            
            logger.info(
                f"[OpenAIProvider] Resposta gerada - "
                f"Tokens: {tokens_used}, Custo: ${cost:.4f}, "
                f"Latência: {latency_ms}ms"
            )
            
            return ProviderResponse(
                texto=texto,
                provider_type=ProviderType.OPENAI,
                model_used=self.model,
                tokens_used=tokens_used,
                cost_estimate=cost,
                latency_ms=latency_ms,
                metadata={
                    **request.metadata,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "finish_reason": response.choices[0].finish_reason,
                },
                fallback_used=False
            )
        
        except asyncio.TimeoutError:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[OpenAIProvider] Timeout após {latency_ms}ms "
                f"(limite: {request.timeout_seconds}s)"
            )
            raise ProviderTimeoutException(
                f"Timeout após {request.timeout_seconds}s",
                provider_type=ProviderType.OPENAI
            )
        
        except openai.RateLimitError as e:
            logger.error(f"[OpenAIProvider] Rate limit excedido: {e}")
            raise ProviderRateLimitException(
                "Rate limit da OpenAI excedido",
                provider_type=ProviderType.OPENAI,
                original_error=e
            )
        
        except openai.AuthenticationError as e:
            logger.error(f"[OpenAIProvider] Erro de autenticação: {e}")
            raise ProviderAuthException(
                "API key inválida ou expirada",
                provider_type=ProviderType.OPENAI,
                original_error=e
            )
        
        except Exception as e:
            logger.error(f"[OpenAIProvider] Erro inesperado: {e}", exc_info=True)
            raise ProviderException(
                f"Erro ao chamar OpenAI: {str(e)}",
                provider_type=ProviderType.OPENAI,
                original_error=e
            )
    
    async def _call_openai_api(self, request: ProviderRequest):
        """
        Faz chamada à API da OpenAI.
        
        Args:
            request: Request padronizado
            
        Returns:
            Resposta da API OpenAI
        """
        messages = [
            {
                "role": "system",
                "content": "Você é um assistente especializado em análise de dados de Pet Shop."
            },
            {
                "role": "user",
                "content": request.prompt
            }
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        
        return response
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calcula custo da operação.
        
        Args:
            prompt_tokens: Tokens do prompt
            completion_tokens: Tokens da resposta
            
        Returns:
            Custo em USD
        """
        if "gpt-4" in self.model.lower():
            input_cost = (prompt_tokens / 1000) * AISettings.OPENAI_GPT4_PRICE_PER_1K_INPUT
            output_cost = (completion_tokens / 1000) * AISettings.OPENAI_GPT4_PRICE_PER_1K_OUTPUT
        else:  # GPT-3.5
            input_cost = (prompt_tokens / 1000) * AISettings.OPENAI_GPT35_PRICE_PER_1K_INPUT
            output_cost = (completion_tokens / 1000) * AISettings.OPENAI_GPT35_PRICE_PER_1K_OUTPUT
        
        return input_cost + output_cost
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estima custo de uma operação"""
        return self._calculate_cost(prompt_tokens, completion_tokens)
    
    def get_max_tokens_limit(self) -> int:
        """Retorna limite máximo de tokens"""
        if "gpt-4" in self.model.lower():
            return 8192  # GPT-4
        else:
            return 4096  # GPT-3.5
