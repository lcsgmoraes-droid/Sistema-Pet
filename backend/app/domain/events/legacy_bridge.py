import logging
from app.domain.events.event_trace import trace_event

from app.events import subscribe_event, VendaRealizadaEvent
from app.domain.events import publish_event, VendaFinalizada

logger = logging.getLogger(__name__)

_BRIDGE_INITIALIZED = False


def _legacy_to_domain(event: VendaRealizadaEvent):
    """Bridge LEGACY -> DOMAIN (safe)."""

    try:
        metadados = event.metadados or {}

        novo_evento = VendaFinalizada(
            venda_id=event.venda_id,
            numero_venda=event.numero_venda,
            user_id=event.user_id,
            user_nome="legacy_bridge",
            cliente_id=event.cliente_id,
            funcionario_id=event.funcionario_id,
            total=float(event.total),
            total_pago=float(metadados.get("total_pago", event.total)),
            status=metadados.get("status", "finalizada"),
            formas_pagamento=metadados.get("formas_pagamento", []),
            estoque_baixado=True,
            caixa_movimentado=True,
            contas_baixadas=0,
            metadados={
                "bridge": "legacy_to_domain",
                "source_event": "VendaRealizadaEvent"
            }
        )

        trace_event("legacy_bridge", "VendaRealizadaEvent", event)
        publish_event(novo_evento)

        logger.info(
            f"🌉 Bridge legado→domain executado venda_id={event.venda_id}"
        )

    except Exception as e:
        logger.error(
            f"Erro no bridge legado→domain: {e}",
            exc_info=True
        )


def setup_legacy_bridge():
    global _BRIDGE_INITIALIZED

    if _BRIDGE_INITIALIZED:
        logger.warning("⚠️ Legacy bridge já inicializado — ignorando")
        return

    subscribe_event(VendaRealizadaEvent, _legacy_to_domain)

    _BRIDGE_INITIALIZED = True
    logger.info("✅ Legacy bridge ativado")