"""Helpers de vinculo e persistencia do confronto de pedidos de compra."""

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.produtos_models import PedidoCompra, PedidoCompraNotaEntrada


def _ids_notas_vinculadas(
    db: Session, pedido: PedidoCompra, tenant_id: int
) -> List[int]:
    ids = [
        row[0]
        for row in db.query(PedidoCompraNotaEntrada.nota_entrada_id)
        .filter(
            PedidoCompraNotaEntrada.pedido_compra_id == pedido.id,
            PedidoCompraNotaEntrada.tenant_id == tenant_id,
        )
        .order_by(PedidoCompraNotaEntrada.id.asc())
        .all()
    ]
    if not ids and pedido.nota_entrada_id:
        ids = [pedido.nota_entrada_id]
    return ids


def _garantir_vinculo_legado(
    db: Session, pedido: PedidoCompra, tenant_id: int, user_id: int
) -> None:
    if not pedido.nota_entrada_id:
        return
    existe = (
        db.query(PedidoCompraNotaEntrada.id)
        .filter(
            PedidoCompraNotaEntrada.pedido_compra_id == pedido.id,
            PedidoCompraNotaEntrada.nota_entrada_id == pedido.nota_entrada_id,
            PedidoCompraNotaEntrada.tenant_id == tenant_id,
        )
        .first()
    )
    if existe:
        return
    db.add(
        PedidoCompraNotaEntrada(
            pedido_compra_id=pedido.id,
            nota_entrada_id=pedido.nota_entrada_id,
            user_id=user_id,
            tenant_id=tenant_id,
        )
    )
    db.flush()


def _sincronizar_nota_legacy(pedido: PedidoCompra, nota_ids: List[int]) -> None:
    pedido.nota_entrada_id = nota_ids[0] if nota_ids else None


def _obter_notas_vinculadas(
    db: Session, pedido: PedidoCompra, tenant_id: int, com_itens: bool = False
) -> List:
    from app.produtos_models import NotaEntrada

    nota_ids = _ids_notas_vinculadas(db, pedido, tenant_id)
    if not nota_ids:
        return []

    query = db.query(NotaEntrada)
    if com_itens:
        query = query.options(joinedload(NotaEntrada.itens))

    notas = query.filter(
        NotaEntrada.id.in_(nota_ids),
        NotaEntrada.tenant_id == tenant_id,
    ).all()
    por_id = {n.id: n for n in notas}
    return [por_id[nid] for nid in nota_ids if nid in por_id]


def _buscar_pedido_finalizado_da_nota(
    db: Session, nota_id: int, pedido_id: int, tenant_id: int
) -> Optional[PedidoCompra]:
    pedido_por_vinculo = (
        db.query(PedidoCompra)
        .join(
            PedidoCompraNotaEntrada,
            PedidoCompraNotaEntrada.pedido_compra_id == PedidoCompra.id,
        )
        .filter(
            PedidoCompraNotaEntrada.nota_entrada_id == nota_id,
            PedidoCompraNotaEntrada.tenant_id == tenant_id,
            PedidoCompra.confronto_finalizado,
            PedidoCompra.id != pedido_id,
            PedidoCompra.tenant_id == tenant_id,
        )
        .first()
    )
    if pedido_por_vinculo:
        return pedido_por_vinculo

    return (
        db.query(PedidoCompra)
        .filter(
            PedidoCompra.nota_entrada_id == nota_id,
            PedidoCompra.confronto_finalizado,
            PedidoCompra.id != pedido_id,
            PedidoCompra.tenant_id == tenant_id,
        )
        .first()
    )


def _salvar_confronto_pedido(
    pedido: PedidoCompra, notas: List, confronto: dict
) -> None:
    pedido.data_confronto = datetime.utcnow()
    pedido.status_confronto = confronto["status_confronto"]
    pedido.resumo_confronto = json.dumps(confronto, ensure_ascii=False, default=str)
    pedido.updated_at = datetime.utcnow()
    _sincronizar_nota_legacy(pedido, [n.id for n in notas])
