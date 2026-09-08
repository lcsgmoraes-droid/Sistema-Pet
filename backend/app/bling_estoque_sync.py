"""
Sincronização automática de estoque com o Bling

Este módulo é chamado pelo EstoqueService TODA VEZ que o estoque de um produto
muda — seja por venda PDV, entrada por XML, ajuste manual, devolução, etc.

A sincronização é enfileirada em fila persistente no banco e processada pelo
scheduler. Se o Bling estiver fora do ar, a fila faz retry automático e a operação
de estoque no sistema continua normalmente.

Ponto de entrada único: sincronizar_bling_background(produto_id, estoque_novo, motivo)
"""

import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def sincronizar_bling_background(
    produto_id: int, estoque_novo: float, motivo: str = "", *, db: Session | None = None
) -> None:
    """
    Enfileira sincronização de estoque com o Bling em fila persistente.

    Com db, a fila participa da transação de estoque e só fica disponível após
    seu commit. Falhas da fila ficam isoladas em savepoint. Sem db, o chamador
    deve já ter confirmado a alteração de estoque para usar uma sessão própria.

    Args:
        produto_id: ID do produto no sistema
        estoque_novo: Novo saldo físico de estoque
        motivo: Motivo da alteração (venda, devolucao, ajuste_manual, etc.)
        db: Sessão da operação de estoque, quando ela ainda não fez commit.
    """
    try:
        from app.services.bling_sync_service import BlingSyncService

        if db is not None:
            # Nunca abrir outra sessão esperando locks que o próprio chamador
            # já segura. O savepoint não confirma nem desfaz a venda externa.
            with db.begin_nested():
                BlingSyncService.queue_product_sync(
                    db,
                    produto_id=produto_id,
                    estoque_novo=estoque_novo,
                    motivo=motivo,
                    origem="evento",
                )
        else:
            BlingSyncService.queue_product_sync_background(
                produto_id=produto_id,
                estoque_novo=estoque_novo,
                motivo=motivo,
                origem="evento",
            )
    except Exception as error:
        logger.warning(
            "⚠️ Não foi possível enfileirar sync Bling (produto_id=%s): %s",
            produto_id,
            error,
        )
