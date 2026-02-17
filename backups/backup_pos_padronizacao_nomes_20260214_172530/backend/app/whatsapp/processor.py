"""
Message Processor - Orquestrador Principal

Orquestra todo o fluxo de processamento:
1. Classificar intenção
2. Construir contexto
3. Decidir ação
4. Chamar IA (se necessário)
5. Executar functions (se chamadas)
6. Enviar resposta
7. Registrar métricas
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.ai.intent_classifier import IntentClassifier, IntentRouter
from app.ai.context_builder import ContextBuilder
from app.ai.llm_client import LLMClient, PromptBuilder, AVAILABLE_FUNCTIONS
from app.whatsapp.sender import send_whatsapp_message
from app.whatsapp.models import WhatsAppSession, WhatsAppMessage, WhatsAppMetric, TenantWhatsAppConfig

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Processador principal de mensagens WhatsApp.
    """
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        
        # Buscar config
        self.config = db.query(TenantWhatsAppConfig).filter(
            TenantWhatsAppConfig.tenant_id == tenant_id
        ).first()
        
        if not self.config or not self.config.openai_api_key:
            raise ValueError(f"Tenant {tenant_id} sem OpenAI API key")
        
        # Inicializar componentes
        self.intent_classifier = IntentClassifier(self.config.openai_api_key)
        self.context_builder = ContextBuilder(db)
        self.llm_client = LLMClient(self.config.openai_api_key)
        self.router = IntentRouter()
    
    async def process_message(
        self,
        session_id: str,
        message_id: str,
        message_content: str
    ) -> Dict[str, Any]:
        """
        Processa mensagem completa.
        
        Args:
            session_id: ID da sessão
            message_id: ID da mensagem no banco
            message_content: Conteúdo da mensagem
            
        Returns:
            Resultado do processamento
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"🔄 Processando mensagem: session={session_id}")
            
            # 0. Verificar se auto-response está habilitado
            if not self.config.auto_response_enabled:
                logger.info("Auto-response desabilitado")
                return {"action": "skipped", "reason": "auto_response_disabled"}
            
            # 1. Construir contexto
            context = await self.context_builder.build_context(
                tenant_id=self.tenant_id,
                session_id=session_id,
                message=message_content
            )
            
            # 2. Classificar intenção
            intent_result = await self.intent_classifier.classify(
                message=message_content,
                context=context
            )
            
            intent = intent_result["intent"]
            confidence = intent_result["confidence"]
            
            # Atualizar mensagem com intent detectado
            msg = self.db.query(WhatsAppMessage).get(message_id)
            if msg:
                msg.intent_detected = intent
                self.db.commit()
            
            # Atualizar sessão com último intent
            session = self.db.query(WhatsAppSession).get(session_id)
            if session:
                session.last_intent = intent
                self.db.commit()
            
            # 3. Verificar se deve transferir para humano
            if self.router.should_transfer_to_human(intent, confidence):
                return await self._transfer_to_human(session_id, intent)
            
            # 4. Resposta rápida (sem IA) para intents simples
            quick_response = self.router.get_quick_response(
                intent,
                bot_name=self.config.bot_name or "Assistente"
            )
            
            if quick_response:
                return await self._send_response(
                    session_id=session_id,
                    response=quick_response,
                    intent=intent,
                    model_used="quick_response",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0
                )
            
            # 5. Processar com IA
            return await self._process_with_ai(
                session_id=session_id,
                message_content=message_content,
                context=context,
                intent=intent
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {e}")
            return {"action": "error", "error": str(e)}
        
        finally:
            # Registrar métrica
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            await self._log_metric("processing_time", processing_time)
    
    # ========================================================================
    # PROCESSAMENTO COM IA
    # ========================================================================
    
    async def _process_with_ai(
        self,
        session_id: str,
        message_content: str,
        context: Dict[str, Any],
        intent: str
    ) -> Dict[str, Any]:
        """
        Processa mensagem com IA (GPT).
        """
        try:
            # 1. Construir system prompt
            system_prompt = PromptBuilder.build_system_prompt(context)
            
            # 2. Construir histórico
            history_messages = PromptBuilder.format_conversation_history(
                context.get("historico_conversa", [])
            )
            
            # 3. Mensagem atual
            current_message = {"role": "user", "content": message_content}
            
            # 4. Montar messages completo
            messages = [
                {"role": "system", "content": system_prompt},
                *history_messages,
                current_message
            ]
            
            # 5. Decidir modelo
            model = None
            if self.router.should_use_advanced_model(intent, context):
                model = "gpt-4-turbo-preview"  # Força modelo avançado
            
            # 6. Chamar LLM
            response = await self.llm_client.chat_completion(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=500,
                functions=AVAILABLE_FUNCTIONS,
                function_call="auto"
            )
            
            # 7. Verificar se chamou function
            if response.get("tool_calls"):
                return await self._handle_function_calls(
                    session_id=session_id,
                    tool_calls=response["tool_calls"],
                    context=context,
                    messages=messages,
                    response=response
                )
            
            # 8. Resposta direta (sem function call)
            return await self._send_response(
                session_id=session_id,
                response=response["content"],
                intent=intent,
                model_used=response["model_used"],
                tokens_input=response["tokens_input"],
                tokens_output=response["tokens_output"],
                processing_time_ms=response["processing_time_ms"]
            )
            
        except Exception as e:
            logger.error(f"Erro no processamento IA: {e}")
            # Fallback
            return await self._send_response(
                session_id=session_id,
                response="Desculpe, tive um problema técnico. Pode repetir sua pergunta? 🙏",
                intent=intent,
                model_used="fallback",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0
            )
    
    # ========================================================================
    # FUNCTION CALLING
    # ========================================================================
    
    async def _handle_function_calls(
        self,
        session_id: str,
        tool_calls: list,
        context: Dict,
        messages: list,
        response: Dict
    ) -> Dict[str, Any]:
        """
        Executa function calls e retorna resposta final.
        """
        logger.info(f"🔧 Function calls: {[tc['function'] for tc in tool_calls]}")
        
        # Executar cada function
        function_results = []
        
        for tool_call in tool_calls:
            function_name = tool_call["function"]
            arguments = tool_call["arguments"]
            
            # Executar function
            result = await self._execute_function(
                function_name=function_name,
                arguments=arguments,
                context=context,
                session_id=session_id
            )
            
            function_results.append({
                "tool_call_id": tool_call["id"],
                "role": "tool",
                "name": function_name,
                "content": str(result)
            })
        
        # Chamar IA novamente com resultados das functions
        messages.extend(function_results)
        
        final_response = await self.llm_client.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        # Enviar resposta final
        return await self._send_response(
            session_id=session_id,
            response=final_response["content"],
            intent="function_executed",
            model_used=final_response["model_used"],
            tokens_input=response["tokens_input"] + final_response["tokens_input"],
            tokens_output=response["tokens_output"] + final_response["tokens_output"],
            processing_time_ms=response["processing_time_ms"] + final_response["processing_time_ms"]
        )
    
    async def _execute_function(
        self,
        function_name: str,
        arguments: Dict,
        context: Dict,
        session_id: str
    ) -> Any:
        """
        Executa function call usando handlers reais.
        """
        logger.info(f"🔧 Executando function: {function_name}({arguments})")
        
        # Importar handlers
        from app.whatsapp.function_handlers import execute_function
        
        # Executar function real
        try:
            result = execute_function(
                function_name=function_name,
                db=self.db,
                tenant_id=self.tenant_id,
                session_id=session_id,
                **arguments
            )
            
            logger.info(f"✅ Function {function_name} executada: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao executar {function_name}: {e}")
            return {"error": str(e)}
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    async def _send_response(
        self,
        session_id: str,
        response: str,
        intent: str,
        model_used: str,
        tokens_input: int,
        tokens_output: int,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """
        Envia resposta via WhatsApp e registra no banco.
        """
        # Enviar via WhatsApp
        message = await send_whatsapp_message(
            db=self.db,
            tenant_id=self.tenant_id,
            session_id=session_id,
            message=response
        )
        
        if not message:
            logger.error("Falha ao enviar mensagem")
            return {"action": "error", "error": "send_failed"}
        
        # Atualizar mensagem com métricas de IA
        message.model_used = model_used
        message.tokens_input = tokens_input
        message.tokens_output = tokens_output
        message.processing_time_ms = processing_time_ms
        self.db.commit()
        
        # Registrar métricas
        await self._log_metric("message_sent", 1)
        await self._log_metric("tokens_used", tokens_input + tokens_output)
        
        logger.info(f"✅ Resposta enviada: {len(response)} chars")
        
        return {
            "action": "responded",
            "message_id": message.id,
            "intent": intent,
            "model": model_used,
            "tokens": tokens_input + tokens_output
        }
    
    async def _transfer_to_human(self, session_id: str, reason: str) -> Dict[str, Any]:
        """
        Transfere conversa para atendente humano.
        """
        session = self.db.query(WhatsAppSession).get(session_id)
        if session:
            session.status = "waiting_human"
            self.db.commit()
        
        # Enviar mensagem de transferência
        await send_whatsapp_message(
            db=self.db,
            tenant_id=self.tenant_id,
            session_id=session_id,
            message="Um momento! Estou transferindo você para um atendente humano. ⏳"
        )
        
        logger.info(f"👤 Transferido para humano: {reason}")
        
        return {"action": "transferred_to_human", "reason": reason}
    
    async def _log_metric(self, metric_type: str, value: float):
        """Registra métrica no banco."""
        try:
            metric = WhatsAppMetric(
                tenant_id=self.tenant_id,
                metric_type=metric_type,
                value=value,
                timestamp=datetime.utcnow()
            )
            self.db.add(metric)
            self.db.commit()
        except Exception as e:
            logger.warning(f"Erro ao registrar métrica: {e}")
