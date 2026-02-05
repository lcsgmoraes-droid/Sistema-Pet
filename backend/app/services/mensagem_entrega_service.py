"""
ETAPA 10 - Service de Montagem de Mensagens de Entrega

Gera mensagem padrão única para todos os envios.
VERSÃO PROFISSIONAL - Menos emoji, linguagem objetiva.
"""


def normalizar_tempo(minutos: int) -> int:
    """
    Normaliza tempo para intervalos redondos.
    Cliente prefere "20 minutos" do que "17 minutos".
    """
    if minutos <= 5:
        return 5
    if minutos <= 10:
        return 10
    if minutos <= 20:
        return 20
    return round(minutos / 5) * 5


def normalizar_forma_pagamento(forma: str) -> str:
    """
    Padroniza forma de pagamento para evitar dúvidas.
    """
    if not forma:
        return "Não informado"
    
    forma_lower = forma.lower()
    
    if "dinheiro" in forma_lower:
        return "Dinheiro"
    if "pix" in forma_lower:
        return "Pix"
    if "cartao" in forma_lower or "cartão" in forma_lower or "credito" in forma_lower or "crédito" in forma_lower:
        return "Cartão"
    if "online" in forma_lower or "pago" in forma_lower:
        return "Já pago"
    
    return forma  # Retorna original se não identificar


def formatar_lista_produtos(produtos: list[str], max_linhas: int = 5) -> str:
    """
    Formata lista de produtos com limite anti-spam.
    Máximo 5 linhas. Se tiver mais, mostra +X itens.
    """
    if not produtos:
        return "- Pedido sem itens especificados"
    
    if len(produtos) <= max_linhas:
        return "\n".join(f"- {p}" for p in produtos)
    
    # Mostrar primeiros N-1 e resumir o resto
    produtos_visiveis = produtos[:max_linhas - 1]
    itens_ocultos = len(produtos) - len(produtos_visiveis)
    
    linhas = [f"- {p}" for p in produtos_visiveis]
    linhas.append(f"- +{itens_ocultos} itens")
    
    return "\n".join(linhas)


def montar_mensagem_entrega(
    cliente_nome: str,
    numero_pedido: str,
    produtos: list[str],
    forma_pagamento: str,
    minutos: int,
) -> str:
    """
    Monta mensagem padrão de entrega - VERSÃO PROFISSIONAL.
    
    Melhorias:
    - Menos emoji (reduz bloqueio WhatsApp)
    - Linguagem objetiva
    - Tempo normalizado (aprox.)
    - Lista limitada anti-spam
    - Pedido educado no final
    
    Args:
        cliente_nome: Nome do cliente
        numero_pedido: Número do pedido (ex: "123")
        produtos: Lista de produtos (ex: ["Ração Premium 15kg", "Shampoo Pet 500ml"])
        forma_pagamento: Forma de pagamento (ex: "Dinheiro", "Cartão de Crédito")
        minutos: Tempo estimado em minutos
        
    Returns:
        Mensagem formatada pronta para envio
    """
    # Normalizar tempo
    minutos_norm = normalizar_tempo(minutos)
    
    # Normalizar forma de pagamento
    pagamento_norm = normalizar_forma_pagamento(forma_pagamento)
    
    # Formatar produtos (máx 5 linhas)
    lista_produtos = formatar_lista_produtos(produtos, max_linhas=5)
    
    return f"""🛵 Olá, {cliente_nome}!

Seu pedido #{numero_pedido} já saiu para entrega.

📦 Itens:
{lista_produtos}

💳 Pagamento:
{pagamento_norm}

⏱️ Previsão de chegada:
aprox. {minutos_norm} minutos.

Por favor, mantenha alguém disponível para receber.""".strip()
