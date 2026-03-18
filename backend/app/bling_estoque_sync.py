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

logger = logging.getLogger(__name__)


def sincronizar_bling_background(produto_id: int, estoque_novo: float, motivo: str = "") -> None:
    """
    Enfileira sincronização de estoque com o Bling em fila persistente.

    Não bloqueia. Se o Bling falhar, registra warning mas NÃO desfaz a operação
    de estoque no sistema.

    Args:
        produto_id: ID do produto no sistema
        estoque_novo: Novo saldo físico de estoque
        motivo: Motivo da alteração (venda, devolucao, ajuste_manual, etc.)
    """
    try:
        from app.services.bling_sync_service import BlingSyncService

        BlingSyncService.queue_product_sync_background(
            produto_id=produto_id,
            estoque_novo=estoque_novo,
            motivo=motivo,
            origem="evento",
        )
    except Exception as error:
        logger.warning("⚠️ Não foi possível enfileirar sync Bling (produto_id=%s): %s", produto_id, error)
