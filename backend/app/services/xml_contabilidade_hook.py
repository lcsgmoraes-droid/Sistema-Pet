"""Enfileiramento contábil sem comprometer a transação da nota fiscal."""

import logging

logger = logging.getLogger(__name__)


def tentar_enfileirar_documento(db, tenant_id, provider, documento_id):
    """A fila é opcional para emitir; seu erro fica restrito ao savepoint.

    O commit pertence ao fluxo fiscal. O flush dentro do savepoint também
    protege a emissão quando o banco ainda não recebeu a migration da fila.
    """
    try:
        from app.services.xml_contabilidade_service import enfileirar_documento

        with db.begin_nested():
            enfileirar_documento(db, tenant_id, provider, documento_id)
            db.flush()
    except Exception as exc:
        # Não registrar XML, destinatário, credenciais ou conteúdo da exceção.
        logger.warning(
            "Falha ao enfileirar XML contábil; provider=%s documento_id=%s erro=%s",
            provider,
            documento_id,
            type(exc).__name__,
        )
