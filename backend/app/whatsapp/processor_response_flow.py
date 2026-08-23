"""Envio, handoff e métricas do processador de WhatsApp."""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

from app.whatsapp.conversation_helpers import MAX_PRODUCT_IMAGES_PER_RESPONSE
from app.whatsapp.models import WhatsAppMetric, WhatsAppSession
from app.whatsapp.order_drafts import is_safe_product_image_url
from app.whatsapp.tenant_context import whatsapp_tenant_context

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


class WhatsAppResponseFlowMixin:
    """Responsabilidades de resposta, transferência humana e observabilidade."""

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
        fallback_message = await self._send_whatsapp_message(
            db=self.db,
            tenant_id=self.tenant_id,
            session_id=session_id,
            message="Recebi sua mensagem e já estou te atendendo. Pode me enviar novamente em texto curto?",
        )
        if fallback_message:
            return {"action": "fallback_responded", "error": str(error)}
        return {"action": "error", "error": str(error)}

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
        message = await self._send_whatsapp_message(
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
            image_message = await self._send_whatsapp_message(
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

            handoff_manager = self._create_handoff_manager(self.db, self.tenant_id)
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
        await self._send_whatsapp_message(
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
