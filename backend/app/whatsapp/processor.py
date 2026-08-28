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

import json
import logging
import os
import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from types import SimpleNamespace

from app.ai.intent_classifier import IntentClassifier, IntentRouter
from app.ai.context_builder import ContextBuilder
from app.ai.llm_client import LLMClient
from app.whatsapp.sender import send_whatsapp_message
from app.whatsapp.models import (
    WhatsAppSession,
    WhatsAppMessage,
    TenantWhatsAppConfig,
)
from app.whatsapp.handoff_manager import HandoffManager
from app.whatsapp.tenant_context import whatsapp_tenant_context
from app.whatsapp.customer_context_service import (
    resolve_session_customer,
)
from app.whatsapp.catalog_query_helpers import (
    _canonicalize_numeric_measurements as _canonicalize_numeric_measurements,
    _catalog_followup_query,
    _extract_explicit_measurements as _extract_explicit_measurements,
    _normalize_text,
    _product_query_from_choice_phrase,
    _remove_explicit_measurements as _remove_explicit_measurements,
    _special_catalog_request_query,
    _strip_audio_marker,
)
from app.whatsapp.conversation_helpers import (
    CATALOG_SEARCH_CONTEXT_KEY,
    GOLD_BRAND_OPTIONS as GOLD_BRAND_OPTIONS,
    GOLD_CLARIFICATION_MESSAGE as GOLD_CLARIFICATION_MESSAGE,
    MAX_PRODUCT_IMAGES_PER_RESPONSE,
    _build_catalog_response as _build_catalog_response,
    _build_validity_response as _build_validity_response,
    _build_weight_options_response as _build_weight_options_response,
    _confirmation_reply,
    _customer_benefits_response as _customer_benefits_response,
    _delivery_status_response as _delivery_status_response,
    _filter_unavailable_catalog_products as _filter_unavailable_catalog_products,
    _gold_brand_from_reply as _gold_brand_from_reply,
    _gold_brand_matches_product_caption as _gold_brand_matches_product_caption,
    _gold_catalog_query as _gold_catalog_query,
    _image_catalog_query,
    _image_identification_response,
    _is_contextless_product_photo_request,
    _is_generic_gold_query as _is_generic_gold_query,
    _operational_handoff_reason,
    _preserve_explicit_measurements as _preserve_explicit_measurements,
    _recent_purchase_confirmation_message as _recent_purchase_confirmation_message,
    _replace_generic_gold as _replace_generic_gold,
    _restricted_scope_response,
    _tool_choice_for_intent as _tool_choice_for_intent,
)
from app.whatsapp.processor_checkout_flow import WhatsAppCheckoutFlowMixin
from app.whatsapp.processor_checkout_support import WhatsAppCheckoutSupportMixin
from app.whatsapp.processor_ai_flow import WhatsAppAIFlowMixin
from app.whatsapp.processor_order_draft_flow import WhatsAppOrderDraftFlowMixin
from app.whatsapp.processor_operational_flow import WhatsAppOperationalFlowMixin
from app.whatsapp.processor_product_clarification_flow import (
    WhatsAppProductClarificationFlowMixin,
)
from app.whatsapp.processor_response_flow import (
    WhatsAppResponseFlowMixin,
    _clean_response_image_links as _clean_response_image_links,
    _extract_product_media as _extract_product_media,
)
from app.whatsapp.remote_corepet_client import (
    create_remote_order,
    fetch_remote_customer_context,
    fetch_remote_order_preview,
)

logger = logging.getLogger(__name__)


class MessageProcessor(
    WhatsAppCheckoutSupportMixin,
    WhatsAppCheckoutFlowMixin,
    WhatsAppOrderDraftFlowMixin,
    WhatsAppOperationalFlowMixin,
    WhatsAppProductClarificationFlowMixin,
    WhatsAppAIFlowMixin,
    WhatsAppResponseFlowMixin,
):
    """
    Processador principal de mensagens WhatsApp.
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

        # Buscar config
        with whatsapp_tenant_context(tenant_id):
            config = (
                db.query(TenantWhatsAppConfig)
                .filter(TenantWhatsAppConfig.tenant_id == tenant_id)
                .first()
            )

        fallback_openai_key = os.getenv("OPENAI_API_KEY", "")
        if not config:
            logger.warning(
                "Tenant %s sem tenant_whatsapp_config; aplicando fallback para piloto",
                tenant_id,
            )
            self.config = SimpleNamespace(
                openai_api_key=fallback_openai_key,
                model_preference=(os.getenv("WHATSAPP_OPENAI_MODEL") or "gpt-4o-mini"),
                auto_response_enabled=True,
                bot_name="Assistente",
            )
        else:
            self.config = config
            if not self.config.openai_api_key and fallback_openai_key:
                self.config = SimpleNamespace(
                    openai_api_key=fallback_openai_key,
                    model_preference=(
                        os.getenv("WHATSAPP_OPENAI_MODEL")
                        or getattr(config, "model_preference", None)
                        or "gpt-4o-mini"
                    ),
                    auto_response_enabled=getattr(
                        config, "auto_response_enabled", True
                    ),
                    bot_name=getattr(config, "bot_name", "Assistente"),
                )

        self.ai_enabled = bool(self.config.openai_api_key)
        preferred_model = (
            os.getenv("WHATSAPP_OPENAI_MODEL")
            or getattr(self.config, "model_preference", None)
            or "gpt-4o-mini"
        )

        # Inicializar componentes
        self.intent_classifier = (
            IntentClassifier(self.config.openai_api_key, model=preferred_model)
            if self.ai_enabled
            else None
        )
        self.context_builder = ContextBuilder(db)
        self.llm_client = (
            LLMClient(
                self.config.openai_api_key,
                default_model=preferred_model,
                advanced_model=preferred_model,
            )
            if self.ai_enabled
            else None
        )
        self.router = IntentRouter()

    @staticmethod
    def _fetch_remote_customer_context(
        *args: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        return fetch_remote_customer_context(*args, **kwargs)

    @staticmethod
    def _fetch_remote_order_preview(
        *args: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        return fetch_remote_order_preview(*args, **kwargs)

    @staticmethod
    def _create_remote_order(*args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return create_remote_order(*args, **kwargs)

    @staticmethod
    async def _send_whatsapp_message(*args: Any, **kwargs: Any):
        """Mantém o ponto histórico de substituição do sender nos testes."""
        return await send_whatsapp_message(*args, **kwargs)

    @staticmethod
    def _create_handoff_manager(db: Session, tenant_id: str) -> HandoffManager:
        """Centraliza a criação do gerenciador de handoff na fachada pública."""
        return HandoffManager(db, tenant_id)

    async def _build_context(
        self, session_id: str, message_content: str
    ) -> Dict[str, Any]:
        try:
            return await self.context_builder.build_context(
                tenant_id=self.tenant_id,
                session_id=session_id,
                message=message_content,
            )
        except Exception as context_error:
            logger.warning(
                f"Falha ao construir contexto, seguindo com contexto mínimo: {context_error}"
            )
            self.db.rollback()
            return {}

    async def _detect_intent(
        self, message_content: str, context: Dict[str, Any]
    ) -> tuple[str, float]:
        if not self.ai_enabled:
            result = IntentClassifier._fallback_classification(message_content)
            return result["intent"], result["confidence"]

        intent_result = await self.intent_classifier.classify(
            message=message_content,
            context=context,
        )
        return intent_result["intent"], intent_result["confidence"]

    async def _interpret_confirmation_reply(
        self,
        message: str,
        *,
        pending_question: str,
    ) -> Optional[bool]:
        """Usa IA apenas quando a confirmação não puder ser decidida com segurança."""
        deterministic = _confirmation_reply(message)
        if deterministic is not None:
            return deterministic

        llm_client = getattr(self, "llm_client", None)
        if not getattr(self, "ai_enabled", False) or llm_client is None:
            return None

        try:
            result = await llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classifique a resposta do cliente à pergunta pendente. "
                            "Responda somente SIM, NAO ou OUTRO. SIM significa que o "
                            "cliente confirmou; NAO significa que recusou ou quer alterar; "
                            "OUTRO significa dúvida, pergunta nova ou resposta insuficiente."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Pergunta pendente: {pending_question}\n"
                            f"Resposta do cliente: {message}"
                        ),
                    },
                ],
                temperature=0,
                max_tokens=8,
            )
        except Exception as error:
            logger.warning("Falha ao interpretar confirmação com IA: %s", error)
            return None

        label = re.sub(r"[^a-z]", "", _normalize_text(str(result.get("content") or "")))
        if label == "sim":
            return True
        if label == "nao":
            return False
        return None

    def _save_message_intent(self, message_id: str, intent: str) -> None:
        msg = self.db.query(WhatsAppMessage).get(message_id)
        if not msg:
            return

        try:
            msg.intent_detected = intent
            self.db.commit()
        except Exception as intent_save_error:
            logger.warning(f"Falha ao salvar intent na mensagem: {intent_save_error}")
            self.db.rollback()

    def _save_session_intent(self, session_id: str, intent: str) -> None:
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            return

        try:
            session.last_intent = intent
            self.db.commit()
        except Exception as session_save_error:
            logger.warning(f"Falha ao salvar intent na sessão: {session_save_error}")
            self.db.rollback()

    def _save_detected_intent(
        self, message_id: str, session_id: str, intent: str
    ) -> None:
        self._save_message_intent(message_id, intent)
        self._save_session_intent(session_id, intent)

    def _load_session_context(self, session: WhatsAppSession) -> Dict[str, Any]:
        try:
            parsed = json.loads(session.context or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}

    def _save_session_context(
        self, session: WhatsAppSession, context: Dict[str, Any]
    ) -> None:
        session.context = json.dumps(context, ensure_ascii=False)
        self.db.commit()

    def _remember_catalog_search(
        self,
        session_id: str,
        catalog_query: str,
        function_result: Any,
    ) -> None:
        """Guarda o produto pesquisado para entender refinamentos na próxima fala."""
        if not getattr(self, "db", None):
            return
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            return

        data = (
            function_result.get("data") if isinstance(function_result, dict) else None
        )
        if not isinstance(data, dict):
            data = function_result if isinstance(function_result, dict) else {}
        products = data.get("produtos")
        if not isinstance(products, list):
            products = []

        session_context = self._load_session_context(session)
        session_context[CATALOG_SEARCH_CONTEXT_KEY] = {
            "query": catalog_query,
            "options": [
                {
                    "id": product.get("id"),
                    "nome": product.get("nome"),
                    "estoque": product.get("estoque"),
                    "preco": product.get("preco"),
                    "imagem_url": product.get("imagem_url") or "",
                }
                for product in products[:MAX_PRODUCT_IMAGES_PER_RESPONSE]
                if isinstance(product, dict)
            ],
        }
        self._save_session_context(session, session_context)

    def _resolve_catalog_followup(
        self, session_id: str, message_content: str
    ) -> Optional[str]:
        """Aplica peso/variação curta ao último produto consultado na sessão."""
        if not getattr(self, "db", None):
            return None
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            return None
        session_context = self._load_session_context(session)
        pending = session_context.get(CATALOG_SEARCH_CONTEXT_KEY)
        if not isinstance(pending, dict):
            return None
        return _catalog_followup_query(
            message_content,
            str(pending.get("query") or ""),
        )

    def _last_catalog_query(self, session_id: str) -> str:
        """Recupera o produto em foco para perguntas como 'qual a validade?'"""
        if not getattr(self, "db", None):
            return ""
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            return ""
        pending = self._load_session_context(session).get(CATALOG_SEARCH_CONTEXT_KEY)
        if not isinstance(pending, dict):
            return ""
        return str(pending.get("query") or "").strip()

    def _resolve_customer_for_session(self, session: WhatsAppSession):
        try:
            customer = resolve_session_customer(
                self.db,
                tenant_id=self.tenant_id,
                session=session,
            )
            if (
                customer
                and not session.cliente_id
                and not getattr(customer, "_remote_source", False)
            ):
                session.cliente_id = customer.id
                self.db.commit()
            return customer
        except Exception as customer_error:
            logger.warning(
                "Falha ao identificar cliente da sessão %s: %s",
                session.id,
                customer_error,
            )
            self.db.rollback()
            return None

    async def process_message(
        self, session_id: str, message_id: str, message_content: str
    ) -> Dict[str, Any]:
        with whatsapp_tenant_context(self.tenant_id):
            return await self._process_message_with_context(
                session_id=session_id,
                message_id=message_id,
                message_content=message_content,
            )

    async def _process_message_with_context(
        self, session_id: str, message_id: str, message_content: str
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

            restricted_response = _restricted_scope_response(message_content)
            if restricted_response:
                self._save_detected_intent(
                    message_id,
                    session_id,
                    "fora_escopo_restrito",
                )
                return await self._send_response(
                    session_id=session_id,
                    response=restricted_response,
                    intent="fora_escopo_restrito",
                    model_used="deterministic_scope_guard",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            order_draft_result = await self._handle_order_draft_flow(
                session_id=session_id,
                message_content=message_content,
            )
            if order_draft_result:
                self._save_detected_intent(
                    message_id,
                    session_id,
                    str(order_draft_result.get("reason") or "rascunho_pedido"),
                )
                return order_draft_result

            operational_handoff = _operational_handoff_reason(message_content)
            if operational_handoff:
                reason, reason_details = operational_handoff
                self._save_detected_intent(message_id, session_id, reason)
                operational_result = await self._handle_real_operational_request(
                    session_id=session_id,
                    message_content=message_content,
                    reason=reason,
                )
                if operational_result:
                    return operational_result
                return await self._transfer_to_human(
                    session_id=session_id,
                    reason=reason,
                    reason_details=reason_details,
                )

            if _is_contextless_product_photo_request(message_content):
                self._save_detected_intent(
                    message_id, session_id, "clarificacao_foto_produto"
                )
                return await self._send_response(
                    session_id=session_id,
                    response=("Claro. De qual produto você gostaria de ver as fotos?"),
                    intent="clarificacao_foto_produto",
                    model_used="deterministic_photo_clarification",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            image_response = _image_identification_response(message_content)
            if image_response:
                return await self._send_response(
                    session_id=session_id,
                    response=image_response,
                    intent="identificacao_imagem",
                    model_used="deterministic_image_identification",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            image_catalog_query = _image_catalog_query(message_content)
            if image_catalog_query:
                message_content = image_catalog_query

            catalog_followup_query = self._resolve_catalog_followup(
                session_id, message_content
            )
            if catalog_followup_query:
                message_content = catalog_followup_query

            product_choice_query = _product_query_from_choice_phrase(
                _strip_audio_marker(message_content)
            )
            if product_choice_query:
                message_content = product_choice_query

            (
                clarification_result,
                message_content,
                product_query_resolved,
            ) = await self._handle_product_clarification(
                session_id=session_id,
                message_content=message_content,
            )
            if clarification_result:
                return clarification_result

            validity_requested, validity_query = _special_catalog_request_query(
                message_content,
                request_type="validity",
            )
            if validity_requested:
                validity_query = validity_query or self._last_catalog_query(session_id)
                self._save_detected_intent(
                    message_id,
                    session_id,
                    "consulta_validade_produto",
                )
                if not validity_query:
                    return await self._send_response(
                        session_id=session_id,
                        response=(
                            "Claro. De qual produto você quer conferir a validade?"
                        ),
                        intent="consulta_validade_produto",
                        model_used="deterministic_validity_clarification",
                        tokens_input=0,
                        tokens_output=0,
                        processing_time_ms=0,
                    )
                return await self._handle_deterministic_validity_lookup(
                    session_id=session_id,
                    catalog_query=validity_query,
                    context={},
                )

            weights_requested, weights_query = _special_catalog_request_query(
                message_content,
                request_type="weights",
            )
            if weights_requested:
                weights_query = weights_query or self._last_catalog_query(session_id)
                self._save_detected_intent(
                    message_id,
                    session_id,
                    "consulta_pesos_produto",
                )
                if not weights_query:
                    return await self._send_response(
                        session_id=session_id,
                        response=(
                            "Claro. De qual produto você quer ver os pesos disponíveis?"
                        ),
                        intent="consulta_pesos_produto",
                        model_used="deterministic_weight_clarification",
                        tokens_input=0,
                        tokens_output=0,
                        processing_time_ms=0,
                    )
                return await self._handle_deterministic_weight_options_lookup(
                    session_id=session_id,
                    catalog_query=weights_query,
                    context={},
                )

            product_query_resolved = bool(
                product_query_resolved
                or image_catalog_query
                or catalog_followup_query
                or product_choice_query
            )

            # 1. Construir contexto
            context = await self._build_context(session_id, message_content)

            # 2. Classificar intenção
            if product_query_resolved:
                intent, confidence = "consulta_produto", 1.0
            else:
                intent, confidence = await self._detect_intent(message_content, context)

            # Atualizar mensagem e sessão com intent detectado
            self._save_detected_intent(message_id, session_id, intent)

            # 3. Verificar se deve transferir para humano
            transfer_result = await self._maybe_transfer_to_human(
                session_id=session_id,
                message_content=message_content,
                intent=intent,
                confidence=confidence,
            )
            if transfer_result:
                return transfer_result

            # 4. Resposta rápida (sem IA) para intents simples
            quick_response = self.router.get_quick_response(
                intent, bot_name=self.config.bot_name or "Assistente"
            )

            if quick_response:
                return await self._send_response(
                    session_id=session_id,
                    response=quick_response,
                    intent=intent,
                    model_used="quick_response",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            # 5. Processar com IA
            if not self.ai_enabled:
                return await self._send_basic_mode_response(session_id, intent)

            return await self._process_with_ai(
                session_id=session_id,
                message_content=message_content,
                context=context,
                intent=intent,
                catalog_query_override=(
                    message_content if product_query_resolved else None
                ),
            )

        except Exception as e:
            return await self._handle_processing_error(session_id, e)

        finally:
            # Registrar métrica
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            await self._log_metric("processing_time", processing_time)
