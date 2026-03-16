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
            from app.produtos_models import Produto
            from sqlalchemy import or_

            q = self.db.query(Produto).filter(
                Produto.tenant_id == self.tenant_id,
                Produto.situacao == True,
                Produto.tipo_produto != 'PAI',
                or_(
                    Produto.nome.ilike(f'%{query}%'),
                    Produto.descricao_curta.ilike(f'%{query}%')
                )
            ).limit(limite).all()

            if not q:
                return {
                    "success": True,
                    "produtos": [],
                    "message": f"Nenhum produto encontrado para '{query}'"
                }

            produtos = [
                {
                    "id": str(p.id),
                    "nome": p.nome,
                    "preco": float(p.preco_venda) if p.preco_venda else 0.0,
                    "estoque": float(p.estoque_atual) if p.estoque_atual is not None else 0,
                    "descricao": p.descricao_curta or ""
                }
                for p in q
            ]

            return {
                "success": True,
                "produtos": produtos,
                "total": len(produtos)
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
            from app.vendas_models import Venda
            from app.models import Cliente
            from sqlalchemy import or_

            q = self.db.query(Venda).filter(Venda.tenant_id == self.tenant_id)

            if codigo_pedido:
                q = q.filter(Venda.numero_venda == codigo_pedido)
            elif telefone:
                tel_digits = ''.join(filter(str.isdigit, telefone))
                sufixo = tel_digits[-8:] if len(tel_digits) >= 8 else tel_digits
                q = q.join(Cliente, Venda.cliente_id == Cliente.id).filter(
                    or_(
                        Cliente.celular.ilike(f'%{sufixo}%'),
                        Cliente.telefone.ilike(f'%{sufixo}%')
                    )
                )
            else:
                return {
                    "success": True,
                    "pedidos": [],
                    "message": "Informe o número do pedido ou telefone para consultar"
                }

            vendas = q.order_by(Venda.created_at.desc()).limit(5).all()

            if not vendas:
                return {
                    "success": True,
                    "pedidos": [],
                    "message": "Nenhum pedido encontrado"
                }

            status_label = {
                "aberta": "Em aberto",
                "finalizada": "Finalizada",
                "cancelada": "Cancelada"
            }
            entrega_label = {
                "pendente": "Aguardando retirada",
                "em_rota": "Em rota de entrega",
                "entregue": "Entregue",
                "cancelado": "Entrega cancelada"
            }

            pedidos = [
                {
                    "codigo": v.numero_venda,
                    "data": v.created_at.strftime("%d/%m/%Y") if v.created_at else "",
                    "status": status_label.get(v.status, v.status),
                    "status_entrega": entrega_label.get(v.status_entrega or "", v.status_entrega or "sem entrega"),
                    "total": float(v.total) if v.total else 0.0,
                    "itens": [
                        (i.produto.nome if i.produto else i.servico_descricao or "item")
                        for i in (v.itens or [])
                    ]
                }
                for v in vendas
            ]

            return {
                "success": True,
                "pedidos": pedidos,
                "total": len(pedidos)
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
            from app.vendas_models import Venda
            from app.models import Cliente
            from sqlalchemy import or_

            tel_digits = ''.join(filter(str.isdigit, telefone))
            sufixo = tel_digits[-8:] if len(tel_digits) >= 8 else tel_digits

            vendas = (
                self.db.query(Venda)
                .join(Cliente, Venda.cliente_id == Cliente.id)
                .filter(
                    Venda.tenant_id == self.tenant_id,
                    Venda.status == 'finalizada',
                    or_(
                        Cliente.celular.ilike(f'%{sufixo}%'),
                        Cliente.telefone.ilike(f'%{sufixo}%')
                    )
                )
                .order_by(Venda.created_at.desc())
                .limit(limite)
                .all()
            )

            if not vendas:
                return {
                    "success": True,
                    "compras": [],
                    "message": "Nenhuma compra anterior encontrada"
                }

            compras = [
                {
                    "codigo": v.numero_venda,
                    "data": v.created_at.strftime("%d/%m/%Y") if v.created_at else "",
                    "total": float(v.total) if v.total else 0.0,
                    "itens": [
                        (i.produto.nome if i.produto else i.servico_descricao or "item")
                        for i in (v.itens or [])
                    ]
                }
                for v in vendas
            ]

            return {
                "success": True,
                "compras": compras,
                "total": len(compras)
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
            from app.whatsapp.models import TenantWhatsAppConfig
            from app.models import Tenant

            tenant = self.db.query(Tenant).filter(Tenant.id == self.tenant_id).first()
            wa_config = self.db.query(TenantWhatsAppConfig).filter(
                TenantWhatsAppConfig.tenant_id == self.tenant_id
            ).first()

            nome = (wa_config.bot_name if wa_config and wa_config.bot_name else None) or (tenant.name if tenant else "Pet Shop")

            if tenant:
                partes_end = [p for p in [tenant.endereco, tenant.numero, tenant.bairro] if p]
                endereco = ", ".join(partes_end) if partes_end else "Não informado"
                cidade = f"{tenant.cidade} - {tenant.uf}" if tenant.cidade else "Não informado"
                telefone_loja = tenant.telefone or "Não informado"
            else:
                endereco = "Não informado"
                cidade = "Não informado"
                telefone_loja = "Não informado"

            if wa_config and wa_config.working_hours_start and wa_config.working_hours_end:
                h_ini = wa_config.working_hours_start.strftime("%H:%M")
                h_fim = wa_config.working_hours_end.strftime("%H:%M")
                horario_semana = f"Segunda a Sexta: {h_ini} às {h_fim}"
            elif tenant and tenant.ecommerce_horario_abertura and tenant.ecommerce_horario_fechamento:
                horario_semana = f"Segunda a Sexta: {tenant.ecommerce_horario_abertura} às {tenant.ecommerce_horario_fechamento}"
            else:
                horario_semana = "Horário não informado — entre em contato para confirmar"

            info_loja = {
                "nome": nome,
                "endereco": endereco,
                "cidade": cidade,
                "telefone": telefone_loja,
                "horario": {
                    "semana": horario_semana,
                    "sabado": "Consultar a loja",
                    "domingo": "Consultar a loja"
                }
            }

            if tipo_info == "endereco":
                return {"success": True, "endereco": info_loja["endereco"], "cidade": info_loja["cidade"]}
            elif tipo_info == "horario":
                return {"success": True, "horario": info_loja["horario"]}
            elif tipo_info == "contato":
                return {"success": True, "telefone": info_loja["telefone"]}
            else:
                return {"success": True, **info_loja}

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
