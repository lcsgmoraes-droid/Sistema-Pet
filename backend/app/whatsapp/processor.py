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
from app.ai.llm_client import (
    LLMClient,
    PromptBuilder,
    AVAILABLE_FUNCTIONS_PHASE1_READ_ONLY,
)
from app.whatsapp.sender import send_whatsapp_message
from app.whatsapp.models import (
    WhatsAppSession,
    WhatsAppMessage,
    WhatsAppMetric,
    TenantWhatsAppConfig,
)
from app.whatsapp.handoff_manager import HandoffManager
from app.whatsapp.tenant_context import whatsapp_tenant_context
from app.whatsapp.customer_context_service import (
    load_customer_benefits,
    load_latest_delivery,
    load_store_hours,
    resolve_session_customer,
)
from app.whatsapp.order_drafts import (
    is_safe_product_image_url,
)
from app.whatsapp.catalog_query_helpers import (
    _canonicalize_numeric_measurements as _canonicalize_numeric_measurements,
    _catalog_followup_query,
    _extract_explicit_measurements,
    _normalize_text,
    _product_query_from_choice_phrase,
    _remove_explicit_measurements,
    _special_catalog_request_query,
    _strip_audio_marker,
)
from app.whatsapp.conversation_helpers import (
    CATALOG_SEARCH_CONTEXT_KEY,
    GOLD_BRAND_OPTIONS,
    GOLD_CLARIFICATION_MESSAGE,
    MAX_PRODUCT_IMAGES_PER_RESPONSE,
    _build_catalog_response,
    _build_validity_response,
    _build_weight_options_response,
    _confirmation_reply,
    _customer_benefits_response,
    _delivery_status_response,
    _filter_unavailable_catalog_products,
    _gold_brand_from_reply,
    _gold_brand_matches_product_caption,
    _gold_catalog_query,
    _image_catalog_query,
    _image_identification_response,
    _is_contextless_product_photo_request,
    _is_generic_gold_query,
    _operational_handoff_reason,
    _preserve_explicit_measurements,
    _recent_purchase_confirmation_message,
    _replace_generic_gold as _replace_generic_gold,
    _restricted_scope_response,
    _tool_choice_for_intent,
)
from app.whatsapp.processor_checkout_flow import WhatsAppCheckoutFlowMixin
from app.whatsapp.processor_checkout_support import WhatsAppCheckoutSupportMixin
from app.whatsapp.processor_order_draft_flow import WhatsAppOrderDraftFlowMixin
from app.whatsapp.remote_corepet_client import (
    create_remote_order,
    fetch_remote_customer_context,
    fetch_remote_order_preview,
)

logger = logging.getLogger(__name__)

MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+)\)")


def _extract_product_media(function_result: Any) -> list[Dict[str, str]]:
    """Extrai fotos dos produtos retornados pelas functions de catálogo."""
    if not isinstance(function_result, dict):
        return []

    data = function_result.get("data")
    if not isinstance(data, dict):
        data = function_result

    products = data.get("produtos")
    if not isinstance(products, list):
        return []

    media: list[Dict[str, str]] = []
    for product in products:
        if not isinstance(product, dict):
            continue
        image_url = str(product.get("imagem_url") or "").strip()
        if not is_safe_product_image_url(image_url):
            continue

        name = str(product.get("nome") or "Produto").strip()
        price = product.get("preco")
        caption = name
        if isinstance(price, (int, float)):
            caption += f" — R$ {float(price):.2f}".replace(".", ",")
        media.append({"image_url": image_url, "caption": caption})

    return media


def _clean_response_image_links(
    response: str, product_media: list[Dict[str, str]]
) -> str:
    """Remove links de imagem do texto quando a foto será anexada de verdade."""
    cleaned = MARKDOWN_IMAGE_PATTERN.sub("", response or "")
    for item in product_media:
        image_url = item.get("image_url") or ""
        if image_url:
            cleaned = cleaned.replace(image_url, "")

    cleaned = re.sub(r"(?m)^\s*-\s*$", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


class MessageProcessor(
    WhatsAppCheckoutSupportMixin,
    WhatsAppCheckoutFlowMixin,
    WhatsAppOrderDraftFlowMixin,
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
    def _is_explicit_human_request(message: str) -> bool:
        """Detecta pedido explícito de atendimento humano."""
        text = (message or "").lower()
        triggers = [
            "atendente",
            "atendimento humano",
            "humano",
            "falar com pessoa",
            "falar com humano",
            "falar com atendente",
            "quero suporte humano",
            "transferir para humano",
        ]
        return any(trigger in text for trigger in triggers)

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

    async def _handle_real_operational_request(
        self,
        *,
        session_id: str,
        message_content: str,
        reason: str,
    ) -> Optional[Dict[str, Any]]:
        """Responde usando o CorePet; retorna None quando falta dado confiável."""
        try:
            if reason == "store_hours":
                hours = load_store_hours(self.db, tenant_id=self.tenant_id)
                if not hours:
                    return None
                return await self._send_response(
                    session_id=session_id,
                    response=(
                        "O horário cadastrado no CorePet é das "
                        f"{hours['start']} às {hours['end']}."
                    ),
                    intent="consulta_horario_loja",
                    model_used="corepet_store_hours",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            if reason not in {"delivery_status", "loyalty_or_credit"}:
                return None

            session = self.db.query(WhatsAppSession).get(session_id)
            if not session:
                return None
            customer = self._resolve_customer_for_session(session)
            if not customer:
                return None

            if reason == "delivery_status":
                delivery = load_latest_delivery(
                    self.db,
                    tenant_id=self.tenant_id,
                    customer_id=customer.id,
                )
                response = _delivery_status_response(delivery) if delivery else None
                if not response:
                    return None
                return await self._send_response(
                    session_id=session_id,
                    response=response,
                    intent="consulta_status_entrega",
                    model_used="corepet_delivery_status",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            benefits = load_customer_benefits(
                self.db,
                tenant_id=self.tenant_id,
                customer=customer,
            )
            response = _customer_benefits_response(benefits, message_content)
            if not response:
                return None
            return await self._send_response(
                session_id=session_id,
                response=response,
                intent="consulta_beneficios_cliente",
                model_used="corepet_customer_benefits",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )
        except Exception as operational_error:
            logger.warning(
                "Falha na consulta operacional %s: %s",
                reason,
                operational_error,
            )
            self.db.rollback()
            return None

    async def _get_gold_clarification_media(
        self, session_id: str, original_query: str
    ) -> list[Dict[str, str]]:
        """Busca no catálogo uma foto representativa para cada opção de marca."""
        media: list[Dict[str, str]] = []
        for choice, brand in GOLD_BRAND_OPTIONS.items():
            result = await self._execute_function(
                function_name="buscar_produto",
                arguments={
                    "termo": _gold_catalog_query(original_query, brand),
                    "limit": 1,
                },
                context={},
                session_id=session_id,
            )
            candidates = _extract_product_media(result)
            matching_candidate = next(
                (
                    candidate
                    for candidate in candidates
                    if _gold_brand_matches_product_caption(
                        brand, candidate.get("caption", "")
                    )
                ),
                None,
            )
            if not matching_candidate:
                continue
            media.append(
                {
                    "image_url": matching_candidate["image_url"],
                    "caption": f"{choice}. {brand}",
                }
            )
        return media

    def _find_recent_gold_purchase(
        self, session: WhatsAppSession, original_query: str
    ) -> Optional[str]:
        """Retorna a compra Gold mais recente do cliente, respeitando peso e tenant."""
        if not session.cliente_id:
            return None

        from sqlalchemy import func

        from app.produtos_models import Produto
        from app.vendas_models import Venda, VendaItem

        try:
            with whatsapp_tenant_context(self.tenant_id):
                query = (
                    self.db.query(Produto.nome)
                    .join(VendaItem, VendaItem.produto_id == Produto.id)
                    .join(Venda, Venda.id == VendaItem.venda_id)
                    .filter(
                        Produto.tenant_id == self.tenant_id,
                        VendaItem.tenant_id == self.tenant_id,
                        Venda.tenant_id == self.tenant_id,
                        Venda.cliente_id == session.cliente_id,
                        Venda.status != "cancelada",
                        VendaItem.tipo == "produto",
                        Produto.situacao.is_(True),
                        Produto.nome.ilike("%gold%"),
                    )
                )

                weight_match = re.search(
                    r"\b\d+(?:[.,]\d+)?\s*kg\b",
                    _normalize_text(original_query),
                )
                if weight_match:
                    normalized_weight = weight_match.group(0).replace(" ", "")
                    query = query.filter(
                        func.replace(func.lower(Produto.nome), " ", "").like(
                            f"%{normalized_weight}%"
                        )
                    )

                recent = query.order_by(
                    Venda.data_venda.desc(), VendaItem.id.desc()
                ).first()
                return str(recent.nome).strip() if recent and recent.nome else None
        except Exception as history_error:
            logger.warning(
                "Falha ao consultar histórico de produto da sessão %s: %s",
                session.id,
                history_error,
            )
            self.db.rollback()
            return None

    async def _get_recent_purchase_media(
        self, session_id: str, product_name: str
    ) -> list[Dict[str, str]]:
        result = await self._execute_function(
            function_name="buscar_produto",
            arguments={"termo": product_name, "limit": 5},
            context={},
            session_id=session_id,
        )
        media = _extract_product_media(result)
        if not media:
            return []

        normalized_name = _normalize_text(product_name)
        exact = next(
            (
                item
                for item in media
                if _normalize_text(item.get("caption", "").split(" — ", 1)[0])
                == normalized_name
            ),
            media[0],
        )
        return [{"image_url": exact["image_url"], "caption": product_name}]

    async def _send_gold_brand_clarification(
        self,
        session_id: str,
        original_query: str,
    ) -> Dict[str, Any]:
        return await self._send_response(
            session_id=session_id,
            response=GOLD_CLARIFICATION_MESSAGE,
            intent="clarificacao_produto",
            model_used="deterministic_clarification",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
            product_media=await self._get_gold_clarification_media(
                session_id, original_query
            ),
        )

    async def _handle_product_clarification(
        self, session_id: str, message_content: str
    ) -> tuple[Optional[Dict[str, Any]], str, bool]:
        """Conduz ambiguidades de produto em etapas, antes de consultar a IA."""
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            return None, message_content, False

        session_context = self._load_session_context(session)
        pending = session_context.get("pending_product_clarification")
        if (
            isinstance(pending, dict)
            and pending.get("type") == "recent_gold_confirmation"
        ):
            original_query = str(pending.get("original_query") or "ração Gold")
            product_name = str(pending.get("product_name") or "").strip()
            brand = _gold_brand_from_reply(message_content)
            if brand:
                session_context.pop("pending_product_clarification", None)
                self._save_session_context(session, session_context)
                current_measurements = _extract_explicit_measurements(message_content)
                detailed_query = " ".join(
                    [
                        (
                            _remove_explicit_measurements(original_query)
                            if current_measurements
                            else original_query
                        ),
                        *current_measurements,
                    ]
                )
                return None, _gold_catalog_query(detailed_query, brand), True

            confirmation = await self._interpret_confirmation_reply(
                message_content,
                pending_question=f"É este produto: {product_name}?",
            )
            if confirmation is True and product_name:
                session_context.pop("pending_product_clarification", None)
                self._save_session_context(session, session_context)
                return None, product_name, True

            if confirmation is False:
                session_context["pending_product_clarification"] = {
                    "type": "gold_brand",
                    "original_query": original_query,
                }
                self._save_session_context(session, session_context)
                return (
                    await self._send_gold_brand_clarification(
                        session_id, original_query
                    ),
                    message_content,
                    False,
                )

            return (
                await self._send_response(
                    session_id=session_id,
                    response=_recent_purchase_confirmation_message(product_name),
                    intent="clarificacao_produto_historico",
                    model_used="deterministic_purchase_history",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                    product_media=await self._get_recent_purchase_media(
                        session_id, product_name
                    ),
                ),
                message_content,
                False,
            )

        if isinstance(pending, dict) and pending.get("type") == "gold_brand":
            brand = _gold_brand_from_reply(message_content)
            if brand:
                original_query = str(pending.get("original_query") or "ração Gold")
                session_context.pop("pending_product_clarification", None)
                self._save_session_context(session, session_context)
                current_measurements = _extract_explicit_measurements(message_content)
                detailed_query = " ".join(
                    [
                        (
                            _remove_explicit_measurements(original_query)
                            if current_measurements
                            else original_query
                        ),
                        *current_measurements,
                    ]
                )
                return None, _gold_catalog_query(detailed_query, brand), True

            original_query = str(pending.get("original_query") or "ração Gold")
            return (
                await self._send_gold_brand_clarification(session_id, original_query),
                message_content,
                False,
            )

        if not _is_generic_gold_query(message_content):
            return None, message_content, False

        recent_product = self._find_recent_gold_purchase(session, message_content)
        if recent_product:
            session_context["pending_product_clarification"] = {
                "type": "recent_gold_confirmation",
                "original_query": message_content,
                "product_name": recent_product,
            }
            self._save_session_context(session, session_context)
            return (
                await self._send_response(
                    session_id=session_id,
                    response=_recent_purchase_confirmation_message(recent_product),
                    intent="clarificacao_produto_historico",
                    model_used="deterministic_purchase_history",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                    product_media=await self._get_recent_purchase_media(
                        session_id, recent_product
                    ),
                ),
                message_content,
                False,
            )

        session_context["pending_product_clarification"] = {
            "type": "gold_brand",
            "original_query": message_content,
        }
        self._save_session_context(session, session_context)
        return (
            await self._send_gold_brand_clarification(session_id, message_content),
            message_content,
            False,
        )

    async def _maybe_transfer_to_human(
        self,
        session_id: str,
        message_content: str,
        intent: str,
        confidence: float,
    ) -> Optional[Dict[str, Any]]:
        if self._is_explicit_human_request(message_content):
            return await self._transfer_to_human(
                session_id=session_id,
                reason="manual_request",
                reason_details="Pedido explícito do cliente por atendente humano",
            )

        if self.router.should_transfer_to_human(intent, confidence):
            return await self._transfer_to_human(session_id, intent)

        return None

    async def _send_basic_mode_response(
        self, session_id: str, intent: str
    ) -> Dict[str, Any]:
        return await self._send_response(
            session_id=session_id,
            response=(
                "Recebi sua mensagem e já vou te ajudar. "
                "No momento estou em modo básico e em seguida um atendente assume se necessário."
            ),
            intent=intent,
            model_used="fallback_no_openai",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
        )

    async def _handle_processing_error(
        self, session_id: str, error: Exception
    ) -> Dict[str, Any]:
        logger.error(f"❌ Erro ao processar mensagem: {error}")
        self.db.rollback()
        fallback_message = await send_whatsapp_message(
            db=self.db,
            tenant_id=self.tenant_id,
            session_id=session_id,
            message="Recebi sua mensagem e já estou te atendendo. Pode me enviar novamente em texto curto?",
        )
        if fallback_message:
            return {"action": "fallback_responded", "error": str(error)}
        return {"action": "error", "error": str(error)}

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

    # ========================================================================
    # PROCESSAMENTO COM IA
    # ========================================================================

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
        processing_time_ms: int,
        product_media: Optional[list[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Envia resposta via WhatsApp e registra no banco.
        """
        unique_media: list[Dict[str, str]] = []
        seen_urls: set[str] = set()
        for item in product_media or []:
            image_url = str(item.get("image_url") or "").strip()
            if not image_url or image_url in seen_urls:
                continue
            seen_urls.add(image_url)
            unique_media.append(item)

        unique_media = unique_media[:MAX_PRODUCT_IMAGES_PER_RESPONSE]
        clean_response = _clean_response_image_links(response, unique_media)

        # Enviar texto via WhatsApp
        message = await send_whatsapp_message(
            db=self.db,
            tenant_id=self.tenant_id,
            session_id=session_id,
            message=clean_response,
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

        images_sent = 0
        for item in unique_media:
            image_message = await send_whatsapp_message(
                db=self.db,
                tenant_id=self.tenant_id,
                session_id=session_id,
                message=item.get("caption") or "Foto do produto",
                message_type="image",
                image_url=item["image_url"],
            )
            if image_message:
                images_sent += 1
            else:
                logger.warning("Falha ao enviar imagem de produto")

        # Registrar métricas
        await self._log_metric("message_sent", 1)
        await self._log_metric("tokens_used", tokens_input + tokens_output)

        logger.info(
            "✅ Resposta enviada: %s chars, %s imagens",
            len(clean_response),
            images_sent,
        )

        return {
            "action": "responded",
            "message_id": message.id,
            "intent": intent,
            "model": model_used,
            "tokens": tokens_input + tokens_output,
            "images_sent": images_sent,
        }

    async def _transfer_to_human(
        self,
        session_id: str,
        reason: str,
        reason_details: Optional[str] = None,
        customer_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transfere conversa para atendente humano.
        """
        session = self.db.query(WhatsAppSession).get(session_id)
        handoff = None

        if session:
            session.status = "waiting_human"

            handoff_manager = HandoffManager(self.db, self.tenant_id)
            existing_handoff = handoff_manager.get_active_handoff(session_id)

            if existing_handoff:
                handoff = existing_handoff
            else:
                handoff = handoff_manager.create_handoff(
                    session_id=session_id,
                    phone_number=session.phone_number,
                    reason=reason,
                    priority=(
                        "high"
                        if reason in {"reclamacao", "manual_request"}
                        else "medium"
                    ),
                    reason_details=reason_details
                    or f"Transferência automática por intent: {reason}",
                )

            self.db.commit()

        transfer_messages = {
            "medical_guidance": (
                "Para a segurança do seu pet, não vou indicar medicamento sem "
                "avaliação. Vou chamar um atendente para orientar o próximo passo. ⏳"
            ),
            "delivery_status": (
                "Vou chamar um atendente para verificar sua entrega. Um momento, por favor. ⏳"
            ),
        }

        # Enviar mensagem de transferência
        await send_whatsapp_message(
            db=self.db,
            tenant_id=self.tenant_id,
            session_id=session_id,
            message=transfer_messages.get(
                reason,
                customer_message
                or "Um momento! Estou transferindo você para um atendente humano. ⏳",
            ),
        )

        logger.info(f"👤 Transferido para humano: {reason}")

        return {
            "action": "transferred_to_human",
            "reason": reason,
            "handoff_id": str(handoff.id) if handoff else None,
        }

    async def _log_metric(self, metric_type: str, value: float):
        with whatsapp_tenant_context(self.tenant_id):
            return await self._log_metric_with_context(metric_type, value)

    async def _log_metric_with_context(self, metric_type: str, value: float):
        """Registra métrica no banco."""
        try:
            metric = WhatsAppMetric(
                tenant_id=self.tenant_id,
                metric_type=metric_type,
                value=value,
                timestamp=datetime.utcnow(),
            )
            self.db.add(metric)
            self.db.commit()
        except Exception as e:
            logger.warning(f"Erro ao registrar métrica: {e}")
