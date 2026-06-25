"""Rotas de recebimento e entrada automatica em estoque."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..auth.dependencies import get_current_user_and_tenant
from ..db import get_session
from ..produtos_models import (
    EstoqueMovimentacao,
    PedidoCompra,
    PedidoCompraItem,
    Produto,
    ProdutoLote,
)
from .schemas import RecebimentoPedidoRequest

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# RECEBER PEDIDO (com entrada automática no estoque)
# ============================================================================


@router.post("/{pedido_id}/receber")
def receber_pedido(
    pedido_id: int,
    request: RecebimentoPedidoRequest,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Recebe pedido (total ou parcial) e dá entrada automática no estoque
    """
    current_user, tenant_id = current_user_and_tenant
    logger.info(f"📦 Recebendo pedido {pedido_id}")

    pedido = (
        db.query(PedidoCompra)
        .options(joinedload(PedidoCompra.itens))
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status not in ["confirmado", "recebido_parcial"]:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido não pode ser recebido no status '{pedido.status}'",
        )

    data_recebimento = request.data_recebimento or datetime.utcnow()
    itens_recebidos = []
    para_sync_bling = []  # (produto_id, estoque_atual)

    # Processar cada item
    for receb_item in request.itens:
        # Buscar item
        item = (
            db.query(PedidoCompraItem)
            .filter(
                PedidoCompraItem.id == receb_item.item_id,
                PedidoCompraItem.pedido_compra_id == pedido_id,
            )
            .first()
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Item {receb_item.item_id} não encontrado no pedido",
            )

        # Validar quantidade
        quantidade_pendente = item.quantidade_pedida - item.quantidade_recebida
        if receb_item.quantidade_recebida > quantidade_pendente:
            raise HTTPException(
                status_code=400,
                detail=f"Item {item.id}: quantidade recebida ({receb_item.quantidade_recebida}) "
                f"maior que pendente ({quantidade_pendente})",
            )

        # Atualizar quantidade recebida
        item.quantidade_recebida += receb_item.quantidade_recebida

        # Atualizar status do item
        if item.quantidade_recebida >= item.quantidade_pedida:
            item.status = "recebido_total"
        else:
            item.status = "recebido_parcial"

        # DAR ENTRADA NO ESTOQUE
        produto = (
            db.query(Produto)
            .filter(Produto.id == item.produto_id, Produto.tenant_id == tenant_id)
            .first()
        )
        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto {item.produto_id} nao encontrado para o item {item.id}",
            )

        # Criar lote
        numero_lote = f"PC{pedido.id}-{item.id}"
        custo_unitario_lote = float(item.preco_unitario or 0) - float(
            item.desconto_item or 0
        )

        lote = ProdutoLote(
            produto_id=produto.id,
            nome_lote=numero_lote,
            quantidade_inicial=receb_item.quantidade_recebida,
            quantidade_disponivel=receb_item.quantidade_recebida,
            quantidade_reservada=0,
            custo_unitario=custo_unitario_lote,
            data_fabricacao=None,
            data_validade=None,
            ordem_entrada=int(datetime.utcnow().timestamp()),
            status="ativo",
            tenant_id=tenant_id,
        )
        db.add(lote)
        db.flush()

        # Atualizar estoque do produto
        produto.estoque_atual = (
            produto.estoque_atual or 0
        ) + receb_item.quantidade_recebida

        # Recalcular custo médio ponderado
        if produto.custo_medio:
            estoque_anterior = (
                produto.estoque_atual or 0
            ) - receb_item.quantidade_recebida
            valor_anterior = estoque_anterior * produto.custo_medio
            valor_entrada = receb_item.quantidade_recebida * lote.custo_unitario
            produto.custo_medio = (
                valor_anterior + valor_entrada
            ) / produto.estoque_atual
        else:
            produto.custo_medio = lote.custo_unitario

        # Registrar movimentação
        movimentacao = EstoqueMovimentacao(
            produto_id=produto.id,
            lote_id=lote.id,
            tipo_movimentacao="entrada",
            quantidade=receb_item.quantidade_recebida,
            custo_unitario=lote.custo_unitario,
            motivo=f"Recebimento do pedido {pedido.numero_pedido}",
            documento=pedido.numero_pedido,
            estoque_anterior=(produto.estoque_atual or 0)
            - receb_item.quantidade_recebida,
            estoque_atual=produto.estoque_atual,
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
        db.add(movimentacao)

        itens_recebidos.append(
            {
                "item_id": item.id,
                "produto_id": produto.id,
                "produto_nome": produto.nome,
                "quantidade_recebida": receb_item.quantidade_recebida,
                "lote": numero_lote,
                "status": item.status,
            }
        )
        para_sync_bling.append((produto.id, produto.estoque_atual))

        logger.info(
            f"  ✅ Item {item.id}: {produto.nome} - "
            f"{receb_item.quantidade_recebida} unidades recebidas"
        )

    # Atualizar status do pedido
    todos_recebidos = all(item.status == "recebido_total" for item in pedido.itens)
    algum_recebido = any(item.quantidade_recebida > 0 for item in pedido.itens)

    if todos_recebidos:
        pedido.status = "recebido_total"
        pedido.data_recebimento = data_recebimento
    elif algum_recebido:
        pedido.status = "recebido_parcial"
        if not pedido.data_recebimento:
            pedido.data_recebimento = data_recebimento

    pedido.updated_at = datetime.utcnow()

    db.commit()

    # SINCRONIZAR ESTOQUE COM BLING para todos os itens recebidos
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        for produto_id, estoque_novo in para_sync_bling:
            sincronizar_bling_background(
                produto_id, estoque_novo, "recebimento_pedido_compra"
            )
    except Exception as e_sync:
        logger.warning(f"[BLING-SYNC] Erro ao agendar sync (pedido_compra): {e_sync}")

    logger.info(f"✅ Pedido {pedido.numero_pedido} recebido - Status: {pedido.status}")

    return {
        "message": "Recebimento processado com sucesso",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "status": pedido.status,
        "itens_recebidos": len(itens_recebidos),
        "detalhes": itens_recebidos,
    }
