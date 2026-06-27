"""Definicoes das tools do WhatsApp para OpenAI Function Calling."""

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_produtos",
            "description": "Busca produtos no catálogo. Use quando o cliente perguntar sobre produtos, preços, estoque ou ração.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Termo de busca (nome do produto, marca, categoria). Ex: 'ração golden', 'brinquedo', 'coleira'",
                    },
                    "categoria": {
                        "type": "string",
                        "enum": [
                            "racao",
                            "brinquedo",
                            "higiene",
                            "acessorio",
                            "medicamento",
                            "outro",
                        ],
                        "description": "Categoria do produto (opcional)",
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de resultados (padrão: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verificar_horarios_disponiveis",
            "description": "Verifica horários disponíveis para agendamento. Use quando o cliente quiser marcar banho, tosa ou consulta.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "string",
                        "description": "Data desejada no formato YYYY-MM-DD. Use 'hoje' ou 'amanha' para datas relativas.",
                    },
                    "tipo_servico": {
                        "type": "string",
                        "enum": ["banho", "tosa", "consulta", "vacina", "outro"],
                        "description": "Tipo de serviço",
                    },
                },
                "required": ["tipo_servico"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_status_pedido",
            "description": "Busca informações sobre pedido ou entrega. Use quando o cliente perguntar 'onde está meu pedido', 'status da entrega', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telefone": {
                        "type": "string",
                        "description": "Telefone do cliente (será preenchido automaticamente)",
                    },
                    "codigo_pedido": {
                        "type": "string",
                        "description": "Código do pedido se o cliente informar",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_historico_compras",
            "description": "Busca histórico de compras do cliente. Use para mostrar últimas compras ou recomendar produtos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telefone": {
                        "type": "string",
                        "description": "Telefone do cliente",
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Número de compras a retornar (padrão: 3)",
                        "default": 3,
                    },
                },
                "required": ["telefone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obter_informacoes_loja",
            "description": "Retorna informações da loja: endereço, horário de funcionamento, telefone, etc. Use quando cliente perguntar 'onde fica', 'horário', 'telefone'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_info": {
                        "type": "string",
                        "enum": ["endereco", "horario", "contato", "todos"],
                        "description": "Tipo de informação desejada",
                        "default": "todos",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "criar_agendamento",
            "description": "Cria um novo agendamento para o cliente. Use quando o cliente confirmar data, horário e serviço desejado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_servico": {
                        "type": "string",
                        "enum": ["banho", "tosa", "consulta", "vacina", "outro"],
                        "description": "Tipo de serviço",
                    },
                    "data": {
                        "type": "string",
                        "description": "Data no formato YYYY-MM-DD",
                    },
                    "horario": {
                        "type": "string",
                        "description": "Horário no formato HH:MM",
                    },
                    "nome_pet": {"type": "string", "description": "Nome do pet"},
                    "observacoes": {
                        "type": "string",
                        "description": "Observações adicionais (opcional)",
                    },
                },
                "required": ["tipo_servico", "data", "horario", "nome_pet"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adicionar_ao_carrinho",
            "description": "Adiciona um produto ao carrinho de compras. Use quando o cliente quiser comprar algo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "produto_id": {"type": "string", "description": "ID do produto"},
                    "quantidade": {
                        "type": "integer",
                        "description": "Quantidade desejada",
                        "default": 1,
                    },
                },
                "required": ["produto_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ver_carrinho",
            "description": "Mostra os produtos no carrinho do cliente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telefone": {"type": "string", "description": "Telefone do cliente"}
                },
                "required": ["telefone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_frete",
            "description": "Calcula o valor do frete para o endereço do cliente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cep": {
                        "type": "string",
                        "description": "CEP de entrega (somente números)",
                    }
                },
                "required": ["cep"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finalizar_pedido",
            "description": "Finaliza o pedido e gera link de pagamento.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telefone": {
                        "type": "string",
                        "description": "Telefone do cliente",
                    },
                    "forma_pagamento": {
                        "type": "string",
                        "enum": ["pix", "cartao", "dinheiro"],
                        "description": "Forma de pagamento",
                    },
                    "cep_entrega": {
                        "type": "string",
                        "description": "CEP para entrega",
                    },
                },
                "required": ["telefone", "forma_pagamento"],
            },
        },
    },
]

__all__ = ["TOOLS_DEFINITIONS"]
