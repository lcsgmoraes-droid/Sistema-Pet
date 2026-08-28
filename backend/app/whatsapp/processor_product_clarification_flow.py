"""Clarificacao deterministica de produtos no atendimento por WhatsApp."""

import logging
import re
from typing import Any, Dict, Optional

from app.whatsapp.catalog_query_helpers import (
    _extract_explicit_measurements,
    _normalize_text,
    _remove_explicit_measurements,
)
from app.whatsapp.conversation_helpers import (
    GOLD_BRAND_OPTIONS,
    GOLD_CLARIFICATION_MESSAGE,
    _gold_brand_from_reply,
    _gold_brand_matches_product_caption,
    _gold_catalog_query,
    _is_generic_gold_query,
    _recent_purchase_confirmation_message,
)
from app.whatsapp.models import WhatsAppSession
from app.whatsapp.processor_response_flow import _extract_product_media
from app.whatsapp.tenant_context import whatsapp_tenant_context


logger = logging.getLogger(__name__)


class WhatsAppProductClarificationFlowMixin:
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
