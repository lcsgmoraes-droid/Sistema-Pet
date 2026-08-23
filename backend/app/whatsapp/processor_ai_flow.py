"""Orquestração de IA e function calling do processador de WhatsApp."""

import json
import logging
from typing import Any, Dict, Optional

from app.ai.llm_client import (
    AVAILABLE_FUNCTIONS_PHASE1_READ_ONLY,
    PromptBuilder,
)
from app.whatsapp.conversation_helpers import (
    _build_catalog_response,
    _build_validity_response,
    _build_weight_options_response,
    _filter_unavailable_catalog_products,
    _preserve_explicit_measurements,
    _tool_choice_for_intent,
)
from app.whatsapp.processor_response_flow import _extract_product_media

logger = logging.getLogger(__name__)


class WhatsAppAIFlowMixin:
    """Geração assistida por IA e execução controlada das funções de negócio."""

    async def _process_with_ai(
        self,
        session_id: str,
        message_content: str,
        context: Dict[str, Any],
        intent: str,
        catalog_query_override: Optional[str] = None,
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
                current_message,
            ]

            if catalog_query_override:
                return await self._handle_deterministic_product_lookup(
                    session_id=session_id,
                    catalog_query=catalog_query_override,
                    context=context,
                )

            # 5. Decidir modelo
            model = None
            if self.router.should_use_advanced_model(intent, context):
                model = self.llm_client.advanced_model

            # 6. Chamar LLM
            response = await self.llm_client.chat_completion(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=500,
                functions=AVAILABLE_FUNCTIONS_PHASE1_READ_ONLY,
                function_call=_tool_choice_for_intent(intent),
            )

            # 7. Verificar se chamou function
            if response.get("tool_calls"):
                return await self._handle_function_calls(
                    session_id=session_id,
                    tool_calls=response["tool_calls"],
                    context=context,
                    messages=messages,
                    response=response,
                )

            # 8. Resposta direta (sem function call)
            return await self._send_response(
                session_id=session_id,
                response=response["content"],
                intent=intent,
                model_used=response["model_used"],
                tokens_input=response["tokens_input"],
                tokens_output=response["tokens_output"],
                processing_time_ms=response["processing_time_ms"],
            )

        except Exception as e:
            logger.error(f"Erro no processamento IA: {e}")
            self.db.rollback()
            # Fallback
            return await self._send_response(
                session_id=session_id,
                response="Desculpe, tive um problema técnico. Pode repetir sua pergunta? 🙏",
                intent=intent,
                model_used="fallback",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

    # ========================================================================
    # FUNCTION CALLING
    # ========================================================================

    async def _handle_deterministic_product_lookup(
        self, session_id: str, catalog_query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Lista resultados reais sem permitir que a IA presuma uma compra."""
        result = await self._execute_function(
            function_name="buscar_produto",
            arguments={"termo": catalog_query},
            context=context,
            session_id=session_id,
        )
        result = _filter_unavailable_catalog_products(result)
        self._remember_catalog_search(session_id, catalog_query, result)

        return await self._send_response(
            session_id=session_id,
            response=_build_catalog_response(result, catalog_query),
            intent="function_executed",
            model_used="deterministic_catalog",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
            product_media=_extract_product_media(result),
        )

    async def _handle_deterministic_weight_options_lookup(
        self,
        session_id: str,
        catalog_query: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        result = await self._execute_function(
            function_name="buscar_produto",
            arguments={"termo": catalog_query, "limit": 15},
            context=context,
            session_id=session_id,
        )
        result = _filter_unavailable_catalog_products(result)
        self._remember_catalog_search(session_id, catalog_query, result)
        return await self._send_response(
            session_id=session_id,
            response=_build_weight_options_response(result, catalog_query),
            intent="consulta_pesos_produto",
            model_used="deterministic_weight_options",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
            product_media=_extract_product_media(result),
        )

    async def _handle_deterministic_validity_lookup(
        self,
        session_id: str,
        catalog_query: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        result = await self._execute_function(
            function_name="buscar_produto",
            arguments={"termo": catalog_query, "limit": 10},
            context=context,
            session_id=session_id,
        )
        result = _filter_unavailable_catalog_products(result)
        self._remember_catalog_search(session_id, catalog_query, result)
        response, needs_human = _build_validity_response(result, catalog_query)
        if needs_human:
            return await self._transfer_to_human(
                session_id=session_id,
                reason="product_validity",
                reason_details=(
                    "Validade ausente ou não segura no lote vendável consultado"
                ),
                customer_message=response,
            )
        return await self._send_response(
            session_id=session_id,
            response=response,
            intent="consulta_validade_produto",
            model_used="deterministic_product_validity",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
            product_media=_extract_product_media(result),
        )

    async def _handle_function_calls(
        self,
        session_id: str,
        tool_calls: list,
        context: Dict,
        messages: list,
        response: Dict,
    ) -> Dict[str, Any]:
        """
        Executa function calls e retorna resposta final.
        """
        logger.info(f"🔧 Function calls: {[tc['function'] for tc in tool_calls]}")

        # Executar cada function
        function_results = []
        product_media: list[Dict[str, str]] = []
        catalog_result: Optional[Dict[str, Any]] = None
        catalog_query = "produto solicitado"

        for tool_call in tool_calls:
            function_name = tool_call["function"]
            arguments = dict(tool_call["arguments"])
            if function_name == "buscar_produto":
                arguments["termo"] = _preserve_explicit_measurements(
                    str(arguments.get("termo") or "produto"), messages
                )
                # A categoria sugerida pela IA pode não refletir a categoria
                # cadastrada no ERP e já ocultou embalagens exatas no piloto.
                arguments.pop("categoria", None)

            # Executar function
            result = await self._execute_function(
                function_name=function_name,
                arguments=arguments,
                context=context,
                session_id=session_id,
            )
            if function_name == "buscar_produto":
                result = _filter_unavailable_catalog_products(result)
            product_media.extend(_extract_product_media(result))
            if function_name == "buscar_produto" and isinstance(result, dict):
                catalog_result = result
                catalog_query = str(arguments.get("termo") or catalog_query).strip()

            function_results.append(
                {
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "name": function_name,
                    "content": str(result),
                }
            )

        if catalog_result is not None:
            self._remember_catalog_search(session_id, catalog_query, catalog_result)
            return await self._send_response(
                session_id=session_id,
                response=_build_catalog_response(catalog_result, catalog_query),
                intent="function_executed",
                model_used=response.get("model_used") or "deterministic_catalog",
                tokens_input=response.get("tokens_input", 0),
                tokens_output=response.get("tokens_output", 0),
                processing_time_ms=response.get("processing_time_ms", 0),
                product_media=product_media,
            )

        # Chamar IA novamente com resultados das functions
        # OBRIGATÓRIO: adicionar primeiro a mensagem do assistente com tool_calls
        # (a API da OpenAI exige que toda mensagem "tool" seja precedida por
        #  uma mensagem "assistant" contendo os tool_calls correspondentes)
        messages.append(
            {
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"],
                            "arguments": json.dumps(
                                tc["arguments"], ensure_ascii=False
                            ),
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )
        messages.extend(function_results)

        if product_media and messages and messages[0].get("role") == "system":
            messages[0]["content"] += (
                "\n\nAs fotos dos produtos serão enviadas pelo sistema como anexos do "
                "WhatsApp. Não inclua URLs nem sintaxe Markdown de imagem na resposta."
            )

        final_response = await self.llm_client.chat_completion(
            messages=messages, temperature=0.7, max_tokens=500
        )

        # Enviar resposta final
        return await self._send_response(
            session_id=session_id,
            response=final_response["content"],
            intent="function_executed",
            model_used=final_response["model_used"],
            tokens_input=response["tokens_input"] + final_response["tokens_input"],
            tokens_output=response["tokens_output"] + final_response["tokens_output"],
            processing_time_ms=response["processing_time_ms"]
            + final_response["processing_time_ms"],
            product_media=product_media,
        )

    async def _execute_function(
        self, function_name: str, arguments: Dict, context: Dict, session_id: str
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
                **arguments,
            )

            logger.info(f"✅ Function {function_name} executada: {result}")
            return result

        except Exception as e:
            logger.error(f"❌ Erro ao executar {function_name}: {e}")
            return {"error": str(e)}
