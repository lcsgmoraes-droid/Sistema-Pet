"""Enfileiramento contábil sem comprometer a transação da nota fiscal."""

import logging

logger = logging.getLogger(__name__)


def tentar_enfileirar_documento(db, tenant_id, provider, documento_id):
    """Só persistência local; o fluxo fiscal mantém o commit e nunca usa SMTP."""
    try:
        from app.services.xml_contabilidade_service import enfileirar_documento

        with db.begin_nested():
            enfileirar_documento(db, tenant_id, provider, documento_id)
            db.flush()
    except Exception as exc:
        logger.warning(
            "Falha ao enfileirar XML contábil; provider=%s documento_id=%s erro=%s",
            provider,
            documento_id,
            type(exc).__name__,
        )
