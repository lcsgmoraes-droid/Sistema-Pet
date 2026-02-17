"""
Tool Calling - Functions para OpenAI buscar dados reais do sistema
Permite que a IA consulte produtos, horários, pedidos, etc.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# Definições de tools para OpenAI Function Calling
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
                        "description": "Termo de busca (nome do produto, marca, categoria). Ex: 'ração golden', 'brinquedo', 'coleira'"
                    },
                    "categoria": {
                        "type": "string",
                        "enum": ["racao", "brinquedo", "higiene", "acessorio", "medicamento", "outro"],
                        "description": "Categoria do produto (opcional)"
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de resultados (padrão: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
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
                        "description": "Data desejada no formato YYYY-MM-DD. Use 'hoje' ou 'amanha' para datas relativas."
                    },
                    "tipo_servico": {
                        "type": "string",
                        "enum": ["banho", "tosa", "consulta", "vacina", "outro"],
                        "description": "Tipo de serviço"
                    }
                },
                "required": ["tipo_servico"]
            }
        }
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
                        "description": "Telefone do cliente (será preenchido automaticamente)"
                    },
                    "codigo_pedido": {
                        "type": "string",
                        "description": "Código do pedido se o cliente informar"
                    }
                },
                "required": []
            }
        }
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
                        "description": "Telefone do cliente"
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Número de compras a retornar (padrão: 3)",
                        "default": 3
                    }
                },
                "required": ["telefone"]
            }
        }
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
                        "default": "todos"
                    }
                },
                "required": []
            }
        }
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
                        "description": "Tipo de serviço"
                    },
                    "data": {
                        "type": "string",
                        "description": "Data no formato YYYY-MM-DD"
                    },
                    "horario": {
                        "type": "string",
                        "description": "Horário no formato HH:MM"
                    },
                    "nome_pet": {
                        "type": "string",
                        "description": "Nome do pet"
                    },
                    "observacoes": {
                        "type": "string",
                        "description": "Observações adicionais (opcional)"
                    }
                },
                "required": ["tipo_servico", "data", "horario", "nome_pet"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adicionar_ao_carrinho",
            "description": "Adiciona um produto ao carrinho de compras. Use quando o cliente quiser comprar algo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "produto_id": {
                        "type": "string",
                        "description": "ID do produto"
                    },
                    "quantidade": {
                        "type": "integer",
                        "description": "Quantidade desejada",
                        "default": 1
                    }
                },
                "required": ["produto_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ver_carrinho",
            "description": "Mostra os produtos no carrinho do cliente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telefone": {
                        "type": "string",
                        "description": "Telefone do cliente"
                    }
                },
                "required": ["telefone"]
            }
        }
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
                        "description": "CEP de entrega (somente números)"
                    }
                },
                "required": ["cep"]
            }
        }
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
                        "description": "Telefone do cliente"
                    },
                    "forma_pagamento": {
                        "type": "string",
                        "enum": ["pix", "cartao", "dinheiro"],
                        "description": "Forma de pagamento"
                    },
                    "cep_entrega": {
                        "type": "string",
                        "description": "CEP para entrega"
                    }
                },
                "required": ["telefone", "forma_pagamento"]
            }
        }
    }
]


class ToolExecutor:
    """Executa functions chamadas pela IA"""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa uma tool e retorna resultado
        
        Args:
            tool_name: Nome da function
            arguments: Argumentos da function
            
        Returns:
            Dicionário com resultado da execução
        """
        try:
            logger.info(f"Executando tool: {tool_name} com args: {arguments}")
            
            if tool_name == "buscar_produtos":
                return self._buscar_produtos(**arguments)
            
            elif tool_name == "verificar_horarios_disponiveis":
                return self._verificar_horarios_disponiveis(**arguments)
            
            elif tool_name == "buscar_status_pedido":
                return self._buscar_status_pedido(**arguments)
            
            elif tool_name == "buscar_historico_compras":
                return self._buscar_historico_compras(**arguments)
            
            elif tool_name == "obter_informacoes_loja":
                return self._obter_informacoes_loja(**arguments)
            
            elif tool_name == "criar_agendamento":
                return self._criar_agendamento(**arguments)
            
            elif tool_name == "adicionar_ao_carrinho":
                return self._adicionar_ao_carrinho(**arguments)
            
            elif tool_name == "ver_carrinho":
                return self._ver_carrinho(**arguments)
            
            elif tool_name == "calcular_frete":
                return self._calcular_frete(**arguments)
            
            elif tool_name == "finalizar_pedido":
                return self._finalizar_pedido(**arguments)
            
            else:
                return {
                    "error": f"Tool desconhecida: {tool_name}",
                    "success": False
                }
        
        except Exception as e:
            logger.error(f"Erro ao executar tool {tool_name}: {e}")
            return {
                "error": str(e),
                "success": False
            }
    
    def _buscar_produtos(
        self,
        query: str,
        categoria: Optional[str] = None,
        limite: int = 5
    ) -> Dict[str, Any]:
        """Busca produtos no catálogo"""
        try:
            # TODO: Integrar com tabela real de produtos quando disponível
            # Por enquanto, retorna mock data
            
            mock_produtos = [
                {
                    "id": "1",
                    "nome": "Ração Golden Fórmula Adulto 15kg",
                    "preco": 189.90,
                    "estoque": 12,
                    "categoria": "racao",
                    "descricao": "Ração super premium para cães adultos"
                },
                {
                    "id": "2",
                    "nome": "Ração Premier Ambientes Internos 10kg",
                    "preco": 156.50,
                    "estoque": 8,
                    "categoria": "racao",
                    "descricao": "Para cães que vivem em apartamento"
                },
                {
                    "id": "3",
                    "nome": "Brinquedo Kong Classic M",
                    "preco": 45.90,
                    "estoque": 25,
                    "categoria": "brinquedo",
                    "descricao": "Brinquedo resistente de borracha"
                }
            ]
            
            # Filtrar por query e categoria
            query_lower = query.lower()
            resultados = [
                p for p in mock_produtos
                if query_lower in p["nome"].lower() or query_lower in p["descricao"].lower()
            ]
            
            if categoria:
                resultados = [p for p in resultados if p["categoria"] == categoria]
            
            resultados = resultados[:limite]
            
            if not resultados:
                return {
                    "success": True,
                    "produtos": [],
                    "message": f"Nenhum produto encontrado para '{query}'"
                }
            
            return {
                "success": True,
                "produtos": resultados,
                "total": len(resultados)
            }
        
        except Exception as e:
            logger.error(f"Erro ao buscar produtos: {e}")
            return {"success": False, "error": str(e)}
    
    def _verificar_horarios_disponiveis(
        self,
        tipo_servico: str,
        data: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verifica horários disponíveis para agendamento"""
        try:
            # TODO: Integrar com sistema real de agendamentos
            # Por enquanto, retorna horários mock
            
            # Processar data
            if not data or data == "hoje":
                data_obj = datetime.now().date()
            elif data == "amanha":
                data_obj = (datetime.now() + timedelta(days=1)).date()
            else:
                try:
                    data_obj = datetime.strptime(data, "%Y-%m-%d").date()
                except:
                    data_obj = datetime.now().date()
            
            # Gerar horários disponíveis (mock)
            horarios_disponiveis = [
                "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"
            ]
            
            return {
                "success": True,
                "data": data_obj.strftime("%d/%m/%Y"),
                "tipo_servico": tipo_servico,
                "horarios_disponiveis": horarios_disponiveis,
                "message": f"Horários disponíveis para {tipo_servico} em {data_obj.strftime('%d/%m/%Y')}"
            }
        
        except Exception as e:
            logger.error(f"Erro ao verificar horários: {e}")
            return {"success": False, "error": str(e)}
    
    def _buscar_status_pedido(
        self,
        telefone: Optional[str] = None,
        codigo_pedido: Optional[str] = None
    ) -> Dict[str, Any]:
        """Busca status de pedidos"""
        try:
            # TODO: Integrar com sistema real de pedidos
            # Por enquanto, retorna mock data
            
            mock_pedidos = [
                {
                    "codigo": "PED-12345",
                    "data": "25/01/2026",
                    "status": "em_transito",
                    "status_descricao": "Em trânsito para entrega",
                    "previsao_entrega": "02/02/2026",
                    "itens": ["Ração Golden 15kg", "Shampoo Pet"]
                }
            ]
            
            if not mock_pedidos:
                return {
                    "success": True,
                    "pedidos": [],
                    "message": "Nenhum pedido encontrado"
                }
            
            return {
                "success": True,
                "pedidos": mock_pedidos,
                "total": len(mock_pedidos)
            }
        
        except Exception as e:
            logger.error(f"Erro ao buscar pedidos: {e}")
            return {"success": False, "error": str(e)}
    
    def _buscar_historico_compras(
        self,
        telefone: str,
        limite: int = 3
    ) -> Dict[str, Any]:
        """Busca histórico de compras do cliente"""
        try:
            # TODO: Integrar com sistema real
            return {
                "success": True,
                "compras": [],
                "message": "Nenhuma compra anterior encontrada"
            }
        
        except Exception as e:
            logger.error(f"Erro ao buscar histórico: {e}")
            return {"success": False, "error": str(e)}
    
    def _obter_informacoes_loja(
        self,
        tipo_info: str = "todos"
    ) -> Dict[str, Any]:
        """Retorna informações da loja"""
        try:
            # TODO: Buscar de configurações do tenant
            info_loja = {
                "nome": "Pet Shop Amigo",
                "endereco": "Rua das Flores, 123 - Centro",
                "cidade": "São Paulo - SP",
                "telefone": "(11) 98765-4321",
                "horario": {
                    "semana": "Segunda a Sexta: 8h às 18h",
                    "sabado": "Sábado: 8h às 14h",
                    "domingo": "Domingo: Fechado"
                },
                "servicos": ["Banho", "Tosa", "Consulta Veterinária", "Vacinas"],
                "formas_pagamento": ["Dinheiro", "Cartão", "Pix"]
            }
            
            if tipo_info == "endereco":
                return {
                    "success": True,
                    "endereco": info_loja["endereco"],
                    "cidade": info_loja["cidade"]
                }
            elif tipo_info == "horario":
                return {
                    "success": True,
                    "horario": info_loja["horario"]
                }
            elif tipo_info == "contato":
                return {
                    "success": True,
                    "telefone": info_loja["telefone"]
                }
            else:
                return {
                    "success": True,
                    **info_loja
                }
        
        except Exception as e:
            logger.error(f"Erro ao obter informações da loja: {e}")
            return {"success": False, "error": str(e)}
    
    def _criar_agendamento(
        self,
        tipo_servico: str,
        data: str,
        horario: str,
        nome_pet: str,
        observacoes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cria um novo agendamento"""
        try:
            # TODO: Integrar com sistema real de agendamentos
            
            # Mock: criar agendamento
            codigo_agendamento = f"AGD{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Formatar data para exibição
            try:
                data_obj = datetime.strptime(data, "%Y-%m-%d")
                data_formatada = data_obj.strftime("%d/%m/%Y")
            except:
                data_formatada = data
            
            return {
                "success": True,
                "codigo": codigo_agendamento,
                "tipo_servico": tipo_servico,
                "data": data_formatada,
                "horario": horario,
                "nome_pet": nome_pet,
                "observacoes": observacoes,
                "status": "confirmado",
                "message": f"✅ Agendamento confirmado!\n\nCódigo: {codigo_agendamento}\nServiço: {tipo_servico.title()}\nPet: {nome_pet}\nData: {data_formatada} às {horario}"
            }
        
        except Exception as e:
            logger.error(f"Erro ao criar agendamento: {e}")
            return {"success": False, "error": str(e)}
    
    def _adicionar_ao_carrinho(
        self,
        produto_id: str,
        quantidade: int = 1
    ) -> Dict[str, Any]:
        """Adiciona produto ao carrinho"""
        try:
            # TODO: Implementar carrinho real (Redis ou banco temporário)
            
            # Mock: buscar produto
            produto = {
                "id": produto_id,
                "nome": "Ração Golden 15kg",
                "preco": 189.90
            }
            
            subtotal = produto["preco"] * quantidade
            
            return {
                "success": True,
                "produto": produto["nome"],
                "quantidade": quantidade,
                "subtotal": subtotal,
                "message": f"✅ Adicionado ao carrinho:\n{quantidade}x {produto['nome']}\nSubtotal: R$ {subtotal:.2f}"
            }
        
        except Exception as e:
            logger.error(f"Erro ao adicionar ao carrinho: {e}")
            return {"success": False, "error": str(e)}
    
    def _ver_carrinho(
        self,
        telefone: str
    ) -> Dict[str, Any]:
        """Mostra carrinho do cliente"""
        try:
            # TODO: Buscar carrinho real
            
            # Mock: carrinho vazio
            carrinho_mock = {
                "itens": [
                    {
                        "produto": "Ração Golden 15kg",
                        "quantidade": 2,
                        "preco_unitario": 189.90,
                        "subtotal": 379.80
                    }
                ],
                "total": 379.80
            }
            
            if not carrinho_mock["itens"]:
                return {
                    "success": True,
                    "itens": [],
                    "total": 0,
                    "message": "🛒 Carrinho vazio"
                }
            
            return {
                "success": True,
                **carrinho_mock,
                "message": f"🛒 Seu carrinho:\n\n{self._formatar_carrinho(carrinho_mock)}"
            }
        
        except Exception as e:
            logger.error(f"Erro ao ver carrinho: {e}")
            return {"success": False, "error": str(e)}
    
    def _calcular_frete(
        self,
        cep: str
    ) -> Dict[str, Any]:
        """Calcula frete"""
        try:
            # TODO: Integrar com API de frete (Correios, Melhor Envio)
            
            cep_limpo = cep.replace("-", "").replace(".", "")
            
            # Mock: opções de frete
            opcoes_frete = [
                {
                    "tipo": "PAC",
                    "prazo": "5-7 dias úteis",
                    "valor": 15.00
                },
                {
                    "tipo": "SEDEX",
                    "prazo": "2-3 dias úteis",
                    "valor": 25.00
                },
                {
                    "tipo": "Entrega Local",
                    "prazo": "1 dia útil",
                    "valor": 10.00
                }
            ]
            
            return {
                "success": True,
                "cep": cep_limpo,
                "opcoes": opcoes_frete,
                "message": "📦 Opções de frete:\n\n" + "\n".join([
                    f"• {opt['tipo']}: R$ {opt['valor']:.2f} ({opt['prazo']})"
                    for opt in opcoes_frete
                ])
            }
        
        except Exception as e:
            logger.error(f"Erro ao calcular frete: {e}")
            return {"success": False, "error": str(e)}
    
    def _finalizar_pedido(
        self,
        telefone: str,
        forma_pagamento: str,
        cep_entrega: Optional[str] = None
    ) -> Dict[str, Any]:
        """Finaliza pedido e gera pagamento"""
        try:
            # TODO: Integrar com sistema real de pedidos e pagamento
            
            # Mock: criar pedido
            codigo_pedido = f"PED{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Valores mock
            subtotal = 379.80
            frete = 15.00
            total = subtotal + frete
            
            resultado = {
                "success": True,
                "codigo_pedido": codigo_pedido,
                "forma_pagamento": forma_pagamento,
                "subtotal": subtotal,
                "frete": frete,
                "total": total,
                "status": "aguardando_pagamento"
            }
            
            # Gerar pagamento conforme forma escolhida
            if forma_pagamento == "pix":
                resultado["pix_qrcode"] = "00020126580014br.gov.bcb.pix..."
                resultado["pix_copia_cola"] = "00020126580014br.gov.bcb.pix..."
                resultado["message"] = f"""✅ Pedido criado!

Código: {codigo_pedido}
Subtotal: R$ {subtotal:.2f}
Frete: R$ {frete:.2f}
Total: R$ {total:.2f}

💳 PIX - Copie e cole o código:
{resultado['pix_copia_cola']}

Válido por 30 minutos."""
            
            elif forma_pagamento == "cartao":
                resultado["link_pagamento"] = f"https://pay.exemplo.com/{codigo_pedido}"
                resultado["message"] = f"""✅ Pedido criado!

Código: {codigo_pedido}
Total: R$ {total:.2f}

💳 Pague com cartão:
{resultado['link_pagamento']}"""
            
            else:  # dinheiro
                resultado["message"] = f"""✅ Pedido confirmado!

Código: {codigo_pedido}
Total: R$ {total:.2f}

💵 Pagamento na entrega
Previsão: 1-2 dias úteis"""
            
            return resultado
        
        except Exception as e:
            logger.error(f"Erro ao finalizar pedido: {e}")
            return {"success": False, "error": str(e)}
    
    def _formatar_carrinho(self, carrinho: Dict[str, Any]) -> str:
        """Formata carrinho para mensagem"""
        linhas = []
        for item in carrinho["itens"]:
            linhas.append(
                f"{item['quantidade']}x {item['produto']}\n"
                f"R$ {item['preco_unitario']:.2f} cada = R$ {item['subtotal']:.2f}"
            )
        
        linhas.append(f"\n━━━━━━━━━━━━━━━━")
        linhas.append(f"Total: R$ {carrinho['total']:.2f}")
        
        return "\n".join(linhas)
