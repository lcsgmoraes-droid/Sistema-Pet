"""
Adapter para Chat do Operador

Este módulo é responsável por:
1. Detectar a intenção da pergunta (heurística simples, SEM IA)
2. Selecionar o prompt adequado
3. Montar AIContext compatível com o AI Engine
4. Injetar dados de PDVContext, Insights e Read Models

IMPORTANTE: Este adapter usa apenas REGRAS DETERMINÍSTICAS.
Não usa IA para detectar intenção (isso seria overhead desnecessário).
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from .models import (
    OperatorChatContext,
    IntentionDetectionResult,
    INTENCAO_CLIENTE,
    INTENCAO_PRODUTO,
    INTENCAO_KIT,
    INTENCAO_ESTOQUE,
    INTENCAO_INSIGHT,
    INTENCAO_VENDA,
    INTENCAO_GENERICA,
)


# ============================================================================
# PALAVRAS-CHAVE PARA DETECÇÃO DE INTENÇÃO
# ============================================================================

KEYWORDS_CLIENTE = [
    "cliente", "comprador", "freguês", "histórico do cliente",
    "cliente costuma", "esse cliente", "perfil do cliente",
    "cliente já", "cliente comprou", "cliente atrasa",
    "cliente paga", "cliente vip"
]

KEYWORDS_PRODUTO = [
    "produto", "item", "mercadoria", "este produto",
    "esse produto", "vende bem", "popular", "mais vendido",
    "produto bom", "qual produto", "tem produto"
]

KEYWORDS_KIT = [
    "kit", "combo", "conjunto", "pacote", "promoção",
    "kit melhor", "tem kit", "existe kit", "kit vantajoso",
    "sai mais barato", "mais em conta"
]

KEYWORDS_ESTOQUE = [
    "estoque", "disponível", "tem no estoque", "falta",
    "quantidade", "acabou", "acabando", "repor",
    "estoque baixo", "tem em estoque"
]

KEYWORDS_INSIGHT = [
    "insight", "sugestão", "recomendação", "dica",
    "sistema sugere", "o que o sistema", "por que sugeriu",
    "porque apareceu", "entender", "explicar"
]

KEYWORDS_VENDA = [
    "venda", "essa venda", "esta venda", "resumo",
    "resumir", "total", "o que vendi", "o que estou vendendo",
    "deveria oferecer", "o que oferecer"
]


# ============================================================================
# FUNÇÕES DE DETECÇÃO DE INTENÇÃO
# ============================================================================

def normalizar_texto(texto: str) -> str:
    """
    Normaliza texto para facilitar comparação.
    
    - Remove acentos (simplificado)
    - Converte para minúsculas
    - Remove pontuação extra
    """
    texto = texto.lower()
    # Simplificação: remove apenas pontuação comum
    texto = re.sub(r'[?.!,;:]', ' ', texto)
    return texto.strip()


def contar_palavras_chave(texto_normalizado: str, keywords: List[str]) -> int:
    """
    Conta quantas palavras-chave aparecem no texto.
    
    Args:
        texto_normalizado: Texto já normalizado
        keywords: Lista de palavras-chave a buscar
        
    Returns:
        Número de palavras-chave encontradas
    """
    contador = 0
    palavras_encontradas = []
    
    for keyword in keywords:
        keyword_norm = normalizar_texto(keyword)
        if keyword_norm in texto_normalizado:
            contador += 1
            palavras_encontradas.append(keyword)
    
    return contador, palavras_encontradas


def detectar_intencao(pergunta: str) -> IntentionDetectionResult:
    """
    Detecta a intenção da pergunta usando heurística simples.
    
    Algoritmo:
    1. Normaliza o texto
    2. Conta palavras-chave de cada categoria
    3. Retorna a categoria com mais matches
    4. Se empate ou nenhum match: genérica
    
    Args:
        pergunta: Pergunta do operador
        
    Returns:
        IntentionDetectionResult com intenção detectada
    """
    texto_norm = normalizar_texto(pergunta)
    
    # Contar matches de cada categoria
    scores = {}
    palavras_por_intencao = {}
    
    for intencao, keywords in [
        (INTENCAO_CLIENTE, KEYWORDS_CLIENTE),
        (INTENCAO_PRODUTO, KEYWORDS_PRODUTO),
        (INTENCAO_KIT, KEYWORDS_KIT),
        (INTENCAO_ESTOQUE, KEYWORDS_ESTOQUE),
        (INTENCAO_INSIGHT, KEYWORDS_INSIGHT),
        (INTENCAO_VENDA, KEYWORDS_VENDA),
    ]:
        count, palavras = contar_palavras_chave(texto_norm, keywords)
        scores[intencao] = count
        palavras_por_intencao[intencao] = palavras
    
    # Encontrar intenção com maior score
    if not scores or max(scores.values()) == 0:
        # Nenhuma palavra-chave encontrada
        return IntentionDetectionResult(
            intencao=INTENCAO_GENERICA,
            confianca=0.5,
            palavras_chave=[],
            prompt_sugerido="generica"
        )
    
    intencao_detectada = max(scores, key=scores.get)
    max_score = scores[intencao_detectada]
    
    # Calcular confiança baseada no número de matches
    # 1 match = 0.6, 2 matches = 0.75, 3+ matches = 0.9
    if max_score == 1:
        confianca = 0.6
    elif max_score == 2:
        confianca = 0.75
    else:
        confianca = 0.9
    
    return IntentionDetectionResult(
        intencao=intencao_detectada,
        confianca=confianca,
        palavras_chave=palavras_por_intencao[intencao_detectada],
        prompt_sugerido=intencao_detectada
    )


# ============================================================================
# MONTAGEM DE CONTEXTO PARA AI ENGINE
# ============================================================================

def montar_contexto_para_ai(
    operator_context: OperatorChatContext
) -> Dict[str, Any]:
    """
    Monta um dicionário de contexto compatível com o AI Engine.
    
    Este contexto será usado para formatar o prompt e será incluído
    na resposta para rastreabilidade.
    
    Args:
        operator_context: Contexto do chat do operador
        
    Returns:
        Dicionário com todos os contextos disponíveis formatados
    """
    contexto_ai = {}
    
    # Contexto PDV (venda em andamento)
    if operator_context.contexto_pdv:
        contexto_ai["contexto_pdv"] = formatar_contexto_pdv(
            operator_context.contexto_pdv
        )
    
    # Contexto Cliente
    if operator_context.contexto_cliente:
        contexto_ai["contexto_cliente"] = formatar_contexto_cliente(
            operator_context.contexto_cliente
        )
    
    # Contexto Produtos
    if operator_context.contexto_produto:
        contexto_ai["contexto_produto"] = formatar_contexto_produtos(
            operator_context.contexto_produto
        )
    
    # Contexto Insights
    if operator_context.contexto_insights:
        contexto_ai["contexto_insights"] = formatar_contexto_insights(
            operator_context.contexto_insights
        )
    
    return contexto_ai


def formatar_contexto_pdv(pdv_data: Dict[str, Any]) -> str:
    """
    Formata dados do PDV para inclusão no prompt.
    
    Args:
        pdv_data: Dados da venda em andamento
        
    Returns:
        String formatada para o prompt
    """
    linhas = ["VENDA EM ANDAMENTO:"]
    
    if "venda_id" in pdv_data:
        linhas.append(f"- ID da Venda: {pdv_data['venda_id']}")
    
    if "cliente_nome" in pdv_data:
        linhas.append(f"- Cliente: {pdv_data['cliente_nome']}")
    
    if "total_parcial" in pdv_data:
        linhas.append(f"- Total Parcial: R$ {pdv_data['total_parcial']:.2f}")
    
    if "itens" in pdv_data and pdv_data["itens"]:
        linhas.append(f"- Itens na venda: {len(pdv_data['itens'])}")
        linhas.append("  Produtos:")
        for item in pdv_data["itens"][:5]:  # Limita a 5 produtos
            nome = item.get("nome_produto", "Desconhecido")
            qtd = item.get("quantidade", 0)
            valor = item.get("valor_total", 0)
            linhas.append(f"    • {nome} (Qtd: {qtd}, Total: R$ {valor:.2f})")
    
    if "vendedor_nome" in pdv_data:
        linhas.append(f"- Vendedor: {pdv_data['vendedor_nome']}")
    
    return "\n".join(linhas)


def formatar_contexto_cliente(cliente_data: Dict[str, Any]) -> str:
    """
    Formata dados do cliente para inclusão no prompt.
    
    Args:
        cliente_data: Dados do cliente
        
    Returns:
        String formatada para o prompt
    """
    linhas = ["INFORMAÇÕES DO CLIENTE:"]
    
    if "nome" in cliente_data:
        linhas.append(f"- Nome: {cliente_data['nome']}")
    
    if "total_compras" in cliente_data:
        linhas.append(f"- Total de Compras: {cliente_data['total_compras']}")
    
    if "ticket_medio" in cliente_data:
        linhas.append(f"- Ticket Médio: R$ {cliente_data['ticket_medio']:.2f}")
    
    if "ultima_compra" in cliente_data:
        linhas.append(f"- Última Compra: {cliente_data['ultima_compra']}")
    
    if "status" in cliente_data:
        linhas.append(f"- Status: {cliente_data['status']}")
    
    if "categorias_preferidas" in cliente_data:
        cats = ", ".join(cliente_data["categorias_preferidas"][:3])
        linhas.append(f"- Categorias Preferidas: {cats}")
    
    return "\n".join(linhas)


def formatar_contexto_produtos(produtos_data: List[Dict[str, Any]]) -> str:
    """
    Formata dados de produtos para inclusão no prompt.
    
    Args:
        produtos_data: Lista de produtos
        
    Returns:
        String formatada para o prompt
    """
    linhas = ["PRODUTOS DA VENDA:"]
    
    for idx, produto in enumerate(produtos_data[:5], 1):  # Limita a 5
        linhas.append(f"{idx}. {produto.get('nome', 'Desconhecido')}")
        
        if "categoria" in produto:
            linhas.append(f"   - Categoria: {produto['categoria']}")
        
        if "fabricante" in produto:
            linhas.append(f"   - Fabricante: {produto['fabricante']}")
        
        if "valor_unitario" in produto:
            linhas.append(f"   - Valor Unitário: R$ {produto['valor_unitario']:.2f}")
        
        if "quantidade" in produto:
            linhas.append(f"   - Quantidade: {produto['quantidade']}")
    
    if len(produtos_data) > 5:
        linhas.append(f"\n(... e mais {len(produtos_data) - 5} produtos)")
    
    return "\n".join(linhas)


def formatar_contexto_insights(insights_data: List[Dict[str, Any]]) -> str:
    """
    Formata insights para inclusão no prompt.
    
    Args:
        insights_data: Lista de insights
        
    Returns:
        String formatada para o prompt
    """
    if not insights_data:
        return "Nenhum insight disponível no momento."
    
    linhas = ["INSIGHTS DISPONÍVEIS:"]
    
    for idx, insight in enumerate(insights_data[:5], 1):  # Limita a 5
        tipo = insight.get("tipo", "desconhecido")
        titulo = insight.get("titulo", "Sem título")
        mensagem = insight.get("mensagem_curta", "")
        
        linhas.append(f"{idx}. [{tipo.upper()}] {titulo}")
        if mensagem:
            linhas.append(f"   {mensagem}")
        
        if "confianca" in insight:
            linhas.append(f"   Confiança: {insight['confianca']*100:.0f}%")
    
    if len(insights_data) > 5:
        linhas.append(f"\n(... e mais {len(insights_data) - 5} insights)")
    
    return "\n".join(linhas)


# ============================================================================
# FUNÇÃO PRINCIPAL DO ADAPTER
# ============================================================================

def preparar_contexto_completo(
    operator_context: OperatorChatContext
) -> Dict[str, Any]:
    """
    Função principal do adapter que prepara tudo para o serviço.
    
    1. Detecta intenção
    2. Monta contexto para IA
    3. Retorna tudo junto
    
    Args:
        operator_context: Contexto do operador
        
    Returns:
        Dicionário com intenção detectada e contexto formatado
    """
    # 1. Detectar intenção
    intencao = detectar_intencao(operator_context.message.pergunta)
    
    # 2. Montar contexto
    contexto_ai = montar_contexto_para_ai(operator_context)
    
    # 3. Retornar tudo
    return {
        "intencao": intencao,
        "contexto_formatado": contexto_ai,
        "tenant_id": operator_context.tenant_id,
        "operador_id": operator_context.message.operador_id,
        "pergunta": operator_context.message.pergunta,
    }
