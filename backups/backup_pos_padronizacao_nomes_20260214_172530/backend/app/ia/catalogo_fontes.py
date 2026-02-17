"""
Catálogo de Fontes da IA - Base Semântica
Mapeia quais dados existem, o que cada serviço responde e quando usar cada um.
Este é o "mapa mental" formal da IA para acessar informações do sistema.
"""

CATALOGO_FONTES_IA = {
    "dre": {
        "nome": "DRE - Demonstração de Resultado",
        "descricao": "Resultado financeiro mensal da empresa (receitas, custos, despesas, lucro/prejuízo)",
        "usar_quando": [
            "lucro",
            "prejuizo",
            "resultado",
            "margem",
            "receita",
            "faturamento",
            "despesas",
            "custos",
            "quanto ganhei",
            "quanto vendi",
        ],
        "endpoint": "/dre/canais",
        "tipo": "historico",
        "dados_retornados": [
            "receita_bruta",
            "impostos",
            "custos",
            "despesas_operacionais",
            "despesas_pessoal",
            "lucro_liquido",
        ],
        "exemplo_pergunta": "Qual foi meu lucro em janeiro?",
    },
    
    "simples_nacional": {
        "nome": "Simples Nacional - Tributação",
        "descricao": "Imposto efetivo, alíquota vigente e sugerida do Simples Nacional",
        "usar_quando": [
            "imposto",
            "simples",
            "aliquota",
            "tributacao",
            "quanto paguei de imposto",
            "das",
            "anexo",
        ],
        "endpoint": "/simples/fechamento",
        "tipo": "historico",
        "dados_retornados": [
            "faturamento_sistema",
            "faturamento_contador",
            "imposto_estimado",
            "das_real",
            "aliquota_efetiva",
            "aliquota_sugerida",
        ],
        "exemplo_pergunta": "Qual minha alíquota efetiva do Simples?",
    },
    
    "auditoria_provisoes": {
        "nome": "Auditoria de Provisões",
        "descricao": "Comparação entre valores provisionados e valores reais pagos (Simples, INSS, FGTS, Folha, Férias, 13º)",
        "usar_quando": [
            "provisao",
            "provisionado",
            "quanto provisionei",
            "diferenca provisao",
            "provisao vs realizado",
            "acuracidade",
        ],
        "endpoint": "/auditoria-provisoes/mensal",
        "tipo": "historico",
        "dados_retornados": [
            "valor_provisionado",
            "valor_realizado",
            "diferenca",
            "percentual_diferenca",
            "status",
        ],
        "exemplo_pergunta": "As provisões de janeiro bateram com o realizado?",
    },
    
    "provisoes_trabalhistas": {
        "nome": "Provisões Trabalhistas",
        "descricao": "Custos futuros obrigatórios relacionados a funcionários (folha, férias, 13º, encargos)",
        "usar_quando": [
            "funcionario",
            "folha",
            "ferias",
            "13",
            "decimo terceiro",
            "custo pessoal",
            "encargos",
            "inss",
            "fgts",
            "quanto custa meus funcionarios",
        ],
        "endpoint": "/auditoria-provisoes/mensal",
        "tipo": "historico",
        "dados_retornados": [
            "folha_provisionada",
            "folha_realizada",
            "ferias_acumuladas",
            "13_acumulado",
        ],
        "exemplo_pergunta": "Quanto tenho acumulado de férias?",
    },
    
    "projecao_caixa": {
        "nome": "Projeção de Caixa",
        "descricao": "Projeção futura de caixa baseada em histórico real + provisões obrigatórias",
        "usar_quando": [
            "caixa futuro",
            "vai faltar dinheiro",
            "previsao",
            "projecao",
            "quanto terei",
            "saldo futuro",
            "30 dias",
            "60 dias",
            "90 dias",
        ],
        "endpoint": "/projecao-caixa/",
        "tipo": "projecao",
        "dados_retornados": [
            "receita_prevista",
            "imposto_simples_previsto",
            "folha_encargos_previstos",
            "despesas_previstas",
            "saldo_previsto",
        ],
        "exemplo_pergunta": "Como vai estar meu caixa em 3 meses?",
    },
    
    "simulacao_contratacao": {
        "nome": "Simulação de Contratação",
        "descricao": "Simula impacto financeiro de contratar um novo funcionário (custo total mensal incluindo encargos e provisões)",
        "usar_quando": [
            "contratar",
            "admitir",
            "novo funcionario",
            "vale a pena contratar",
            "quanto custa contratar",
            "impacto de contratar",
            "simulacao",
            "hipotetico",
        ],
        "endpoint": "/simulacao-contratacao/",
        "tipo": "hipotetico",
        "dados_retornados": [
            "custo_total_mensal",
            "salario",
            "inss",
            "fgts",
            "provisao_ferias",
            "provisao_13",
            "detalhamento_mensal",
        ],
        "exemplo_pergunta": "Se eu contratar alguém por R$ 2.000, quanto vai custar de verdade?",
    },
    
    "contas_pagar": {
        "nome": "Contas a Pagar",
        "descricao": "Contas e compromissos financeiros a pagar (fornecedores, impostos, folha, etc)",
        "usar_quando": [
            "pagar",
            "divida",
            "compromissos",
            "vencimentos",
            "boletos",
            "fornecedores",
            "quanto devo",
            "o que preciso pagar",
        ],
        "endpoint": "/contas-pagar",
        "tipo": "historico",
        "dados_retornados": [
            "valor_original",
            "valor_pago",
            "valor_pendente",
            "data_vencimento",
            "categoria",
            "fornecedor",
        ],
        "exemplo_pergunta": "Quais contas vencem esta semana?",
    },
    
    "vendas": {
        "nome": "Vendas",
        "descricao": "Histórico de vendas realizadas (PDV, canais, produtos, valores)",
        "usar_quando": [
            "vendas",
            "quanto vendi",
            "produto mais vendido",
            "ticket medio",
            "clientes",
            "faturamento",
        ],
        "endpoint": "/vendas",
        "tipo": "historico",
        "dados_retornados": [
            "valor_total",
            "quantidade_vendas",
            "produtos_vendidos",
            "canal",
            "cliente",
        ],
        "exemplo_pergunta": "Qual foi o produto mais vendido em janeiro?",
    },
    
    "estoque": {
        "nome": "Estoque",
        "descricao": "Produtos disponíveis em estoque (quantidades, valores, movimentações)",
        "usar_quando": [
            "estoque",
            "produto disponivel",
            "quanto tenho",
            "falta produto",
            "inventario",
        ],
        "endpoint": "/estoque",
        "tipo": "atual",
        "dados_retornados": [
            "quantidade_disponivel",
            "valor_estoque",
            "custo_medio",
            "produtos_zerados",
        ],
        "exemplo_pergunta": "Quantas unidades tenho do produto X?",
    },
}


# Mapa de intenções para facilitar matching de perguntas
MAPA_INTENCOES = {
    "resultado_financeiro": ["dre"],
    "tributacao": ["simples_nacional"],
    "provisoes": ["auditoria_provisoes", "provisoes_trabalhistas"],
    "custos_pessoal": ["provisoes_trabalhistas", "simulacao_contratacao"],
    "previsao_futura": ["projecao_caixa"],
    "simulacao_cenario": ["simulacao_contratacao"],
    "compromissos": ["contas_pagar"],
    "vendas_produtos": ["vendas", "estoque"],
    "disponibilidade": ["estoque"],
}


# Palavras-chave por categoria para ajudar a IA a escolher a fonte certa
PALAVRAS_CHAVE = {
    "financeiro_historico": [
        "lucro", "prejuizo", "resultado", "margem", "receita", "faturamento",
        "quanto ganhei", "quanto vendi", "resultado do mes"
    ],
    "tributacao": [
        "imposto", "simples", "aliquota", "tributacao", "das", "anexo",
        "quanto paguei de imposto", "imposto efetivo"
    ],
    "provisoes_analise": [
        "provisao", "provisionado", "acumulado", "diferenca",
        "provisao vs realizado", "bateu", "acuracidade"
    ],
    "custos_trabalhistas": [
        "funcionario", "folha", "ferias", "13", "decimo terceiro",
        "custo pessoal", "encargos", "inss", "fgts"
    ],
    "projecao_futuro": [
        "futuro", "vai", "tera", "previsao", "projecao",
        "30 dias", "60 dias", "90 dias", "proximo mes",
        "vai faltar", "vai sobrar"
    ],
    "simulacao_hipotese": [
        "se", "contratar", "admitir", "vale a pena",
        "quanto custaria", "impacto de", "simulacao",
        "novo funcionario", "hipotetico"
    ],
    "compromissos_pagamentos": [
        "pagar", "divida", "compromissos", "vencimentos",
        "boletos", "fornecedores", "quanto devo"
    ],
    "vendas": [
        "vendi", "vendas", "produto mais vendido", "ticket medio",
        "clientes", "canais"
    ],
    "estoque_disponibilidade": [
        "estoque", "disponivel", "quanto tenho", "falta",
        "inventario", "zerado"
    ],
}


def obter_fonte_por_intencao(pergunta: str) -> list:
    """
    Analisa uma pergunta e retorna as fontes mais adequadas.
    
    Args:
        pergunta: Pergunta do usuário em linguagem natural
        
    Returns:
        Lista de chaves de fontes no CATALOGO_FONTES_IA
    """
    pergunta_lower = pergunta.lower()
    fontes_candidatas = []
    
    # Verificar cada fonte no catálogo
    for fonte_key, fonte_info in CATALOGO_FONTES_IA.items():
        # Verificar se alguma palavra-chave da fonte aparece na pergunta
        for palavra_chave in fonte_info["usar_quando"]:
            if palavra_chave.lower() in pergunta_lower:
                if fonte_key not in fontes_candidatas:
                    fontes_candidatas.append(fonte_key)
                break
    
    return fontes_candidatas


def descrever_fonte(fonte_key: str) -> str:
    """
    Retorna uma descrição textual de uma fonte para usar em prompts de IA.
    
    Args:
        fonte_key: Chave da fonte no catálogo
        
    Returns:
        Descrição formatada da fonte
    """
    if fonte_key not in CATALOGO_FONTES_IA:
        return f"Fonte '{fonte_key}' não encontrada no catálogo."
    
    fonte = CATALOGO_FONTES_IA[fonte_key]
    
    descricao = f"""
**{fonte['nome']}**
- Descrição: {fonte['descricao']}
- Tipo: {fonte['tipo']}
- Endpoint: {fonte['endpoint']}
- Usar quando a pergunta for sobre: {', '.join(fonte['usar_quando'])}
- Exemplo: "{fonte['exemplo_pergunta']}"
"""
    
    return descricao.strip()


def gerar_contexto_para_ia(pergunta: str) -> str:
    """
    Gera contexto completo para enviar à IA generativa.
    Inclui descrição das fontes relevantes para a pergunta.
    
    Args:
        pergunta: Pergunta do usuário
        
    Returns:
        Contexto formatado com fontes relevantes
    """
    fontes_relevantes = obter_fonte_por_intencao(pergunta)
    
    if not fontes_relevantes:
        # Se não encontrou fontes específicas, retorna todas
        fontes_relevantes = list(CATALOGO_FONTES_IA.keys())
    
    contexto = "# FONTES DE DADOS DISPONÍVEIS\n\n"
    contexto += "Você tem acesso às seguintes fontes de dados do sistema:\n\n"
    
    for fonte_key in fontes_relevantes:
        contexto += descrever_fonte(fonte_key) + "\n\n"
    
    contexto += "\n# PERGUNTA DO USUÁRIO\n\n"
    contexto += pergunta
    
    return contexto
