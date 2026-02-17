"""
Providers - Sistema plugável de IA

Permite trocar entre diferentes providers (mock, OpenAI, Anthropic) via ENV.
"""

from .base import (
    IAIProvider,
    ProviderType,
    ProviderRequest,
    ProviderResponse,
    ProviderException,
    ProviderTimeoutException,
    ProviderRateLimitException,
    ProviderCostLimitException,
    ProviderAuthException,
)
from .mock_provider import MockAIProvider
from .openai_provider import OpenAIProvider
from .factory import ProviderFactory, get_provider


__all__ = [
    # Base
    "IAIProvider",
    "ProviderType",
    "ProviderRequest",
    "ProviderResponse",
    
    # Exceções
    "ProviderException",
    "ProviderTimeoutException",
    "ProviderRateLimitException",
    "ProviderCostLimitException",
    "ProviderAuthException",
    
    # Providers
    "MockAIProvider",
    "OpenAIProvider",
    
    # Factory
    "ProviderFactory",
    "get_provider",
]
