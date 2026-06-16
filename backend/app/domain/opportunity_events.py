"""
Domain types para eventos de oportunidade do PDV.

Define os tipos de eventos que podem ocorrer durante o fluxo de oportunidades
de venda, permitindo rastreamento, métricas e aprendizado da IA.

REGRA CRÍTICA: Eventos só são disparados por ação EXPLÍCITA do usuário.
Silêncio do usuário NUNCA gera evento.
"""

from enum import Enum


class OpportunityEventType(str, Enum):
    """
    Tipos de eventos de oportunidade no PDV.

    Quando usar:
    - OPORTUNIDADE_CONVERTIDA: Usuário clicou em "Adicionar" no painel de oportunidades
    - OPORTUNIDADE_REFINADA: Usuário clicou em "Ver Alternativa" no painel de oportunidades
    - OPORTUNIDADE_REJEITADA: Usuário clicou em "Ignorar" no painel de oportunidades

    Quando NÃO usar:
    - NUNCA disparar evento se usuário não interagiu
    - NUNCA disparar evento se usuário apenas fechou o painel
    - NUNCA disparar evento por timeout ou inatividade
    - NUNCA disparar evento automático baseado em carrinho

    Cada evento representa uma decisão consciente do operador do caixa.
    """

    OPORTUNIDADE_CONVERTIDA = "oportunidade_convertida"
    """
    Usuário aceitou a sugestão e adicionou produto ao carrinho.
    
    Gatilho: Clique no botão "➕ Adicionar" no painel de oportunidades.
    
    Efeito:
    - Incrementa métricas de conversão
    - Registra produto sugerido como aceito
    - Usa para treinamento futuro da IA
    """

    OPORTUNIDADE_REFINADA = "oportunidade_refinada"
    """
    Usuário solicitou alternativa à sugestão atual.
    
    Gatilho: Clique no botão "🔄 Ver Alternativa" no painel de oportunidades.
    
    Efeito:
    - Registra que a primeira sugestão não foi ideal
    - Incrementa contador de refinamentos
    - Backend deve apresentar próxima opção
    """

    OPORTUNIDADE_REJEITADA = "oportunidade_rejeitada"
    """
    Usuário explicitamente rejeitou a sugestão.
    
    Gatilho: Clique no botão "❌ Ignorar" no painel de oportunidades.
    
    Efeito:
    - Registra produto sugerido como não relevante
    - Remove sugestão da lista de oportunidades
    - Usa para aprendizado negativo da IA
    """


class OpportunityType(str, Enum):
    """
    Tipos de estratégia de oportunidade de venda.

    Define qual lógica de negócio gerou a sugestão.
    """

    CROSS_SELL = "cross_sell"
    """
    Venda cruzada: produtos frequentemente comprados juntos.
    
    Exemplo: Cliente comprando ração → sugerir comedouro
    """

    UP_SELL = "up_sell"
    """
    Venda superior: produtos de maior valor/margem na mesma categoria.
    
    Exemplo: Cliente comprando ração comum → sugerir ração premium
    """

    RECORRENCIA = "recorrencia"
    """
    Recompra: produtos que o cliente compra periodicamente.
    
    Exemplo: Cliente que compra ração a cada 30 dias → sugerir reposição
    """
