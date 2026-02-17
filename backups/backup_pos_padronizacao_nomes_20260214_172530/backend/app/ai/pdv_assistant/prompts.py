"""
PDVPromptLibrary - Biblioteca de Prompts Específicos para PDV

Contém prompts otimizados para gerar sugestões contextuais
para operadores do PDV.

CARACTERÍSTICAS DOS PROMPTS PDV:
- Linguagem curta e direta
- Tom de apoio ao operador
- Sem termos técnicos
- Sem linguagem robótica
- Foco em ação imediata
- Máximo 200 caracteres por sugestão
"""

from typing import Dict, Any, List
from app.ai.pdv_assistant.models import PDVContext, ItemVendaPDV


class PDVPromptLibrary:
    """
    Biblioteca de prompts especializados para o PDV.
    
    Cada método gera um prompt específico para uma situação
    do PDV, garantindo que as sugestões sejam úteis e acionáveis.
    """
    
    @staticmethod
    def prompt_analise_geral_pdv(
        pdv_context: PDVContext,
        insights_selecionados: List[Dict[str, Any]]
    ) -> str:
        """
        Prompt geral para análise de contexto do PDV.
        
        Usado quando há múltiplos insights para analisar.
        """
        cliente_info = ""
        if pdv_context.tem_cliente_identificado:
            cliente_info = f"""
**CLIENTE IDENTIFICADO:**
- Nome: {pdv_context.cliente_nome}
- ID: {pdv_context.cliente_id}
"""
        
        itens_info = ""
        if pdv_context.itens:
            itens_lista = "\n".join([
                f"  - {item.nome_produto} (R$ {item.valor_total:.2f})"
                for item in pdv_context.itens
            ])
            itens_info = f"""
**PRODUTOS NA VENDA:**
{itens_lista}
**TOTAL PARCIAL:** R$ {pdv_context.total_parcial:.2f}
"""
        
        insights_info = ""
        if insights_selecionados:
            insights_lista = "\n".join([
                f"  - {insight.get('tipo', 'N/A')}: {insight.get('titulo', 'N/A')}"
                for insight in insights_selecionados
            ])
            insights_info = f"""
**INSIGHTS DISPONÍVEIS:**
{insights_lista}
"""
        
        return f"""
Você é um assistente inteligente para operadores de PDV (Ponto de Venda) de pet shop.

Seu papel é SUGERIR ações úteis ao operador, baseado no contexto da venda em andamento.

**REGRAS ABSOLUTAS:**
- Você NÃO executa ações
- Você NÃO altera a venda
- Você NÃO fala com o cliente
- Você apenas SUGERE para o OPERADOR

**CONTEXTO DA VENDA:**
- Vendedor: {pdv_context.vendedor_nome}
- Momento: {pdv_context.timestamp.strftime('%H:%M')}
{cliente_info}
{itens_info}
{insights_info}

**SUA TAREFA:**
Gere até 3 sugestões curtas, claras e úteis para o operador.

**FORMATO DE CADA SUGESTÃO:**
- Máximo 150 caracteres
- Linguagem humana e amigável
- Tom de apoio (não de ordem)
- Evite jargões técnicos
- Seja específico e acionável

**EXEMPLOS DE BOAS SUGESTÕES:**
✓ "Este cliente costuma comprar ração a cada 30 dias."
✓ "Kit Premium sai 12% mais barato que os itens separados."
✓ "Shampoo antipulgas costuma ser comprado junto com este produto."
✓ "Cliente VIP - última compra foi há 15 dias."

**EXEMPLOS DE MÁS SUGESTÕES:**
✗ "Análise preditiva indica padrão de recompra recorrente." (muito técnico)
✗ "Você deve oferecer o produto X." (tom de ordem)
✗ "Sistema identificou oportunidade de cross-sell com base em..." (muito longo)

Responda APENAS com as sugestões, uma por linha, sem numeração.
"""
    
    @staticmethod
    def prompt_cross_sell(
        produto_atual: ItemVendaPDV,
        produto_sugerido: str,
        percentual_compra_junto: float
    ) -> str:
        """
        Prompt para sugestão de cross-sell.
        """
        return f"""
Gere uma sugestão de cross-sell para o operador do PDV.

**CONTEXTO:**
- Produto na venda: {produto_atual.nome_produto}
- Produto sugerido: {produto_sugerido}
- Frequência de compra junto: {percentual_compra_junto:.0f}%

**REGRAS:**
- Máximo 150 caracteres
- Linguagem amigável
- Não use "você deve" ou "recomendo fortemente"
- Use tom de sugestão: "costuma", "geralmente", "pode interessar"

Responda APENAS com a sugestão.
"""
    
    @staticmethod
    def prompt_kit_vantajoso(
        produtos_venda: List[ItemVendaPDV],
        nome_kit: str,
        economia_percentual: float,
        economia_valor: float
    ) -> str:
        """
        Prompt para sugestão de kit mais vantajoso.
        """
        produtos_lista = ", ".join([p.nome_produto for p in produtos_venda[:3]])
        
        return f"""
Gere uma sugestão sobre kit mais vantajoso para o operador do PDV.

**CONTEXTO:**
- Produtos na venda: {produtos_lista}
- Kit disponível: {nome_kit}
- Economia: {economia_percentual:.0f}% (R$ {economia_valor:.2f})

**REGRAS:**
- Máximo 150 caracteres
- Mencione o percentual OU o valor (não ambos)
- Linguagem clara e objetiva
- Tom informativo (não persuasivo)

**EXEMPLO:**
"Kit {nome_kit} sai {economia_percentual:.0f}% mais barato que os itens separados."

Responda APENAS com a sugestão.
"""
    
    @staticmethod
    def prompt_cliente_recorrente(
        cliente_nome: str,
        dias_desde_ultima_compra: int,
        frequencia_media_dias: int
    ) -> str:
        """
        Prompt para informação sobre padrão de compra do cliente.
        """
        return f"""
Gere uma informação útil sobre o padrão de compra do cliente.

**CONTEXTO:**
- Cliente: {cliente_nome}
- Última compra: há {dias_desde_ultima_compra} dias
- Frequência média: a cada {frequencia_media_dias} dias

**REGRAS:**
- Máximo 120 caracteres
- Linguagem neutra e informativa
- Não sugira contato com o cliente
- Apenas informe o padrão

**EXEMPLOS:**
"Cliente costuma comprar a cada {frequencia_media_dias} dias."
"Última compra foi há {dias_desde_ultima_compra} dias."

Responda APENAS com a informação.
"""
    
    @staticmethod
    def prompt_cliente_inativo(
        cliente_nome: str,
        dias_sem_comprar: int
    ) -> str:
        """
        Prompt para alerta sobre cliente inativo.
        """
        return f"""
Gere um alerta sutil sobre cliente inativo.

**CONTEXTO:**
- Cliente: {cliente_nome}
- Dias sem comprar: {dias_sem_comprar}

**REGRAS:**
- Máximo 100 caracteres
- Tom neutro (não alarmista)
- Apenas informativo

**EXEMPLO:**
"Cliente está há {dias_sem_comprar} dias sem comprar."

Responda APENAS com o alerta.
"""
    
    @staticmethod
    def prompt_cliente_vip(
        cliente_nome: str,
        total_gasto: float,
        quantidade_compras: int
    ) -> str:
        """
        Prompt para identificação de cliente VIP.
        """
        return f"""
Gere uma informação sobre cliente VIP.

**CONTEXTO:**
- Cliente: {cliente_nome}
- Total gasto: R$ {total_gasto:.2f}
- Quantidade de compras: {quantidade_compras}

**REGRAS:**
- Máximo 100 caracteres
- Tom positivo e profissional
- Destaque a importância do cliente

**EXEMPLOS:**
"Cliente VIP - {quantidade_compras} compras realizadas."
"Cliente de alto valor - total gasto: R$ {total_gasto:.2f}."

Responda APENAS com a informação.
"""
    
    @staticmethod
    def prompt_recompra_prevista(
        produto_nome: str,
        dias_media_recompra: int
    ) -> str:
        """
        Prompt para sugestão de produto que cliente costuma recomprar.
        """
        return f"""
Gere uma sugestão sobre oportunidade de recompra.

**CONTEXTO:**
- Produto: {produto_nome}
- Ciclo médio de recompra: {dias_media_recompra} dias

**REGRAS:**
- Máximo 120 caracteres
- Linguagem sugestiva (não impositiva)
- Mencione o produto

**EXEMPLO:**
"Cliente costuma recomprar {produto_nome} a cada {dias_media_recompra} dias."

Responda APENAS com a sugestão.
"""
    
    @staticmethod
    def prompt_estoque_critico(
        produto_nome: str,
        quantidade_disponivel: int
    ) -> str:
        """
        Prompt para alerta sobre estoque crítico.
        """
        return f"""
Gere um alerta sobre estoque baixo.

**CONTEXTO:**
- Produto: {produto_nome}
- Quantidade disponível: {quantidade_disponivel}

**REGRAS:**
- Máximo 100 caracteres
- Tom informativo (não alarmista)
- Não sugira ações

**EXEMPLO:**
"Estoque de {produto_nome}: apenas {quantidade_disponivel} unidades."

Responda APENAS com o alerta.
"""
