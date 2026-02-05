"""
IA Conversacional Interna (Chat do Operador)

Este módulo fornece um chat interno onde operadores podem fazer perguntas
em linguagem natural sobre o sistema.

IMPORTANTE:
- O chat é CONSULTIVO (não executa ações)
- Multi-tenant obrigatório
- Sempre auditável
- Nunca quebra o sistema

Uso básico:
    from app.ai.operator_chat import (
        OperatorMessage,
        OperatorChatContext,
        get_operator_chat_service
    )
    
    # Criar mensagem
    mensagem = OperatorMessage(
        pergunta="Esse cliente costuma comprar o quê?",
        operador_id=1,
        operador_nome="João Silva"
    )
    
    # Criar contexto
    contexto = OperatorChatContext(
        tenant_id=1,
        message=mensagem
    )
    
    # Processar
    service = get_operator_chat_service()
    resposta = service.processar_pergunta(contexto)
    
    print(resposta.resposta)
"""

# Models
from .models import (
    OperatorMessage,
    OperatorChatContext,
    OperatorChatResponse,
    IntentionDetectionResult,
    INTENCAO_CLIENTE,
    INTENCAO_PRODUTO,
    INTENCAO_KIT,
    INTENCAO_ESTOQUE,
    INTENCAO_INSIGHT,
    INTENCAO_VENDA,
    INTENCAO_GENERICA,
    FONTE_PDV_CONTEXT,
    FONTE_READ_MODEL,
    FONTE_INSIGHT,
    FONTE_REGRA_NEGOCIO,
    FONTE_HEURISTICA,
)

# Service
from .service import (
    OperatorChatService,
    get_operator_chat_service,
)

# Adapter (funções auxiliares)
from .adapter import (
    detectar_intencao,
    preparar_contexto_completo,
)

# Prompts (funções auxiliares)
from .prompts import (
    selecionar_prompt,
    formatar_prompt,
    obter_prompt_formatado,
)


__all__ = [
    # Models
    "OperatorMessage",
    "OperatorChatContext",
    "OperatorChatResponse",
    "IntentionDetectionResult",
    
    # Constantes de Intenção
    "INTENCAO_CLIENTE",
    "INTENCAO_PRODUTO",
    "INTENCAO_KIT",
    "INTENCAO_ESTOQUE",
    "INTENCAO_INSIGHT",
    "INTENCAO_VENDA",
    "INTENCAO_GENERICA",
    
    # Constantes de Fonte
    "FONTE_PDV_CONTEXT",
    "FONTE_READ_MODEL",
    "FONTE_INSIGHT",
    "FONTE_REGRA_NEGOCIO",
    "FONTE_HEURISTICA",
    
    # Service
    "OperatorChatService",
    "get_operator_chat_service",
    
    # Adapter
    "detectar_intencao",
    "preparar_contexto_completo",
    
    # Prompts
    "selecionar_prompt",
    "formatar_prompt",
    "obter_prompt_formatado",
]
