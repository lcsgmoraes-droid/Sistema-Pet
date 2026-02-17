"""
PDV Assistant - IA Contextual para Ponto de Venda

Sistema de IA que analisa o contexto de uma venda em andamento e gera
sugestões inteligentes em tempo real para o operador do PDV.

PRINCÍPIOS:
- IA NÃO executa ações
- IA NÃO altera a venda
- IA NÃO fala com o cliente
- IA apenas SUGERE para o OPERADOR

COMPONENTES:
- PDVContext: Contexto da venda em andamento
- PDVInsightSelector: Seleciona insights relevantes
- PDVAIService: Serviço principal de sugestões
- PDVPromptLibrary: Prompts otimizados para PDV

EXEMPLOS DE SUGESTÕES:
- "Este cliente costuma comprar ração a cada 30 dias."
- "Este kit sai 12% mais barato que os itens separados."
- "Produto X costuma ser comprado junto com Y."
- "Cliente está há 65 dias sem comprar."
"""

from app.ai.pdv_assistant.models import PDVContext, PDVSugestao, ItemVendaPDV
from app.ai.pdv_assistant.service import PDVAIService
from app.ai.pdv_assistant.selector import PDVInsightSelector

__all__ = [
    "PDVContext",
    "PDVSugestao",
    "ItemVendaPDV",
    "PDVAIService",
    "PDVInsightSelector",
]
