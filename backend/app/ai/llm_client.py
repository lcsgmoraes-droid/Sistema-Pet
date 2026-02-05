"""
LLM Client - OpenAI Integration

Cliente para comunicação com OpenAI (GPT-4o-mini / GPT-4.1).
Suporta function calling, seleção inteligente de modelo, streaming.
"""
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from openai import AsyncOpenAI
import json

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Cliente OpenAI com seleção inteligente de modelo.
    """
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.default_model = "gpt-4o-mini"
        self.advanced_model = "gpt-4-turbo-preview"  # ou gpt-4.1 quando disponível
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        functions: Optional[List[Dict]] = None,
        function_call: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chamada de chat completion.
        
        Args:
            messages: Lista de mensagens (system, user, assistant)
            model: Modelo a usar (None = auto-select)
            temperature: Criatividade (0.0-2.0)
            max_tokens: Máximo de tokens na resposta
            functions: Lista de funções disponíveis (function calling)
            function_call: "auto", "none", ou {"name": "function_name"}
            
        Returns:
            Response completo com métricas
        """
        start_time = time.time()
        
        try:
            # Selecionar modelo
            model = model or self._select_model(messages)
            
            # Preparar kwargs
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Adicionar functions se fornecidas
            if functions:
                kwargs["tools"] = [
                    {"type": "function", "function": f} for f in functions
                ]
                if function_call:
                    kwargs["tool_choice"] = function_call
            
            # Fazer chamada
            response = await self.client.chat.completions.create(**kwargs)
            
            # Calcular métricas
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Extrair resposta
            message = response.choices[0].message
            
            result = {
                "content": message.content,
                "role": message.role,
                "model_used": model,
                "tokens_input": response.usage.prompt_tokens,
                "tokens_output": response.usage.completion_tokens,
                "tokens_total": response.usage.total_tokens,
                "processing_time_ms": processing_time_ms,
                "finish_reason": response.choices[0].finish_reason
            }
            
            # Se usou function calling
            if hasattr(message, 'tool_calls') and message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "function": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    }
                    for tc in message.tool_calls
                ]
            
            logger.info(
                f"✅ LLM response: model={model}, "
                f"tokens={result['tokens_total']}, "
                f"time={processing_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na chamada LLM: {e}")
            raise
    
    def _select_model(self, messages: List[Dict[str, str]]) -> str:
        """
        Seleciona modelo baseado na complexidade da conversa.
        
        Regras:
        - GPT-4o-mini (80% dos casos): consultas simples, FAQ, classificação
        - GPT-4.1 (20%): vendas complexas, múltiplos produtos, recomendações
        """
        # Contar mensagens
        message_count = len([m for m in messages if m.get("role") == "user"])
        
        # Buscar indicadores de complexidade
        last_user_message = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            ""
        )
        
        complexity_indicators = [
            "recomend",
            "melhor",
            "compar",
            "diferença",
            "qual devo",
            "qual escolher",
            "vale a pena",
            "sugest"
        ]
        
        is_complex = any(
            indicator in last_user_message.lower()
            for indicator in complexity_indicators
        )
        
        # Decisão
        if is_complex or message_count > 5:
            return self.advanced_model
        
        return self.default_model
    
    # ========================================================================
    # STREAMING (para futuro)
    # ========================================================================
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        callback: Optional[Callable] = None
    ):
        """
        Chat completion com streaming (para UI responsiva futura).
        
        Args:
            messages: Lista de mensagens
            model: Modelo a usar
            callback: Função chamada a cada chunk
        """
        model = model or self.default_model
        
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        
        full_response = ""
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                
                if callback:
                    await callback(content)
        
        return full_response


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

class PromptBuilder:
    """
    Constrói prompts estruturados para a IA.
    """
    
    @staticmethod
    def build_system_prompt(context: Dict[str, Any]) -> str:
        """
        Constrói system prompt com contexto do ERP.
        """
        tenant = context.get("tenant", {})
        cliente = context.get("cliente")
        produtos = context.get("produtos_relevantes", [])
        politicas = tenant.get("politicas", {})
        
        # Nome do bot
        bot_name = tenant.get("bot_name", "Assistente")
        
        # Tom da conversa
        tone_map = {
            "friendly": "Seja cordial, use emojis moderadamente 🐾, mostre empatia com os pets",
            "formal": "Seja profissional e objetivo, evite emojis",
            "casual": "Seja descontraído e próximo, use linguagem coloquial"
        }
        tone_instruction = tone_map.get(tenant.get("tone", "friendly"), tone_map["friendly"])
        
        # Montar prompt
        prompt = f"""Você é {bot_name}, assistente de vendas de um pet shop.

REGRAS ABSOLUTAS:
1. NUNCA invente produtos que não estão no catálogo fornecido
2. NUNCA ofereça: {', '.join(politicas.get('proibido_vender', []))}
3. SEMPRE confirme endereço antes de finalizar pedido
4. Se não souber algo, seja honesto e ofereça transferir para humano
5. Valores e estoque podem mudar - sempre mencione "consulte disponibilidade atual"

INFORMAÇÕES DO CLIENTE:
{f"- Nome: {cliente['nome']}" if cliente else "- Cliente novo (não identificado)"}
{f"- Último pedido: R$ {cliente['ultimo_pedido']['valor']:.2f} em {cliente['ultimo_pedido']['data'][:10]}" if cliente and cliente.get('ultimo_pedido') else ""}
{f"- Cliente fiel ({cliente['total_compras_3m']} compras em 3 meses)" if cliente and cliente.get('cliente_fiel') else ""}

PRODUTOS DISPONÍVEIS:
{PromptBuilder._format_produtos(produtos)}

POLÍTICAS DA LOJA:
- Entrega mínima: R$ {politicas.get('minimo_entrega', 50):.2f}
- Formas de pagamento: {', '.join(politicas.get('formas_pagamento', []))}
- Áreas de entrega: {', '.join(politicas.get('areas_entrega', []))}

ESTILO DE COMUNICAÇÃO:
{tone_instruction}

IMPORTANTE:
- Sempre pergunte sobre o pet do cliente (nome, idade, porte, raça)
- Sugira produtos baseados nas necessidades do pet
- Se cliente perguntar sobre produto não listado, diga que vai verificar disponibilidade
"""
        
        return prompt.strip()
    
    @staticmethod
    def _format_produtos(produtos: List[Dict[str, Any]]) -> str:
        """Formata lista de produtos para o prompt."""
        if not produtos:
            return "Nenhum produto específico no momento (busque no sistema se necessário)"
        
        formatted = []
        for p in produtos[:5]:  # Máx 5 produtos
            linha = f"• {p['nome']}"
            if p.get('preco'):
                linha += f" - R$ {p['preco']:.2f}"
            if p.get('estoque'):
                linha += f" ({p['estoque']} em estoque)"
            if p.get('descricao'):
                linha += f"\n  {p['descricao'][:100]}"
            formatted.append(linha)
        
        return "\n".join(formatted)
    
    @staticmethod
    def format_conversation_history(historico: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Formata histórico de conversa para formato OpenAI.
        """
        messages = []
        
        for msg in historico:
            role = "user" if msg["tipo"] == "recebida" else "assistant"
            messages.append({
                "role": role,
                "content": msg["conteudo"]
            })
        
        return messages


# ============================================================================
# FUNCTION DEFINITIONS (para function calling)
# ============================================================================

AVAILABLE_FUNCTIONS = [
    {
        "name": "buscar_produto",
        "description": "Busca produtos no catálogo por nome, categoria ou descrição",
        "parameters": {
            "type": "object",
            "properties": {
                "termo": {
                    "type": "string",
                    "description": "Termo de busca (ex: 'ração golden', 'shampoo para cachorro')"
                },
                "categoria": {
                    "type": "string",
                    "description": "Categoria específica (opcional)",
                    "enum": ["Ração", "Brinquedo", "Higiene", "Acessório", "Medicamento"]
                }
            },
            "required": ["termo"]
        }
    },
    {
        "name": "consultar_estoque",
        "description": "Verifica disponibilidade em estoque de um produto específico",
        "parameters": {
            "type": "object",
            "properties": {
                "produto_id": {
                    "type": "string",
                    "description": "ID do produto"
                }
            },
            "required": ["produto_id"]
        }
    },
    {
        "name": "calcular_frete",
        "description": "Calcula valor e prazo de entrega para um endereço",
        "parameters": {
            "type": "object",
            "properties": {
                "cep": {
                    "type": "string",
                    "description": "CEP de entrega (ex: '01310-100')"
                },
                "valor_pedido": {
                    "type": "number",
                    "description": "Valor total do pedido"
                }
            },
            "required": ["cep"]
        }
    },
    {
        "name": "criar_pedido",
        "description": "Cria um novo pedido para o cliente",
        "parameters": {
            "type": "object",
            "properties": {
                "produtos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "produto_id": {"type": "string"},
                            "quantidade": {"type": "integer"}
                        }
                    },
                    "description": "Lista de produtos e quantidades"
                },
                "forma_pagamento": {
                    "type": "string",
                    "enum": ["Dinheiro", "Pix", "Cartão Débito", "Cartão Crédito"]
                },
                "endereco_entrega": {
                    "type": "string",
                    "description": "Endereço completo de entrega"
                }
            },
            "required": ["produtos", "forma_pagamento"]
        }
    },
    {
        "name": "transferir_para_humano",
        "description": "Transfere conversa para atendente humano",
        "parameters": {
            "type": "object",
            "properties": {
                "motivo": {
                    "type": "string",
                    "description": "Motivo da transferência"
                }
            },
            "required": ["motivo"]
        }
    }
]
