"""
Provider Factory - Seleção automática de provider baseado em ENV

OBJETIVO:
Seleciona o provider correto baseado nas configurações (AISettings.PROVIDER).

PROVIDERS SUPORTADOS:
- mock: MockAIProvider (sempre disponível)
- openai: OpenAIProvider (requer API key)
- anthropic: AnthropicProvider (futuro)

FALLBACK:
Se o provider configurado não estiver disponível, retorna MockAIProvider.
"""

import logging
from typing import Optional

from .base import IAIProvider, ProviderType
from .mock_provider import MockAIProvider
from .openai_provider import OpenAIProvider
from app.ai.settings import AISettings


logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory para criação de providers.
    
    Seleciona provider baseado em ENV (AISettings.PROVIDER).
    """
    
    _instance: Optional[IAIProvider] = None
    _provider_type: Optional[ProviderType] = None
    
    @classmethod
    def create_provider(
        cls,
        provider_type: Optional[ProviderType] = None,
        force_recreate: bool = False
    ) -> IAIProvider:
        """
        Cria provider baseado nas configurações.
        
        Args:
            provider_type: Tipo do provider (usa AISettings.PROVIDER se None)
            force_recreate: Força recriação do provider
            
        Returns:
            Provider configurado (ou mock em caso de fallback)
        """
        # Usar configuração se não especificado
        if provider_type is None:
            provider_type = AISettings.PROVIDER
        
        # Retornar instância em cache se disponível
        if not force_recreate and cls._instance is not None and cls._provider_type == provider_type:
            logger.debug(f"[ProviderFactory] Retornando provider em cache: {provider_type.value}")
            return cls._instance
        
        logger.info(f"[ProviderFactory] Criando provider: {provider_type.value}")
        
        # Criar provider baseado no tipo
        provider = cls._create_provider_instance(provider_type)
        
        # Validar se está disponível
        if not provider.is_available:
            logger.warning(
                f"[ProviderFactory] Provider {provider_type.value} não está disponível. "
                "Usando fallback para MockAIProvider."
            )
            if AISettings.ENABLE_FALLBACK:
                provider = MockAIProvider()
            else:
                raise RuntimeError(
                    f"Provider {provider_type.value} não está disponível e fallback está desabilitado"
                )
        
        # Cachear provider
        cls._instance = provider
        cls._provider_type = provider_type
        
        logger.info(
            f"[ProviderFactory] Provider criado com sucesso: "
            f"{provider.provider_type.value}"
        )
        
        return provider
    
    @classmethod
    def _create_provider_instance(cls, provider_type: ProviderType) -> IAIProvider:
        """
        Cria instância do provider.
        
        Args:
            provider_type: Tipo do provider
            
        Returns:
            Instância do provider
        """
        if provider_type == ProviderType.MOCK:
            return MockAIProvider()
        
        elif provider_type == ProviderType.OPENAI:
            return OpenAIProvider(
                api_key=AISettings.OPENAI_API_KEY,
                model=AISettings.OPENAI_MODEL
            )
        
        elif provider_type == ProviderType.ANTHROPIC:
            # Futuro: AnthropicProvider
            logger.warning(
                "[ProviderFactory] AnthropicProvider ainda não implementado. "
                "Usando MockAIProvider."
            )
            return MockAIProvider()
        
        else:
            logger.error(f"[ProviderFactory] Tipo de provider desconhecido: {provider_type}")
            return MockAIProvider()
    
    @classmethod
    def get_current_provider(cls) -> Optional[IAIProvider]:
        """
        Retorna provider atual em cache.
        
        Returns:
            Provider em cache ou None
        """
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reseta cache do provider"""
        logger.info("[ProviderFactory] Resetando cache de provider")
        cls._instance = None
        cls._provider_type = None


def get_provider() -> IAIProvider:
    """
    Função de conveniência para obter provider.
    
    Returns:
        Provider configurado
    """
    return ProviderFactory.create_provider()
