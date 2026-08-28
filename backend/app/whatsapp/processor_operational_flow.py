"""Consultas operacionais do processador de mensagens do WhatsApp."""

import logging
from typing import Any, Dict, Optional

from app.whatsapp.conversation_helpers import (
    _customer_benefits_response,
    _delivery_status_response,
)
from app.whatsapp.customer_context_service import (
    load_customer_benefits,
    load_latest_delivery,
    load_store_hours,
)
from app.whatsapp.models import WhatsAppSession


logger = logging.getLogger(__name__)


class WhatsAppOperationalFlowMixin:
    """Responde consultas simples usando dados confiáveis do CorePet."""

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
