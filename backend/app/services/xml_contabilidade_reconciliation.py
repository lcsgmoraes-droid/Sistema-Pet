"""Confirma emissões novas sem depender de a tela fiscal continuar aberta."""

import logging
from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from app.intnfe.client import IntNFeClient
from app.intnfe.emission import _access_token, _connection, reconcile
from app.vendas_models import Venda

logger = logging.getLogger(__name__)
BRASILIA = ZoneInfo("America/Sao_Paulo")
LIMITE_POR_CICLO = 10
STATUS_PENDENTES = ("aguardando", "processando", "contingencia", "enviando", "inconclusiva")


def reconciliar_pendentes(db, tenant_id, desde):
    """Chamado com envio automático ativo, antes de reservar itens da fila.

    ``reconcile`` confirma e comita cada documento, enfileirando seu XML pelo
    mesmo hook da emissão. Este trabalho não pode compartilhar alterações
    pendentes com o processamento de um e-mail.
    """
    if desde is None:
        return 0
    api = None
    confirmadas = 0
    try:
        # A emissão direta usa datetime.now() e coluna sem fuso; a API em
        # produção está configurada para America/Sao_Paulo no compose.
        ativacao = desde if desde.tzinfo else desde.replace(tzinfo=timezone.utc)
        inicio = ativacao.astimezone(BRASILIA).replace(tzinfo=None)
        vendas = db.query(Venda).filter(
            Venda.tenant_id == UUID(str(tenant_id)),
            Venda.nfe_provider == "intnfe",
            Venda.nfe_ambiente == 1,
            Venda.nfe_status.in_(STATUS_PENDENTES),
            Venda.nfe_correlation_id.isnot(None),
            Venda.nfe_correlation_id != "",
            Venda.nfe_data_emissao >= inicio,
        ).order_by(Venda.updated_at.asc(), Venda.id.asc()).limit(LIMITE_POR_CICLO).all()
        if not vendas:
            return 0
        api = IntNFeClient()
        connection = _connection(db, tenant_id, require_enabled=False)
        token = _access_token(api, connection, 1)
        for venda in vendas:
            try:
                # Alterna entre pendentes mesmo quando o emissor mantém o
                # mesmo status (por exemplo, uma NFC-e em contingência).
                venda.updated_at = datetime.now()
                result = reconcile(db, venda, api, connection=connection, token=token)
                confirmadas += int(bool(result.get("success")))
            except Exception as exc:
                db.rollback()
                logger.warning("Falha ao consultar emissão contábil; erro=%s", type(exc).__name__)
    except Exception as exc:
        db.rollback()
        logger.warning("Falha na reconciliação contábil IntNFe; erro=%s", type(exc).__name__)
    finally:
        if api is not None:
            try:
                api.close()
            except Exception as exc:
                logger.warning("Falha ao fechar cliente IntNFe; erro=%s", type(exc).__name__)
    return confirmadas
