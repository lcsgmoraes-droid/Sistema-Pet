"""Orquestracao das etapas de checkout conversacional do WhatsApp."""

import re
import uuid
from typing import Any, Dict, Optional

from app.whatsapp.catalog_query_helpers import (
    _normalize_text,
    _product_query_from_choice_phrase,
    _strip_audio_marker,
)
from app.whatsapp.conversation_helpers import CATALOG_SEARCH_CONTEXT_KEY, _format_brl
from app.whatsapp.models import WhatsAppSession
from app.whatsapp.order_checkout import (
    ORDER_CHECKOUT_CONTEXT_KEY,
    ORDER_ITEM_SELECTION_CONTEXT_KEY,
    benefits_lines,
    delivery_address_missing_fields,
    is_final_order_confirmation,
    is_new_conversation_greeting,
    is_order_cancellation,
    is_order_checkout_request,
    is_registered_address_question,
    merge_delivery_address,
    parse_cash_change,
    parse_fulfillment_choice,
    parse_payment_choice,
    parse_quantity_change,
    payment_methods_message,
)
from app.whatsapp.order_drafts import (
    HISTORY_ITEM_SELECTION_CONTEXT_KEY,
    ORDER_DRAFT_CONTEXT_KEY,
    draft_product_media,
)


class WhatsAppCheckoutFlowMixin:
    async def _start_order_checkout(
        self,
        *,
        session: WhatsAppSession,
        session_context: Dict[str, Any],
        items: list[Dict[str, Any]],
        source: str,
    ) -> Dict[str, Any]:
        checkout_items = [self._checkout_item(item) for item in items]
        if not checkout_items or any(item is None for item in checkout_items):
            return await self._send_response(
                session_id=session.id,
                response=(
                    "Antes de fechar, preciso identificar exatamente cada produto no "
                    "catálogo. Envie um produto por vez com o nome e a embalagem."
                ),
                intent="pedido_produto_nao_identificado",
                model_used="deterministic_checkout_missing_product",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        requested_items = [
            {"product_id": item["product_id"], "quantity": item["quantity"]}
            for item in checkout_items
            if item is not None
        ]
        preview = self._fetch_remote_order_preview(
            self.tenant_id,
            phone=session.phone_number,
            items=requested_items,
        )
        if not preview or not preview.get("success"):
            rejection_detail = re.sub(
                r"\s+", " ", str((preview or {}).get("detail") or "")
            ).strip()
            if rejection_detail:
                return await self._transfer_to_human(
                    session_id=session.id,
                    reason="order_preview_rejected",
                    reason_details=rejection_detail,
                    customer_message=(
                        f"Não consigo continuar com este pedido: {rejection_detail} "
                        "O pedido não foi confirmado. Vou encaminhar você para um "
                        "atendente humano ajudar com uma alternativa. ⏳"
                    ),
                )
            return await self._send_response(
                session_id=session.id,
                response=(
                    "Não consegui preparar o resumo agora. Seu pedido ainda não foi "
                    "confirmado. Pode tentar novamente em instantes."
                ),
                intent="pedido_preview_indisponivel",
                model_used="deterministic_checkout_preview_error",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        payment_methods = preview.get("payment_methods") or []
        if not payment_methods:
            return await self._send_response(
                session_id=session.id,
                response=(
                    "Não encontrei formas de pagamento ativas no CorePet. O pedido não "
                    "foi lançado; primeiro é preciso configurar ao menos uma forma."
                ),
                intent="pedido_sem_forma_pagamento",
                model_used="deterministic_checkout_no_payment",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        preview = self._enrich_checkout_preview(preview)
        session_context[ORDER_CHECKOUT_CONTEXT_KEY] = {
            "stage": "fulfillment",
            "source": source,
            "items": requested_items,
            "preview": preview,
            "idempotency_key": str(uuid.uuid4()),
        }
        session_context.pop(ORDER_DRAFT_CONTEXT_KEY, None)
        session_context.pop(ORDER_ITEM_SELECTION_CONTEXT_KEY, None)
        self._save_session_context(session, session_context)
        return await self._send_response(
            session_id=session.id,
            response=(
                "Perfeito. Como você prefere receber?\n\n"
                "1. Entrega\n\n"
                "2. Retirada na loja\n\n"
                "Pode responder do seu jeito, como ‘pode entregar’ ou ‘vou buscar’. "
                "Se preferir, envie 1 ou 2."
            ),
            intent="pedido_escolha_entrega",
            model_used="deterministic_checkout_fulfillment",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
        )

    async def _handle_pending_checkout(
        self,
        *,
        session: WhatsAppSession,
        session_context: Dict[str, Any],
        checkout: Dict[str, Any],
        message_content: str,
    ) -> Optional[Dict[str, Any]]:
        if is_order_cancellation(message_content):
            session_context.pop(ORDER_CHECKOUT_CONTEXT_KEY, None)
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response="Certo, cancelei este pedido antes da confirmação.",
                intent="pedido_cancelado_antes_confirmacao",
                model_used="deterministic_checkout_cancel",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        stage = str(checkout.get("stage") or "fulfillment")
        preview = checkout.get("preview") or {}
        decision = await self._checkout_context_decision(
            message_content=message_content,
            checkout=checkout,
        )

        information_response = self._checkout_information_response(
            action=decision.action if decision else "",
            checkout=checkout,
        )
        if information_response:
            return await self._send_response(
                session_id=session.id,
                response=information_response,
                intent=f"pedido_contexto_{decision.action}",
                model_used="contextual_checkout_orchestrator",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if (
            decision
            and decision.action == "new_request"
            and decision.confidence >= 0.85
        ):
            session_context.pop(ORDER_CHECKOUT_CONTEXT_KEY, None)
            session_context.pop(ORDER_DRAFT_CONTEXT_KEY, None)
            session_context.pop(ORDER_ITEM_SELECTION_CONTEXT_KEY, None)
            self._save_session_context(session, session_context)
            return None

        asks_registered_address = is_registered_address_question(message_content) or (
            decision is not None and decision.action == "ask_registered_address"
        )
        if asks_registered_address:
            if stage == "delivery_address":
                checkout.pop("delivery_address_partial", None)
            registered_address = self._registered_delivery_address(session, preview)
            if not registered_address:
                response = (
                    "Encontrei seu cadastro, mas ele está sem endereço de entrega "
                    "preenchido."
                )
                if stage == "delivery_address":
                    response += " Me envie rua, número, bairro e CEP para continuar."
                else:
                    response += f"\n\n{self._current_checkout_prompt(checkout)}"
            elif stage != "delivery_address":
                response = (
                    f"Seu endereço de entrega cadastrado é: {registered_address}.\n\n"
                    f"{self._current_checkout_prompt(checkout)}"
                )
            else:
                missing = delivery_address_missing_fields(registered_address)
                if missing:
                    checkout["delivery_address_partial"] = registered_address
                    response = (
                        f"Encontrei este endereço no cadastro: {registered_address}. "
                        f"{self._missing_address_prompt(registered_address, missing)}"
                    )
                else:
                    checkout["registered_address_candidate"] = registered_address
                    checkout["stage"] = "delivery_address_confirmation"
                    response = (
                        f"Tenho este endereço cadastrado: {registered_address}. "
                        "Posso usar este endereço para a entrega?"
                    )
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=response,
                intent="pedido_consulta_endereco_cadastrado",
                model_used=(
                    "contextual_checkout_orchestrator"
                    if decision and decision.action == "ask_registered_address"
                    else "deterministic_checkout_registered_address"
                ),
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if stage == "fulfillment":
            fulfillment = parse_fulfillment_choice(message_content)
            if not fulfillment and decision:
                if decision.action == "choose_delivery":
                    fulfillment = "delivery"
                elif decision.action == "choose_pickup":
                    fulfillment = "pickup"
            if not fulfillment:
                response = (
                    "Você prefere que a gente entregue ou quer retirar na loja? "
                    "Pode responder do seu jeito."
                )
            else:
                checkout["fulfillment"] = fulfillment
                response = self._next_checkout_prompt(checkout)
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=response,
                intent="pedido_escolha_entrega",
                model_used="deterministic_checkout_fulfillment",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if stage == "delivery_address":
            message_missing = delivery_address_missing_fields(message_content)
            if (
                decision is not None
                and decision.action not in {"provide_address", "other"}
            ) or (
                decision is not None
                and decision.action == "other"
                and len(message_missing) == 4
            ):
                return await self._send_response(
                    session_id=session.id,
                    response=(
                        "Entendi, mas ainda preciso confirmar onde será a entrega. "
                        "Você pode me passar rua, número, bairro e CEP, ou pedir para eu "
                        "consultar o endereço cadastrado."
                    ),
                    intent="pedido_aguardando_endereco",
                    model_used="contextual_checkout_orchestrator",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )
            if decision is None and len(message_missing) == 4:
                return await self._send_response(
                    session_id=session.id,
                    response=(
                        "Não identifiquei um endereço nessa mensagem. Me passe rua, número, "
                        "bairro e CEP, ou diga que quer usar o endereço cadastrado."
                    ),
                    intent="pedido_aguardando_endereco",
                    model_used="deterministic_checkout_address_guard",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )
            delivery_address = merge_delivery_address(
                str(checkout.get("delivery_address_partial") or ""),
                message_content,
            )
            missing = delivery_address_missing_fields(delivery_address)
            if missing:
                checkout["delivery_address_partial"] = delivery_address
                response = self._missing_address_prompt(delivery_address, missing)
            else:
                checkout["delivery_address"] = delivery_address
                checkout.pop("delivery_address_partial", None)
                response = self._next_checkout_prompt(checkout)
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=response,
                intent="pedido_endereco_entrega",
                model_used="deterministic_checkout_address",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if stage == "payment":
            payment_methods = preview.get("payment_methods") or []
            payment_method = parse_payment_choice(message_content, payment_methods)
            if not payment_method:
                payment_method = self._payment_from_context_decision(
                    decision, payment_methods
                )
            if not payment_method:
                response = (
                    "Ainda não consegui identificar a forma de pagamento. Escolha uma "
                    "das opções disponíveis abaixo.\n\n"
                    f"{payment_methods_message(payment_methods)}"
                )
            else:
                checkout["payment_method"] = payment_method
                checkout.pop("cash_change_answered", None)
                checkout.pop("cash_change_for", None)
                response = self._next_checkout_prompt(checkout)
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=response,
                intent="pedido_escolha_pagamento",
                model_used="deterministic_checkout_payment",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if stage == "delivery_address_confirmation":
            candidate = str(checkout.get("registered_address_candidate") or "").strip()
            if decision and decision.action == "provide_address":
                confirmation = False
            elif decision and decision.action == "confirm":
                confirmation = True
            elif decision and decision.action == "reject":
                confirmation = False
            else:
                confirmation = await self._interpret_confirmation_reply(
                    message_content,
                    pending_question=f"Posso usar este endereço para entrega: {candidate}?",
                )
            if confirmation is True and candidate:
                checkout["delivery_address"] = candidate
                checkout.pop("registered_address_candidate", None)
                response = self._next_checkout_prompt(checkout)
            elif confirmation is False:
                checkout["stage"] = "delivery_address"
                checkout.pop("registered_address_candidate", None)
                checkout.pop("delivery_address", None)
                checkout.pop("delivery_address_partial", None)
                if decision and decision.action == "provide_address":
                    delivery_address = message_content.strip()
                    missing = delivery_address_missing_fields(delivery_address)
                    if missing:
                        checkout["delivery_address_partial"] = delivery_address
                        response = self._missing_address_prompt(
                            delivery_address, missing
                        )
                    else:
                        checkout["delivery_address"] = delivery_address
                        response = self._next_checkout_prompt(checkout)
                else:
                    response = (
                        "Sem problema. Qual endereço você quer usar? Me envie rua, número, "
                        "bairro e CEP."
                    )
            else:
                response = (
                    f"Tenho este endereço cadastrado: {candidate}. Posso usá-lo para "
                    "a entrega? Pode responder do seu jeito."
                )
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=response,
                intent="pedido_confirma_endereco_cadastrado",
                model_used="deterministic_checkout_registered_address_confirmation",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if stage == "cash_change":
            change = parse_cash_change(
                message_content,
                total=float(preview.get("total") or preview.get("subtotal") or 0),
            )
            if not change and decision and decision.action == "no_cash_change":
                change = {"needs_change": False, "amount": None}
            elif not change and decision and decision.action == "cash_change":
                try:
                    amount = float(str(decision.value).replace(",", "."))
                except (TypeError, ValueError):
                    amount = None
                change = (
                    {
                        "needs_change": True,
                        "amount": amount,
                        "valid": amount
                        > float(preview.get("total") or preview.get("subtotal") or 0),
                    }
                    if amount is not None
                    else {"needs_change": True, "amount": None}
                )
            if not change:
                response = "Vai precisar de troco? Se sim, me diga para qual valor."
            elif change.get("needs_change") and change.get("amount") is None:
                response = "Claro. Troco para qual valor?"
            elif change.get("needs_change") and not change.get("valid", True):
                response = (
                    "O valor do troco precisa ser maior que o total do pedido, que é "
                    f"{_format_brl(preview.get('total'))}. Para quanto será o troco?"
                )
            else:
                checkout["cash_change_answered"] = True
                checkout["cash_change_for"] = change.get("amount")
                response = self._next_checkout_prompt(checkout)
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=response,
                intent="pedido_troco_dinheiro",
                model_used="deterministic_checkout_cash_change",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        quantity_change = parse_quantity_change(message_content)
        if (
            quantity_change is None
            and decision
            and decision.action == "change_quantity"
        ):
            try:
                contextual_quantity = float(str(decision.value).replace(",", "."))
            except (TypeError, ValueError):
                contextual_quantity = 0
            quantity_change = contextual_quantity if contextual_quantity > 0 else None
        if quantity_change is not None:
            requested_items = checkout.get("items") or []
            if len(requested_items) != 1:
                response = "Claro, posso alterar. De qual produto você quer mudar a quantidade?"
            else:
                updated_items = [
                    {
                        "product_id": requested_items[0]["product_id"],
                        "quantity": quantity_change,
                    }
                ]
                updated_preview = self._fetch_remote_order_preview(
                    self.tenant_id,
                    phone=session.phone_number,
                    items=updated_items,
                )
                if not updated_preview or not updated_preview.get("success"):
                    detail = str((updated_preview or {}).get("detail") or "").strip()
                    response = (
                        f"Não consegui alterar para essa quantidade: {detail}"
                        if detail
                        else "Não consegui recalcular essa quantidade agora."
                    )
                else:
                    checkout["items"] = updated_items
                    checkout["preview"] = self._enrich_checkout_preview(updated_preview)
                    checkout["idempotency_key"] = str(uuid.uuid4())
                    preview = checkout["preview"]
                    quantity_text = (
                        str(int(quantity_change))
                        if quantity_change.is_integer()
                        else str(quantity_change).replace(".", ",")
                    )
                    response = (
                        f"Claro, alterei para {quantity_text} unidade(s).\n\n"
                        f"{self._next_checkout_prompt(checkout)}"
                    )
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=response,
                intent="pedido_quantidade_alterada",
                model_used="deterministic_checkout_quantity_change",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        normalized_message = _normalize_text(message_content)
        wants_change = any(
            term in normalized_message
            for term in ("altera", "alterar", "muda", "mudar", "troca", "trocar")
        ) or bool(
            decision
            and decision.action
            in {
                "modify_order",
                "reject",
                "choose_delivery",
                "choose_pickup",
                "choose_payment",
            }
        )
        if wants_change:
            payment_methods = preview.get("payment_methods") or []
            payment_change = parse_payment_choice(message_content, payment_methods)
            if not payment_change:
                payment_change = self._payment_from_context_decision(
                    decision, payment_methods
                )
            fulfillment_change = parse_fulfillment_choice(message_content)
            if not fulfillment_change and decision:
                if decision.action == "choose_delivery":
                    fulfillment_change = "delivery"
                elif decision.action == "choose_pickup":
                    fulfillment_change = "pickup"
            if payment_change:
                checkout["payment_method"] = payment_change
                checkout.pop("cash_change_answered", None)
                checkout.pop("cash_change_for", None)
                response = (
                    f"Claro, mudei o pagamento para {payment_change.get('name')}.\n\n"
                    f"{self._next_checkout_prompt(checkout)}"
                )
            elif fulfillment_change:
                checkout["fulfillment"] = fulfillment_change
                if fulfillment_change == "pickup":
                    checkout.pop("delivery_address", None)
                    checkout.pop("delivery_address_partial", None)
                response = self._next_checkout_prompt(checkout)
            elif "endereco" in normalized_message:
                checkout["stage"] = "delivery_address"
                checkout["delivery_address_partial"] = ""
                checkout.pop("delivery_address", None)
                response = self._missing_address_prompt(
                    "", ["rua", "número", "bairro", "CEP"]
                )
            else:
                response = (
                    "Claro, ainda dá para ajustar. Me diga o que você quer mudar: "
                    "produto ou quantidade, entrega/endereço, ou forma de pagamento."
                )
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=response,
                intent="pedido_solicitacao_alteracao",
                model_used="deterministic_checkout_context_change",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if not is_final_order_confirmation(message_content):
            return await self._send_response(
                session_id=session.id,
                response=(
                    "Seu pedido ainda está aguardando sua confirmação. Se estiver "
                    "tudo certo, diga CONFIRMAR. Se quiser mudar algo, pode falar "
                    "normalmente, por exemplo: ‘troca para PIX’ ou ‘altera para retirada’."
                ),
                intent="pedido_aguardando_confirmacao_final",
                model_used=(
                    "contextual_checkout_orchestrator"
                    if decision
                    else "deterministic_checkout_confirmation"
                ),
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        readiness_response = self._next_checkout_prompt(checkout)
        if checkout.get("stage") != "confirmation":
            self._save_session_context(session, session_context)
            return await self._send_response(
                session_id=session.id,
                response=readiness_response,
                intent="pedido_dados_pendentes",
                model_used="deterministic_checkout_pending_data",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        created = self._create_remote_order(
            self.tenant_id,
            phone=session.phone_number,
            items=checkout.get("items") or [],
            fulfillment=str(checkout.get("fulfillment") or "pickup"),
            payment_method=checkout.get("payment_method") or {},
            delivery_address=checkout.get("delivery_address"),
            cash_change_for=checkout.get("cash_change_for"),
            idempotency_key=str(checkout.get("idempotency_key") or ""),
        )
        if not created or not created.get("success"):
            return await self._send_response(
                session_id=session.id,
                response=(
                    "Não consegui lançar a venda no CorePet agora. Nenhuma nova venda "
                    "foi confirmada; pode responder CONFIRMAR para tentar novamente."
                ),
                intent="pedido_criacao_indisponivel",
                model_used="deterministic_checkout_create_error",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        session_context.pop(ORDER_CHECKOUT_CONTEXT_KEY, None)
        session_context.pop(ORDER_DRAFT_CONTEXT_KEY, None)
        session_context.pop(CATALOG_SEARCH_CONTEXT_KEY, None)
        self._save_session_context(session, session_context)
        fulfillment_label = (
            "entrega"
            if created.get("fulfillment") == "delivery"
            else "retirada na loja"
        )
        payment = created.get("payment_method") or checkout.get("payment_method") or {}
        lines = [
            "Prontinho! Recebemos seu pedido 😊",
            f"Pedido nº {created.get('number')}",
            f"Total: {_format_brl(created.get('total'))}",
            f"Recebimento: {fulfillment_label.capitalize()}",
            f"Pagamento: {payment.get('name') or payment.get('nome') or payment.get('key')}",
        ]
        benefits = created.get("benefits") or []
        if benefits:
            lines.extend(["Você ganhou:", *benefits_lines(benefits)])
        if created.get("fulfillment") == "delivery" and created.get(
            "delivery_address_registered"
        ):
            lines.append(
                "Também deixei este endereço salvo para facilitar seus próximos pedidos."
            )
        lines.append(
            "Agora nossa equipe vai preparar tudo. Se precisar ajustar alguma coisa, "
            "é só chamar."
        )
        return await self._send_response(
            session_id=session.id,
            response="\n\n".join(lines),
            intent="pedido_venda_aberta_criada",
            model_used="deterministic_checkout_created",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
        )

    async def _handle_order_checkout_flow(
        self,
        *,
        session: WhatsAppSession,
        session_context: Dict[str, Any],
        message_content: str,
    ) -> Optional[Dict[str, Any]]:
        pending_checkout = session_context.get(ORDER_CHECKOUT_CONTEXT_KEY)
        if isinstance(pending_checkout, dict):
            stage = str(pending_checkout.get("stage") or "fulfillment")
            if stage == "confirmation" and is_new_conversation_greeting(
                message_content
            ):
                session_context.pop(ORDER_CHECKOUT_CONTEXT_KEY, None)
                session_context.pop(ORDER_DRAFT_CONTEXT_KEY, None)
                session_context.pop(ORDER_ITEM_SELECTION_CONTEXT_KEY, None)
                session_context.pop(HISTORY_ITEM_SELECTION_CONTEXT_KEY, None)
                session_context.pop(CATALOG_SEARCH_CONTEXT_KEY, None)
                self._save_session_context(session, session_context)
                return await self._send_response(
                    session_id=session.id,
                    response=(
                        "Oi! 😊 Aquele pedido anterior não tinha sido confirmado, então "
                        "encerrei apenas o rascunho. "
                        "Como posso ajudar agora?"
                    ),
                    intent="novo_atendimento_apos_checkout",
                    model_used="deterministic_checkout_new_conversation",
                    tokens_input=0,
                    tokens_output=0,
                    processing_time_ms=0,
                )

            if stage == "confirmation" and _product_query_from_choice_phrase(
                _strip_audio_marker(message_content)
            ):
                session_context.pop(ORDER_CHECKOUT_CONTEXT_KEY, None)
                session_context.pop(ORDER_DRAFT_CONTEXT_KEY, None)
                session_context.pop(ORDER_ITEM_SELECTION_CONTEXT_KEY, None)
                session_context.pop(HISTORY_ITEM_SELECTION_CONTEXT_KEY, None)
                session_context.pop(CATALOG_SEARCH_CONTEXT_KEY, None)
                self._save_session_context(session, session_context)
                pending_checkout = None

        if isinstance(pending_checkout, dict):
            return await self._handle_pending_checkout(
                session=session,
                session_context=session_context,
                checkout=pending_checkout,
                message_content=message_content,
            )

        pending_selection = session_context.get(ORDER_ITEM_SELECTION_CONTEXT_KEY)
        if isinstance(pending_selection, dict):
            selected_text = re.sub(r"\D", "", message_content or "")
            options = pending_selection.get("options") or []
            if selected_text and len(selected_text) <= 2:
                selected_index = int(selected_text) - 1
                if 0 <= selected_index < len(options):
                    return await self._start_order_checkout(
                        session=session,
                        session_context=session_context,
                        items=[options[selected_index]],
                        source="catalog_selection",
                    )
            return await self._send_response(
                session_id=session.id,
                response="Escolha o número do produto que deseja comprar.",
                intent="pedido_escolha_produto",
                model_used="deterministic_checkout_product_selection",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
            )

        if not is_order_checkout_request(message_content):
            return None

        catalog_context = session_context.get(CATALOG_SEARCH_CONTEXT_KEY)
        options = (
            catalog_context.get("options") if isinstance(catalog_context, dict) else []
        ) or []
        options = [
            option
            for option in options
            if isinstance(option, dict) and float(option.get("estoque") or 0) > 0
        ]
        if len(options) == 1:
            return await self._start_order_checkout(
                session=session,
                session_context=session_context,
                items=[options[0]],
                source="catalog_single_result",
            )
        if len(options) > 1:
            session_context[ORDER_ITEM_SELECTION_CONTEXT_KEY] = {"options": options}
            self._save_session_context(session, session_context)
            lines = ["Qual destes produtos você deseja comprar?"]
            lines.extend(
                f"{index}. {option.get('nome')} — {_format_brl(option.get('preco'))}"
                for index, option in enumerate(options, start=1)
            )
            lines.append("Responda com o número.")
            return await self._send_response(
                session_id=session.id,
                response="\n\n".join(lines),
                intent="pedido_escolha_produto",
                model_used="deterministic_checkout_product_selection",
                tokens_input=0,
                tokens_output=0,
                processing_time_ms=0,
                product_media=draft_product_media(options),
            )
        return await self._send_response(
            session_id=session.id,
            response=(
                "Qual produto você deseja comprar? Envie o nome e a embalagem para eu "
                "consultar o catálogo antes de fechar."
            ),
            intent="pedido_sem_produto_selecionado",
            model_used="deterministic_checkout_missing_selection",
            tokens_input=0,
            tokens_output=0,
            processing_time_ms=0,
        )
