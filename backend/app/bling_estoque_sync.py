"""
Sincronização automática de estoque com o Bling

Este módulo é chamado pelo EstoqueService TODA VEZ que o estoque de um produto
muda — seja por venda PDV, entrada por XML, ajuste manual, devolução, etc.

A sincronização roda em background (thread separada) para NÃO bloquear a operação
principal. Se o Bling estiver fora do ar, apenas registra warning — a operação de
estoque no sistema continua normalmente.

Ponto de entrada único: sincronizar_bling_background(produto_id, estoque_novo, motivo)
"""

import logging

logger = logging.getLogger(__name__)


def sincronizar_bling_background(produto_id: int, estoque_novo: float, motivo: str = "") -> None:
    """
    Agenda sincronização de estoque com o Bling em background.

    Não bloqueia. Se o Bling falhar, registra warning mas NÃO desfaz a operação
    de estoque no sistema (que já foi commitada pelo caller).

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


def _executar_sync(produto_id: int, estoque_novo: float, motivo: str) -> None:
    """Executa a sincronização com o Bling (roda em thread separada)."""
    try:
        from app.services.bling_sync_service import BlingSyncService

        BlingSyncService.queue_product_sync_background(
            produto_id=produto_id,
            estoque_novo=estoque_novo,
            motivo=motivo,
            origem="evento",
        )
    except Exception as error:
        logger.warning(f"⚠️ Bling sync thread error (produto_id={produto_id}): {error}")
