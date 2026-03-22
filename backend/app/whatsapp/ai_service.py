"""
Serviço Principal de IA - Integração completa com OpenAI
Gerencia conversas, detecção de intenções, tool calling e respostas
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from openai import OpenAI
import logging
import time
from datetime import datetime

from app.whatsapp.models import (
    TenantWhatsAppConfig,
    WhatsAppSession,
    WhatsAppMessage
)
from app.whatsapp.intents import detect_intent_with_confidence, IntentType
from app.whatsapp.context_manager import context_manager, ConversationContext
from app.whatsapp.tools import TOOLS_DEFINITIONS, ToolExecutor
from app.whatsapp.templates import ResponseFormatter
from app.whatsapp.sentiment import get_sentiment_analyzer
from app.whatsapp.handoff_manager import get_handoff_manager

logger = logging.getLogger(__name__)


class AIService:
    """Serviço de IA para WhatsApp"""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.config = self._load_config()
        self.client = self._initialize_openai()
        self.tool_executor = ToolExecutor(db, tenant_id)
        self.formatter = ResponseFormatter(loja_nome=self.config.bot_name if self.config else "Pet Shop")
        self.sentiment_analyzer = get_sentiment_analyzer()
        self.handoff_manager = get_handoff_manager(db, tenant_id)
    
    def _load_config(self) -> Optional[TenantWhatsAppConfig]:
        """Carrega configuração do tenant"""
        config = self.db.query(TenantWhatsAppConfig).filter(
            TenantWhatsAppConfig.tenant_id == self.tenant_id
        ).first()
        
        if not config:
            logger.error(f"Configuração WhatsApp não encontrada para tenant {self.tenant_id}")
        
        return config
    
    def _initialize_openai(self) -> Optional[OpenAI]:
        """Inicializa cliente OpenAI"""
        if not self.config or not self.config.openai_api_key:
            logger.error("OpenAI API Key não configurada")
            return None
        
        try:
            client = OpenAI(api_key=self.config.openai_api_key)
            return client
        except Exception as e:
            logger.error(f"Erro ao inicializar OpenAI: {e}")
            return None
    
    async def process_message(
        self,
        message: str,
        phone_number: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa mensagem recebida e gera resposta
        
        Args:
            message: Texto da mensagem do usuário
            phone_number: Telefone do usuário
            session_id: ID da sessão (opcional)
            
        Returns:
            Dict com resposta e metadados
        """
        start_time = time.time()
        
        try:
            # 1. Detectar intenção
            intent, confidence = detect_intent_with_confidence(message)
            logger.info(f"Intenção detectada: {intent} (confiança: {confidence:.2f})")
            
            # 2. Obter/criar contexto
            context = context_manager.get_or_create_context(
                db=self.db,
                phone_number=phone_number,
                tenant_id=self.tenant_id,
                session_id=session_id
            )
            
            # Adicionar mensagem do usuário ao contexto
            context.add_message("user", message, intent)
            context.current_intent = intent
            
            # 2.5. Analisar sentimento (Sprint 4)
            sentiment_result = self.sentiment_analyzer.analyze(
                message,
                conversation_history=[m["content"] for m in context.messages if m["role"] == "user"]
            )
            logger.info(f"😊 Sentimento: {sentiment_result['label']} (score: {sentiment_result['score']})")
            
            # 2.6. Verificar se precisa handoff
            session = self.db.query(WhatsAppSession).filter(
                WhatsAppSession.phone_number == phone_number,
                WhatsAppSession.tenant_id == self.tenant_id
            ).first()
            
            if session and sentiment_result.get("should_handoff"):
                # Criar handoff
                handoff = self.handoff_manager.create_handoff(
                    session_id=session.id,
                    phone_number=phone_number,
                    reason=sentiment_result.get("handoff_reason", "auto_sentiment"),
                    priority=self._calculate_priority(sentiment_result),
                    sentiment_score=sentiment_result["score"],
                    sentiment_label=sentiment_result["label"],
                    reason_details=f"Triggers: {', '.join(sentiment_result.get('triggers', []))}"
                )
                
                logger.warning(f"🚨 Handoff criado: {handoff.id} (reason: {handoff.reason})")
                
                return {
                    "success": True,
                    "response": self.formatter.format_handoff_created(handoff.priority),
                    "intent": intent.value,
                    "confidence": confidence,
                    "processing_time": time.time() - start_time,
                    "tokens_used": 0,
                    "model_used": "",
                    "requires_human": True,
                    "handoff_id": handoff.id,
                    "sentiment": sentiment_result
                }
            
            # 3. Verificar se deve responder (regras de negócio)
            should_respond, reason = self._should_auto_respond(context, intent)
            logger.info(f"🔍 Should respond: {should_respond}, reason: {reason}")
            
            if not should_respond:
                logger.warning(f"⚠️ Não respondendo: {reason}")
                return {
                    "success": False,
                    "error": f"Não respondendo: {reason}",
                    "message": "Não respondendo automaticamente",
                    "reason": reason,
                    "requires_human": True,
                    "intent": intent.value,
                    "confidence": confidence,
                    "processing_time": time.time() - start_time,
                    "tokens_used": 0,
                    "model_used": "",
                    "response": self.formatter.format_error("Transferindo para atendente humano")
                }
            
            # 4. Gerar resposta com IA
            response_text, metadata = await self._generate_ai_response(
                message=message,
                intent=intent,
                context=context
            )
            
            # 5. Adicionar resposta ao contexto
            context.add_message("assistant", response_text)
            context_manager.update_context(context)
            
            # 6. Calcular métricas
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "response": response_text,
                "intent": intent.value,
                "confidence": confidence,
                "processing_time": processing_time,
                "tokens_used": metadata.get("tokens_used", 0),
                "model_used": metadata.get("model", ""),
                "requires_human": metadata.get("requires_human", False)
            }
        
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
            error_msg = str(e)
            if "401" in error_msg or "Incorrect API key" in error_msg:
                error_msg = "OpenAI API Key inválida"
            elif "429" in error_msg:
                error_msg = "Limite de requisições OpenAI excedido"
            return {
                "success": False,
                "error": error_msg,
                "response": self.formatter.format_error("Tive um problema ao processar sua mensagem"),
                "intent": intent.value if 'intent' in locals() else "desconhecido",
                "confidence": confidence if 'confidence' in locals() else 0.0,
                "processing_time": time.time() - start_time,
                "tokens_used": 0,
                "model_used": ""
            }
    
    def _should_auto_respond(
        self,
        context: ConversationContext,
        intent: IntentType
    ) -> tuple[bool, str]:
        """
        Verifica se deve responder automaticamente ou transferir para humano
        
        Returns:
            Tupla (should_respond: bool, reason: str)
        """
        if not self.config:
            return False, "Configuração não encontrada"
        
        # Verificar se auto response está ativado
        if not self.config.auto_response_enabled:
            return False, "Auto response desativado"
        
        # Verificar horário comercial (se configurado)
        if self.config.working_hours_start and self.config.working_hours_end:
            if not self._is_within_working_hours():
                return False, "Fora do horário comercial"
        
        # Reclamações sempre vão para humano
        if intent == IntentType.RECLAMACAO:
            return False, "Reclamação detectada"
        
        # Verificar mensagens repetidas (possível frustração)
        repeated_count = self._count_repeated_messages(context)
        if repeated_count >= 3:
            return False, "Mensagem repetida 3x"
        
        return True, ""
    
    def _is_within_working_hours(self) -> bool:
        """Verifica se está dentro do horário comercial"""
        if not self.config or not self.config.working_hours_start or not self.config.working_hours_end:
            return True
        
        now = datetime.now()
        current_time = now.time()
        
        # Comparar horários
        if self.config.working_hours_start <= current_time <= self.config.working_hours_end:
            return True
        
        return False
    
    def _count_repeated_messages(self, context: ConversationContext) -> int:
        """Conta quantas vezes a última mensagem foi repetida"""
        if not context.messages:
            return 0
        
        last_msg = context.messages[-1]["content"].lower().strip()
        count = 0
        
        # Verificar últimas 5 mensagens do usuário
        user_messages = [m for m in context.messages if m["role"] == "user"][-5:]
        
        for msg in user_messages:
            if msg["content"].lower().strip() == last_msg:
                count += 1
        
        return count
    
    def _calculate_priority(self, sentiment_result: Dict) -> str:
        """Calcula prioridade baseado no sentimento"""
        score = float(sentiment_result.get("score", 0))
        
        if score <= -0.8:
            return "urgent"
        elif score <= -0.6:
            return "high"
        elif score <= -0.3:
            return "medium"
        else:
            return "low"
    
    async def _generate_ai_response(
        self,
        message: str,
        intent: IntentType,
        context: ConversationContext
    ) -> tuple[str, Dict[str, Any]]:
        """
        Gera resposta usando OpenAI
        
        Returns:
            Tupla (resposta: str, metadata: dict)
        """
        if not self.client:
            return self.formatter.format_error("Serviço temporariamente indisponível"), {}
        
        # Construir mensagens para a API
        messages = self._build_messages(message, intent, context)
        
        # Modelo a usar
        model = self.config.model_preference or "gpt-4o-mini"
        
        try:
            # Primeira chamada com tools
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS_DEFINITIONS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=500
            )
            
            response_message = response.choices[0].message
            tokens_used = response.usage.total_tokens
            
            # Verificar se IA quer chamar tools
            tool_calls = response_message.tool_calls
            
            if tool_calls:
                logger.info(f"IA solicitou {len(tool_calls)} tool calls")
                
                # Adicionar resposta da IA nas mensagens
                messages.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in tool_calls
                    ]
                })
                
                # Executar cada tool call
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    
                    try:
                        import json
                        function_args = json.loads(tool_call.function.arguments)
                    except:
                        function_args = {}
                    
                    logger.info(f"Executando tool: {function_name} com args: {function_args}")
                    
                    # Executar tool
                    tool_result = self.tool_executor.execute_tool(
                        tool_name=function_name,
                        arguments=function_args
                    )
                    
                    logger.info(f"Resultado da tool {function_name}: {tool_result}")
                    
                    # Adicionar resultado nas mensagens
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })
                
                # Segunda chamada com resultados das tools
                second_response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
                
                final_response = second_response.choices[0].message.content
                tokens_used += second_response.usage.total_tokens
            
            else:
                # Resposta direta sem tools
                final_response = response_message.content
            
            metadata = {
                "tokens_used": tokens_used,
                "model": model,
                "tool_calls": len(tool_calls) if tool_calls else 0,
                "requires_human": False
            }
            
            return final_response, metadata
        
        except Exception as e:
            logger.error(f"Erro na chamada OpenAI: {e}", exc_info=True)
            return self.formatter.format_error(str(e)), {}
    
    def _build_messages(
        self,
        message: str,
        intent: IntentType,
        context: ConversationContext
    ) -> List[Dict[str, str]]:
        """Constrói mensagens para enviar à OpenAI"""
        
        # System prompt
        system_prompt = self._build_system_prompt(intent, context)
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Adicionar histórico recente
        for msg in context.get_last_messages(limit=5):
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Mensagem atual (se não estiver no histórico)
        if not messages or messages[-1]["content"] != message:
            messages.append({
                "role": "user",
                "content": message
            })
        
        return messages
    
    def _build_system_prompt(
        self,
        intent: IntentType,
        context: ConversationContext
    ) -> str:
        """Constrói system prompt personalizado"""
        
        # Prompt base
        base_prompt = f"""Voce e {self.config.bot_name}, assistente virtual de um pet shop.

**Seu papel:**
- Ajudar clientes com produtos, agendamentos, entregas e duvidas
- Ser {self.config.tone if self.config.tone else 'amigavel'} e prestativo
- Soar humano e consultivo, sem tom robotico
- Respostas curtas e diretas (maximo 3 paragrafos)
- SEMPRE use as tools disponiveis quando precisar buscar informacoes reais

**Regras importantes:**
- Sempre que o cliente perguntar sobre produtos, USE a tool buscar_produtos
- Em produtos, tente termos equivalentes (marca, sabor, peso, SKU, EAN) antes de concluir que nao encontrou
- Para agendamentos, USE a tool verificar_horarios_disponiveis
- Para status de pedidos, USE a tool buscar_status_pedido
- Para informacoes da loja, USE a tool obter_informacoes_loja
- NAO invente informacoes - use as tools para buscar dados reais
- Se nao souber algo, ofereca transferir para atendente humano
- Quando faltar dado, faca apenas uma pergunta objetiva para destravar a conversa
- Ao listar produtos, traga no maximo 3 itens por resposta com nome, preco, estoque e SKU/EAN
"""

        # Adicionar contexto do cliente se disponível
        if context.customer_data:
            customer = context.customer_data
            base_prompt += f"\n**Cliente identificado:**\n"
            base_prompt += f"- Nome: {customer.get('name', 'Não informado')}\n"
            if customer.get('pets'):
                base_prompt += f"- Pets: {', '.join([p['name'] for p in customer['pets']])}\n"
        
        # Adicionar contexto da intenção atual
        intent_contexts = {
            IntentType.SAUDACAO: "Cliente está iniciando conversa. Seja acolhedor!",
            IntentType.PRODUTOS: "Cliente busca produtos. Use a tool buscar_produtos!",
            IntentType.AGENDAMENTO: "Cliente quer agendar. Use a tool verificar_horarios_disponiveis!",
            IntentType.ENTREGA: "Cliente quer rastrear pedido. Use a tool buscar_status_pedido!",
            IntentType.RECLAMACAO: "Cliente está insatisfeito. Seja empático e ofereça transferência para humano.",
            IntentType.DUVIDA: "Cliente tem dúvida. Tente ajudar ou use as tools para buscar informações."
        }
        
        if intent in intent_contexts:
            base_prompt += f"\n**Contexto atual:** {intent_contexts[intent]}\n"
        
        return base_prompt


# Factory function para criar instâncias
def get_ai_service(db: Session, tenant_id: str) -> AIService:
    """Cria instância do AIService"""
    return AIService(db, tenant_id)
