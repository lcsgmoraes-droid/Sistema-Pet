"""Limpeza dos vinculos que impedem excluir uma nota fiscal de entrada."""

from sqlalchemy.orm import Session, joinedload

from app.compras_pendencias_models import CompraPendenciaFornecedor
from app.produtos_models import (
    PedidoCompra,
    PedidoCompraNotaEntrada,
    ProdutoHistoricoPreco,
)


def limpar_vinculos_nota_entrada(
    db: Session, *, nota_id: int, tenant_id
) -> dict[str, int]:
    """Remove vinculos descartaveis e preserva historicos antes da nota ser apagada."""
    pendencias = (
        db.query(CompraPendenciaFornecedor)
        .options(
            joinedload(CompraPendenciaFornecedor.itens),
            joinedload(CompraPendenciaFornecedor.historico),
        )
        .filter(
            CompraPendenciaFornecedor.nota_entrada_id == nota_id,
            CompraPendenciaFornecedor.tenant_id == tenant_id,
        )
        .all()
    )
    for pendencia in pendencias:
        db.delete(pendencia)

    vinculos_pedido = (
        db.query(PedidoCompraNotaEntrada)
        .filter(
            PedidoCompraNotaEntrada.nota_entrada_id == nota_id,
            PedidoCompraNotaEntrada.tenant_id == tenant_id,
        )
        .all()
    )
    pedidos_afetados = {vinculo.pedido_compra_id for vinculo in vinculos_pedido}
    for vinculo in vinculos_pedido:
        db.delete(vinculo)

    pedidos_legados = (
        db.query(PedidoCompra)
        .filter(
            PedidoCompra.nota_entrada_id == nota_id,
            PedidoCompra.tenant_id == tenant_id,
        )
        .all()
    )
    pedidos_afetados.update(pedido.id for pedido in pedidos_legados)

    # Garante que pendencias/itens sejam removidos antes dos itens da NF e que os
    # vinculos N:N saiam antes de sincronizar o campo legado do pedido.
    db.flush()

    for pedido_id in pedidos_afetados:
        pedido = (
            db.query(PedidoCompra)
            .filter(
                PedidoCompra.id == pedido_id,
                PedidoCompra.tenant_id == tenant_id,
            )
            .first()
        )
        if not pedido:
            continue

        proximo_vinculo = (
            db.query(PedidoCompraNotaEntrada)
            .filter(
                PedidoCompraNotaEntrada.pedido_compra_id == pedido.id,
                PedidoCompraNotaEntrada.tenant_id == tenant_id,
            )
            .order_by(PedidoCompraNotaEntrada.id.asc())
            .first()
        )
        pedido.nota_entrada_id = (
            proximo_vinculo.nota_entrada_id if proximo_vinculo else None
        )
        if proximo_vinculo is None:
            pedido.data_confronto = None
            pedido.status_confronto = None
            pedido.resumo_confronto = None
            pedido.confronto_finalizado = False

    historicos_preservados = (
        db.query(ProdutoHistoricoPreco)
        .filter(
            ProdutoHistoricoPreco.nota_entrada_id == nota_id,
            ProdutoHistoricoPreco.tenant_id == tenant_id,
        )
        .update(
            {ProdutoHistoricoPreco.nota_entrada_id: None},
            synchronize_session=False,
        )
    )

    return {
        "pendencias_excluidas": len(pendencias),
        "pedidos_desvinculados": len(pedidos_afetados),
        "historicos_preservados": historicos_preservados,
    }
