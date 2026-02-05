"""
Base Provider - Interface para Provedores de IA

Define o contrato que todos os providers (mock, OpenAI, Claude, etc)
devem implementar.

PRINCÍPIOS:
- Plugável e desacoplado
- Auditável
- Com fallback
- Controle de custo
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class ProviderType(Enum):
    """Tipos de providers suportados"""
    MOCK = "mock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"  # Futuro


@dataclass
class ProviderRequest:
    """
    Request padronizado para qualquer provider.
    
    Atributos:
        prompt: Prompt formatado para envio
        tenant_id: ID do tenant (multi-tenant)
        max_tokens: Limite máximo de tokens na resposta
        temperature: Criatividade (0.0 = determinístico, 1.0 = criativo)
        timeout_seconds: Timeout para a requisição
        metadata: Metadados adicionais (origem, versão do prompt, etc)
    """
    prompt: str
    tenant_id: int
    max_tokens: int = 500
    temperature: float = 0.7
    timeout_seconds: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validações"""
        if not self.prompt:
            raise ValueError("Prompt não pode ser vazio")
        if self.tenant_id <= 0:
            raise ValueError("tenant_id deve ser maior que 0")
        if not (0.0 <= self.temperature <= 1.0):
            raise ValueError("Temperature deve estar entre 0.0 e 1.0")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens deve ser maior que 0")


@dataclass
class ProviderResponse:
    """
    Response padronizado de qualquer provider.
    
    Atributos:
        texto: Resposta gerada pela IA
        provider_type: Qual provider gerou a resposta
        model_used: Modelo específico usado (ex: gpt-4, claude-2)
        tokens_used: Tokens consumidos
        cost_estimate: Custo estimado em USD
        latency_ms: Tempo de resposta em milissegundos
        timestamp: Quando a resposta foi gerada
        metadata: Metadados adicionais (ID da request, versão, etc)
        fallback_used: Se fallback foi ativado
    """
    texto: str
    provider_type: ProviderType
    model_used: str
    tokens_used: int
    cost_estimate: float
    latency_ms: int
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    fallback_used: bool = False
    
    def __post_init__(self):
        """Validações"""
        if not self.texto:
            raise ValueError("Texto da resposta não pode ser vazio")
        if self.tokens_used < 0:
            raise ValueError("tokens_used não pode ser negativo")
        if self.cost_estimate < 0:
            raise ValueError("cost_estimate não pode ser negativo")


class IAIProvider(ABC):
    """
    Interface abstrata para providers de IA.
    
    Todos os providers (mock, OpenAI, Claude) devem implementar esta interface.
    """
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Retorna o tipo do provider"""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica se o provider está disponível.
        
        Returns:
            True se configurado corretamente e disponível
        """
        pass
    
    @abstractmethod
    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        """
        Gera uma resposta baseada no request.
        
        Args:
            request: Request padronizado
            
        Returns:
            ProviderResponse com a resposta gerada
            
        Raises:
            ProviderException: Em caso de erro na geração
        """
        pass
    
    @abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estima o custo de uma operação.
        
        Args:
            prompt_tokens: Tokens do prompt
            completion_tokens: Tokens estimados da resposta
            
        Returns:
            Custo estimado em USD
        """
        pass
    
    @abstractmethod
    def get_max_tokens_limit(self) -> int:
        """
        Retorna o limite máximo de tokens suportado.
        
        Returns:
            Número máximo de tokens
        """
        pass


class ProviderException(Exception):
    """
    Exceção base para erros de providers.
    """
    
    def __init__(
        self,
        message: str,
        provider_type: ProviderType,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.provider_type = provider_type
        self.original_error = original_error
        self.timestamp = datetime.now()


class ProviderTimeoutException(ProviderException):
    """Exceção para timeout"""
    pass


class ProviderRateLimitException(ProviderException):
    """Exceção para rate limit excedido"""
    pass


class ProviderCostLimitException(ProviderException):
    """Exceção para limite de custo excedido"""
    pass


class ProviderAuthException(ProviderException):
    """Exceção para erro de autenticação"""
    pass
