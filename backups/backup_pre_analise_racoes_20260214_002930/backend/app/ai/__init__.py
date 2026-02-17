"""
Motor de IA (AI Engine) - Sistema Pet Shop

Este módulo contém a base do motor de IA que interpreta dados estruturados
e fornece respostas contextualizadas.

PRINCÍPIOS:
- IA NÃO acessa banco de dados
- IA NÃO cria regras de negócio
- IA apenas interpreta dados já processados
- IA retorna respostas auditáveis e explicáveis

COMPONENTES:
- AIPromptBuilder: Constrói prompts controlados e estruturados
- AIEngine: Motor de IA (mock por enquanto, extensível para OpenAI/etc)
- Contracts: Contratos e interfaces que definem comportamentos
"""

from app.ai.engine import AIEngine
from app.ai.prompt_builder import AIPromptBuilder

__all__ = [
    "AIEngine",
    "AIPromptBuilder",
]
