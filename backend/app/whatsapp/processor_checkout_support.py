"""Metodos auxiliares do checkout conversacional do WhatsApp."""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.whatsapp.conversation_helpers import _format_brl
from app.whatsapp.conversation_orchestrator import (
    CheckoutDecision,
    interpret_checkout_message,
)
from app.whatsapp.models import WhatsAppSession
from app.whatsapp.order_checkout import (
    benefits_lines,
    build_checkout_summary,
    delivery_address_missing_fields,
    parse_payment_choice,
    payment_methods_message,
)
from app.whatsapp.tenant_context import whatsapp_tenant_context


logger = logging.getLogger(__name__)


class WhatsAppCheckoutSupportMixin:
    @staticmethod
    def _checkout_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        product_id = item.get("product_id") or item.get("id")
        if product_id in (None, ""):
            return None
        return {
            "product_id": int(product_id),
            "name": str(item.get("name") or item.get("nome") or "Produto"),
            "quantity": float(item.get("quantity") or 1),
            "unit": str(item.get("unit") or "x"),
            "unit_price": item.get("unit_price") or item.get("preco"),
            "image_url": str(item.get("image_url") or item.get("imagem_url") or ""),
        }

    def _loyalty_opportunity(self, total: Any) -> Optional[Dict[str, Any]]:
        """Calcula quanto falta para o próximo carimbo da campanha ativa."""
        from app.campaigns.models import (
            Campaign,
            CampaignStatusEnum,
            CampaignTypeEnum,
        )

        try:
            now = datetime.now(timezone.utc)
            with whatsapp_tenant_context(self.tenant_id):
                campaign = (
                    self.db.query(Campaign)
                    .filter(
                        Campaign.tenant_id == self.tenant_id,
                        Campaign.campaign_type == CampaignTypeEnum.loyalty_stamp,
                        Campaign.status == CampaignStatusEnum.active,
                        (Campaign.valid_from.is_(None) | (Campaign.valid_from <= now)),
                        (
                            Campaign.valid_until.is_(None)
                            | (Campaign.valid_until >= now)
                        ),
                    )
                    .order_by(Campaign.priority.asc(), Campaign.id.asc())
                    .first()
                )
            if not campaign:
                return None
            params = campaign.params or {}
            stamp_value = float(params.get("min_purchase_value") or 0)
            order_total = float(total or 0)
            if stamp_value <= 0 or order_total < 0:
                return None
            earned_stamps = int(order_total // stamp_value)
            next_target = (earned_stamps + 1) * stamp_value
            return {
                "name": campaign.name,
                "stamp_value": stamp_value,
                "earned_stamps": earned_stamps,
                "missing_amount": round(max(next_target - order_total, 0), 2),
                "stamps_to_complete": int(params.get("stamps_to_complete") or 0),
                "reward_value": float(params.get("reward_value") or 0),
            }
        except Exception as campaign_error:
            logger.warning(
                "Falha ao consultar campanha de fidelidade: %s", campaign_error
            )
            rollback = getattr(self.db, "rollback", None)
            if callable(rollback):
                rollback()
            return None

    def _registered_delivery_address(
        self,
        session: WhatsAppSession,
        preview: Dict[str, Any],
    ) -> str:
        preview_customer = preview.get("customer") or {}
        address = str(preview_customer.get("delivery_address") or "").strip()
        if address:
            return address

        customer_id = preview_customer.get("id")
        payload = self._fetch_remote_customer_context(
            self.tenant_id,
            phone=session.phone_number,
            customer_id=(int(customer_id) if customer_id not in (None, "") else None),
        )
        customer = payload.get("customer") if isinstance(payload, dict) else None
        if isinstance(customer, dict):
            address = str(customer.get("delivery_address") or "").strip()
            if address:
                return address
        latest_delivery = (
            payload.get("latest_delivery") if isinstance(payload, dict) else None
        )
        if not isinstance(latest_delivery, dict):
            return ""
        return str(latest_delivery.get("delivery_address") or "").strip()

    def _enrich_checkout_preview(self, preview: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(preview)
        opportunity = self._loyalty_opportunity(
            enriched.get("total") or enriched.get("subtotal")
        )
        if opportunity:
            enriched["loyalty_opportunity"] = opportunity
        return enriched

    @staticmethod
    def _missing_address_prompt(address: str, missing: list[str]) -> str:
        if not address:
            return (
                "Para entregar certinho, me envie rua, número, bairro e CEP. "
                "Exemplo: Rua das Flores, 44, Centro, 19000-000."
            )
        missing_text = (
            missing[0]
            if len(missing) == 1
            else f"{', '.join(missing[:-1])} e {missing[-1]}"
        )
        return f"Já anotei: {address}. Para completar o endereço, falta {missing_text}."

    def _next_checkout_prompt(self, checkout: Dict[str, Any]) -> str:
        """Avança somente até o próximo dado realmente necessário."""
        preview = checkout.get("preview") or {}
        if checkout.get("fulfillment") == "delivery":
            address = str(
                checkout.get("delivery_address")
                or checkout.get("delivery_address_partial")
                or (preview.get("customer") or {}).get("delivery_address")
                or ""
            ).strip()
            missing = delivery_address_missing_fields(address)
            if missing:
                checkout["stage"] = "delivery_address"
                checkout["delivery_address_partial"] = address
                checkout.pop("delivery_address", None)
                return self._missing_address_prompt(address, missing)
            checkout["delivery_address"] = address
            checkout.pop("delivery_address_partial", None)

        payment = checkout.get("payment_method") or {}
        if not payment:
            checkout["stage"] = "payment"
            return payment_methods_message(preview.get("payment_methods") or [])

        if str(payment.get("key") or "").lower() == "dinheiro" and not checkout.get(
            "cash_change_answered"
        ):
            checkout["stage"] = "cash_change"
            return "Vai precisar de troco? Se sim, para qual valor?"

        checkout["stage"] = "confirmation"
        return build_checkout_summary(checkout)

    def _current_checkout_prompt(self, checkout: Dict[str, Any]) -> str:
        """Retoma a etapa atual sem avançar ou alterar o pedido."""
        stage = str(checkout.get("stage") or "fulfillment")
        preview = checkout.get("preview") or {}
        if stage == "fulfillment":
            return "Para continuar: você prefere entrega ou retirada na loja?"
        if stage == "delivery_address":
            address = str(checkout.get("delivery_address_partial") or "").strip()
            return self._missing_address_prompt(
                address, delivery_address_missing_fields(address)
            )
        if stage == "delivery_address_confirmation":
            candidate = str(checkout.get("registered_address_candidate") or "").strip()
            return f"Posso usar este endereço para a entrega: {candidate}?"
        if stage == "payment":
            return payment_methods_message(preview.get("payment_methods") or [])
        if stage == "cash_change":
            return "Vai precisar de troco? Se sim, para qual valor?"
        return (
            "Se estiver tudo certo, diga CONFIRMAR. Se quiser mudar alguma coisa, "
            "pode me dizer o que deseja alterar."
        )

    async def _checkout_context_decision(
        self,
        *,
        message_content: str,
        checkout: Dict[str, Any],
    ) -> Optional[CheckoutDecision]:
        """Pede à IA somente uma ação estruturada; dados e escrita ficam no backend."""
        llm_client = getattr(self, "llm_client", None)
        if not getattr(self, "ai_enabled", False) or llm_client is None:
            return None
        if re.fullmatch(r"\s*\d{1,2}[.)]?\s*", message_content or ""):
            return None
        try:
            return await interpret_checkout_message(
                llm_client,
                message=message_content,
                checkout=checkout,
            )
        except Exception as error:
            logger.warning("Falha no orquestrador contextual do checkout: %s", error)
            return None

    def _checkout_information_response(
        self,
        *,
        action: str,
        checkout: Dict[str, Any],
    ) -> Optional[str]:
        """Responde perguntas do pedido apenas com os dados verificados do preview."""
        preview = checkout.get("preview") or {}
        prompt = self._current_checkout_prompt(checkout)
        if action == "ask_total":
            total = preview.get("total") or preview.get("subtotal")
            return f"Seu pedido está em {_format_brl(total)}.\n\n{prompt}"

        if action == "ask_items":
            items = preview.get("items") or checkout.get("items") or []
            lines = ["Até aqui, seu pedido está assim:"]
            for item in items:
                quantity = float(item.get("quantity") or item.get("quantidade") or 0)
                quantity_text = (
                    str(int(quantity))
                    if quantity.is_integer()
                    else str(quantity).replace(".", ",")
                )
                name = item.get("name") or item.get("nome") or "Produto"
                subtotal = item.get("subtotal")
                suffix = f" — {_format_brl(subtotal)}" if subtotal is not None else ""
                lines.append(f"- {quantity_text}x {name}{suffix}")
            lines.append(prompt)
            return "\n\n".join(lines)

        if action == "ask_benefits":
            benefits = preview.get("benefits") or []
            opportunity = preview.get("loyalty_opportunity") or {}
            lines = ["Com este pedido, você recebe:"]
            if benefits:
                lines.extend(benefits_lines(benefits))
            elif float(opportunity.get("missing_amount") or 0) > 0:
                lines.append(
                    "- Faltam "
                    f"{_format_brl(opportunity['missing_amount'])} para ganhar "
                    f"1 carimbo no {opportunity.get('name') or 'Clube Fidelidade'}."
                )
            else:
                lines = ["Este pedido não gera um benefício adicional no momento."]
            lines.append(prompt)
            return "\n\n".join(lines)
        return None

    @staticmethod
    def _payment_from_context_decision(
        decision: Optional[CheckoutDecision],
        payment_methods: list[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not decision or decision.action != "choose_payment":
            return None
        value = str(decision.value or "").strip()
        if not value:
            return None
        return parse_payment_choice(value, payment_methods)
