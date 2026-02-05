"""
Settings - Configurações de IA

Centraliza todas as configurações relacionadas aos providers de IA.

Variáveis de ambiente:
- AI_PROVIDER: mock|openai|anthropic
- OPENAI_API_KEY: Chave da API OpenAI
- AI_MAX_TOKENS: Limite máximo de tokens por request
- AI_TIMEOUT_SECONDS: Timeout para requests
- AI_DAILY_COST_LIMIT_USD: Limite diário de custo por tenant
- AI_ENABLE_FALLBACK: Se deve usar fallback para mock em caso de falha
"""

import os
from typing import Optional
from enum import Enum


class AIProviderType(Enum):
    """Tipos de providers disponíveis"""
    MOCK = "mock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class AISettings:
    """
    Configurações centralizadas para o sistema de IA.
    
    Usa variáveis de ambiente com valores padrão seguros.
    """
    
    # ========================================================================
    # PROVIDER CONFIGURATION
    # ========================================================================
    
    # Qual provider usar (padrão: mock)
    PROVIDER: AIProviderType = AIProviderType(
        os.getenv("AI_PROVIDER", "mock").lower()
    )
    
    # OpenAI API Key (obrigatório se PROVIDER=openai)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Modelo OpenAI padrão
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # Anthropic API Key (futuro)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # ========================================================================
    # LIMITS AND TIMEOUTS
    # ========================================================================
    
    # Máximo de tokens por request (padrão: 500)
    MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "500"))
    
    # Timeout para requests em segundos (padrão: 5s)
    TIMEOUT_SECONDS: int = int(os.getenv("AI_TIMEOUT_SECONDS", "5"))
    
    # Temperature padrão (0.0 = determinístico, 1.0 = criativo)
    DEFAULT_TEMPERATURE: float = float(os.getenv("AI_DEFAULT_TEMPERATURE", "0.7"))
    TEMPERATURE: float = DEFAULT_TEMPERATURE  # Alias para conveniência
    
    # ========================================================================
    # COST CONTROL
    # ========================================================================
    
    # Limite diário de custo por tenant em USD (padrão: $5.00)
    DAILY_COST_LIMIT_USD: float = float(
        os.getenv("AI_DAILY_COST_LIMIT_USD", "5.0")
    )
    
    # Soft limit - aviso quando atingir X% do limite (padrão: 80%)
    COST_WARNING_THRESHOLD: float = float(
        os.getenv("AI_COST_WARNING_THRESHOLD", "0.8")
    )
    
    # ========================================================================
    # FALLBACK CONFIGURATION
    # ========================================================================
    
    # Se deve usar mock como fallback em caso de falha (padrão: True)
    ENABLE_FALLBACK: bool = os.getenv("AI_ENABLE_FALLBACK", "true").lower() == "true"
    
    # Número máximo de tentativas antes de fallback (padrão: 2)
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("AI_MAX_RETRY_ATTEMPTS", "2"))
    
    # ========================================================================
    # PRICING (OpenAI GPT-4 - valores atualizados)
    # ========================================================================
    
    # Preços por 1K tokens (USD)
    OPENAI_GPT4_PRICE_PER_1K_INPUT: float = 0.03  # $0.03 / 1K tokens
    OPENAI_GPT4_PRICE_PER_1K_OUTPUT: float = 0.06  # $0.06 / 1K tokens
    
    OPENAI_GPT35_PRICE_PER_1K_INPUT: float = 0.0015  # $0.0015 / 1K tokens
    OPENAI_GPT35_PRICE_PER_1K_OUTPUT: float = 0.002  # $0.002 / 1K tokens
    
    # ========================================================================
    # PROMPT VERSIONING
    # ========================================================================
    
    # Versão padrão dos prompts
    DEFAULT_PROMPT_VERSION: str = "v1"
    
    # Se deve incluir versão do prompt no metadata
    INCLUDE_PROMPT_VERSION: bool = True
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    @classmethod
    def validate(cls) -> list:
        """
        Valida as configurações e retorna lista de erros.
        
        Returns:
            Lista de mensagens de erro (vazia se tudo OK)
        """
        errors = []
        
        # Validar provider
        if cls.PROVIDER == AIProviderType.OPENAI:
            if not cls.OPENAI_API_KEY:
                errors.append(
                    "OPENAI_API_KEY é obrigatória quando AI_PROVIDER=openai"
                )
        
        # Validar limites
        if cls.MAX_TOKENS <= 0:
            errors.append("AI_MAX_TOKENS deve ser maior que 0")
        
        if cls.TIMEOUT_SECONDS <= 0:
            errors.append("AI_TIMEOUT_SECONDS deve ser maior que 0")
        
        if cls.DAILY_COST_LIMIT_USD < 0:
            errors.append("AI_DAILY_COST_LIMIT_USD não pode ser negativo")
        
        if not (0.0 <= cls.DEFAULT_TEMPERATURE <= 1.0):
            errors.append("AI_DEFAULT_TEMPERATURE deve estar entre 0.0 e 1.0")
        
        if not (0.0 <= cls.COST_WARNING_THRESHOLD <= 1.0):
            errors.append("AI_COST_WARNING_THRESHOLD deve estar entre 0.0 e 1.0")
        
        return errors
    
    @classmethod
    def is_valid(cls) -> bool:
        """
        Verifica se as configurações são válidas.
        
        Returns:
            True se válidas, False caso contrário
        """
        return len(cls.validate()) == 0
    
    @classmethod
    def get_summary(cls) -> dict:
        """
        Retorna resumo das configurações (sem expor secrets).
        
        Returns:
            Dicionário com configurações (chaves mascaradas)
        """
        return {
            "provider": cls.PROVIDER.value,
            "openai_configured": bool(cls.OPENAI_API_KEY),
            "max_tokens": cls.MAX_TOKENS,
            "timeout_seconds": cls.TIMEOUT_SECONDS,
            "daily_cost_limit_usd": cls.DAILY_COST_LIMIT_USD,
            "enable_fallback": cls.ENABLE_FALLBACK,
            "model": cls.OPENAI_MODEL if cls.PROVIDER == AIProviderType.OPENAI else "N/A",
            "prompt_version": cls.DEFAULT_PROMPT_VERSION,
        }


# Validar configurações na importação
_validation_errors = AISettings.validate()
if _validation_errors and AISettings.PROVIDER != AIProviderType.MOCK:
    import warnings
    for error in _validation_errors:
        warnings.warn(f"[AISettings] {error}", stacklevel=2)
