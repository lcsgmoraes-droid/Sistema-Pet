"""Montagem e confirmacao de rascunhos de pedido recebidos pelo WhatsApp."""

import logging
import re
from typing import Any, Dict, Optional

from app.whatsapp.catalog_query_helpers import (
    _format_measurement_number,
    _normalize_text,
    _strip_audio_marker,
)
from app.whatsapp.conversation_helpers import (
    MAX_PRODUCT_IMAGES_PER_RESPONSE,
    _confirmation_reply,
    _filter_unavailable_catalog_products,
)
from app.whatsapp.customer_context_service import load_latest_purchase
from app.whatsapp.models import WhatsAppSession
from app.whatsapp.order_drafts import (
    HISTORY_ITEM_SELECTION_CONTEXT_KEY,
    ORDER_DRAFT_CONTEXT_KEY,
    build_order_draft_message,
    draft_product_media,
    extract_history_quantity_request,
    extract_multi_item_order,
    extract_single_item_order,
    format_draft_item,
    is_generic_reorder_request,
    purchase_items_as_draft,
)


logger = logging.getLogger(__name__)


class WhatsAppOrderDraftFlowMixin:
    async def _send_order_draft(
        self,
        *,
        session: WhatsAppSession,
        session_context: Dict[str, Any],
        items: list[Dict[str, Any]],
        source: str,
        from_history: bool,
        customer_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_context[ORDER_DRAFT_CONTEXT_KEY] = {
            "source": source,
            "items": items,
        }
        session_context.pop(HISTORY_ITEM_SELECTION_CONTEXT_KEY, None)
        self._save_session_context(session, session_context)
        draft_message = build_order_draft_message(
            items,
            from_history=from_history,
        )
        if customer_note:
            draft_message = f"{customer_note}\n\n{draft_message}"
        return await self._send_response(
            session_id=session.id,
            response=draft_message,
            intent="rascunho_pedido",
            model_used="deterministic_order_draft",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
            product_media=draft_product_media(items),
        )

    async def _handle_single_item_order(
        self,
        *,
        session: WhatsAppSession,
        session_context: Dict[str, Any],
        requested_item: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Pesquisa um pedido unitário antes de decidir por atendimento humano."""
        catalog_query = str(requested_item.get("catalog_query") or "").strip()
        result = await self._execute_function(
            function_name="buscar_produto",
            arguments={"termo": catalog_query, "limit": 5},
            context={},
            session_id=session.id,
        )
        result = _filter_unavailable_catalog_products(result)
        self._remember_catalog_search(session.id, catalog_query, result)

        data = result.get("data") if isinstance(result, dict) else None
        if not isinstance(data, dict):
            data = result if isinstance(result, dict) else {}
        products = data.get("produtos")
        if not isinstance(products, list):
            products = []

        if not products:
            unavailable = bool(data.get("unavailable_found"))
            explanation = (
                f"Encontrei {catalog_query}, mas está sem estoque no momento."
                if unavailable
                else f"Não consegui identificar {catalog_query} no catálogo."
            )
            return await self._transfer_to_human(
                session_id=session.id,
                reason=(
                    "product_out_of_stock" if unavailable else "product_not_identified"
                ),
                reason_details=(
                    f"Pedido explícito não resolvido automaticamente: {catalog_query}"
                ),
                customer_message=(
                    f"{explanation} Vou encaminhar você para um atendente humano "
                    "continuar o atendimento. ⏳"
                ),
            )

        options = [
            {
                "product_id": product.get("id"),
                "name": str(product.get("nome") or "Produto"),
                "quantity": float(requested_item.get("quantity") or 1),
                "unit": str(requested_item.get("unit") or "x"),
                "unit_price": product.get("preco"),
                "stock": float(product.get("estoque") or 0),
                "image_url": str(product.get("imagem_url") or ""),
            }
            for product in products[:MAX_PRODUCT_IMAGES_PER_RESPONSE]
            if isinstance(product, dict) and product.get("id") not in (None, "")
        ]
        if len(options) == 1:
            requested_quantity = float(requested_item.get("quantity") or 1)
            available_quantity = float(options[0].get("stock") or 0)
            customer_note = None
            if 0 < available_quantity < requested_quantity:
                options[0]["quantity"] = available_quantity
                requested_text = _format_measurement_number(requested_quantity)
                available_text = _format_measurement_number(available_quantity)
                customer_note = (
                    f"Você pediu {requested_text} unidade(s), mas encontrei "
                    f"{available_text} em estoque. Posso montar o pedido com "
                    f"as {available_text} disponíveis?"
                )
            return await self._send_order_draft(
                session=session,
                session_context=session_context,
                items=options,
                source="single_item_catalog",
                from_history=False,
                customer_note=customer_note,
            )

        session_context[HISTORY_ITEM_SELECTION_CONTEXT_KEY] = {
            "source": "single_item_catalog",
            "quantity": requested_item.get("quantity", 1),
            "unit": requested_item.get("unit") or "x",
            "options": options,
        }
        session_context.pop(ORDER_DRAFT_CONTEXT_KEY, None)
        self._save_session_context(session, session_context)
        options_text = "\n\n".join(
            f"{index}. {option['name']}"
            for index, option in enumerate(options, start=1)
        )
        return await self._send_response(
            session_id=session.id,
            response=(
                "Encontrei mais de uma opção para esse pedido:\n\n"
                f"{options_text}\n\nResponda com o número do produto."
            ),
            intent="clarificacao_item_catalogo",
            model_used="deterministic_catalog_order_selection",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
            product_media=draft_product_media(options),
        )

    async def _handle_order_draft_flow(
        self, session_id: str, message_content: str
    ) -> Optional[Dict[str, Any]]:
        """Monta e confirma pedidos sem gravar uma venda automaticamente."""
        message_content = _strip_audio_marker(message_content)
        session = self.db.query(WhatsAppSession).get(session_id)
        if not session:
            return None

        session_context = self._load_session_context(session)
        checkout_result = await self._handle_order_checkout_flow(
            session=session,
            session_context=session_context,
            message_content=message_content,
        )
        if checkout_result:
            return checkout_result

        pending_selection = session_context.get(HISTORY_ITEM_SELECTION_CONTEXT_KEY)
        if isinstance(pending_selection, dict):
            normalized_reply = re.sub(r"[^0-9]", "", message_content or "")
            options = pending_selection.get("options") or []
            if normalized_reply and len(normalized_reply) <= 2:
                selected_index = int(normalized_reply) - 1
                if 0 <= selected_index < len(options):
                    selected = dict(options[selected_index])
                    selected["quantity"] = pending_selection.get("quantity", 1)
                    selected["unit"] = pending_selection.get("unit") or "x"
                    selection_source = str(
                        pending_selection.get("source") or "history_quantity"
                    )
                    return await self._send_order_draft(
                        session=session,
                        session_context=session_context,
                        items=[selected],
                        source=selection_source,
                        from_history=selection_source != "single_item_catalog",
                    )
            if _confirmation_reply(message_content) is not None:
                return await self._send_response(
                    session_id=session_id,
                    response="Escolha o número do produto da lista para eu montar o pedido.",
                    intent="clarificacao_item_historico",
                    model_used="deterministic_history_selection",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                    product_media=draft_product_media(options),
                )

        pending_draft = session_context.get(ORDER_DRAFT_CONTEXT_KEY)
        if isinstance(pending_draft, dict):
            confirmation = await self._interpret_confirmation_reply(
                message_content,
                pending_question=(
                    "O pedido está correto: "
                    + "; ".join(
                        format_draft_item(item)
                        for item in pending_draft.get("items") or []
                    )
                    + "?"
                ),
            )
            numeric_confirmation = re.fullmatch(
                r"\s*([12])[.)]?\s*", message_content or ""
            )
            if confirmation is None and numeric_confirmation:
                confirmation = numeric_confirmation.group(1) == "1"
            if confirmation is True:
                items = pending_draft.get("items") or []
                source = str(pending_draft.get("source") or "whatsapp")
                return await self._start_order_checkout(
                    session=session,
                    session_context=session_context,
                    items=items,
                    source=source,
                )
            if confirmation is False:
                session_context.pop(ORDER_DRAFT_CONTEXT_KEY, None)
                self._save_session_context(session, session_context)
                return await self._send_response(
                    session_id=session_id,
                    response="Certo. Envie a lista completa corrigida, com a quantidade de cada item.",
                    intent="correcao_rascunho_pedido",
                    model_used="deterministic_order_correction",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )
            if any(
                term in _normalize_text(message_content)
                for term in ("alterar", "corrigir", "troca o item", "muda o item")
            ):
                return await self._send_response(
                    session_id=session_id,
                    response="Envie a lista completa corrigida, com a quantidade de cada item.",
                    intent="correcao_rascunho_pedido",
                    model_used="deterministic_order_correction",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

        multi_items = extract_multi_item_order(message_content)
        if multi_items:
            return await self._send_order_draft(
                session=session,
                session_context=session_context,
                items=multi_items,
                source="multi_item_message",
                from_history=False,
            )

        single_item = extract_single_item_order(message_content)
        if single_item:
            return await self._handle_single_item_order(
                session=session,
                session_context=session_context,
                requested_item=single_item,
            )

        if isinstance(pending_draft, dict):
            items = pending_draft.get("items") or []
            source = str(pending_draft.get("source") or "")
            return await self._send_response(
                session_id=session_id,
                response=build_order_draft_message(
                    items,
                    from_history=source in {"purchase_history", "history_quantity"},
                    retry=True,
                ),
                intent="confirmacao_pedido_invalida",
                model_used="deterministic_order_confirmation_retry",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
                product_media=draft_product_media(items),
            )

        quantity_request = extract_history_quantity_request(message_content)
        if not quantity_request and not is_generic_reorder_request(message_content):
            return None

        customer = self._resolve_customer_for_session(session)
        if not customer:
            return await self._send_response(
                session_id=session_id,
                response=(
                    "Não encontrei compras vinculadas a este número no CorePet. "
                    "Se quiser, me diga qual produto você procura e eu consulto o catálogo."
                ),
                intent="recompra_cliente_nao_identificado",
                model_used="deterministic_reorder_not_identified",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        try:
            purchase = load_latest_purchase(
                self.db,
                tenant_id=self.tenant_id,
                customer_id=customer.id,
            )
        except Exception as history_error:
            logger.warning("Falha ao consultar última compra: %s", history_error)
            self.db.rollback()
            purchase = None
        if not purchase:
            return await self._send_response(
                session_id=session_id,
                response=(
                    "Não encontrei uma compra concluída vinculada a este número. "
                    "Se quiser, me diga qual produto você procura e eu consulto o catálogo."
                ),
                intent="recompra_historico_nao_encontrado",
                model_used="deterministic_reorder_history_not_found",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        items = purchase_items_as_draft(purchase)
        if quantity_request and len(items) > 1:
            session_context[HISTORY_ITEM_SELECTION_CONTEXT_KEY] = {
                "quantity": quantity_request["quantity"],
                "unit": quantity_request["unit"],
                "options": items,
            }
            self._save_session_context(session, session_context)
            options_text = "\n\n".join(
                f"{index}. {format_draft_item(item)}"
                for index, item in enumerate(items, start=1)
            )
            return await self._send_response(
                session_id=session_id,
                response=(
                    "Encontrei estes itens na sua compra mais recente. "
                    "De qual deles você quer "
                    f"{int(quantity_request['quantity']) if quantity_request['quantity'].is_integer() else quantity_request['quantity']} "
                    f"{quantity_request['unit']}?\n\n{options_text}\n\nResponda com o número."
                ),
                intent="clarificacao_item_historico",
                model_used="deterministic_history_selection",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
                product_media=draft_product_media(items),
            )

        if quantity_request and items:
            items[0]["quantity"] = quantity_request["quantity"]
            items[0]["unit"] = quantity_request["unit"]

        return await self._send_order_draft(
            session=session,
            session_context=session_context,
            items=items,
            source="purchase_history",
            from_history=True,
        )
