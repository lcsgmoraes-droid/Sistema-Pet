
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.produtos_models import Produto
from app.pedido_integrado_item_models import PedidoIntegradoItem

class EstoqueReservaService:
    """
    Serviço central de reserva de estoque.
    Trabalha por SKU.
    """

    @staticmethod
    def _quantidade_reservada(db: Session, sku: str):
        return db.query(
            func.coalesce(func.sum(PedidoIntegradoItem.quantidade), 0)
        ).filter(
            PedidoIntegradoItem.sku == sku,
            PedidoIntegradoItem.liberado_em.is_(None),
            PedidoIntegradoItem.vendido_em.is_(None)
        ).scalar()

    @staticmethod
    def reservar(db: Session, item: PedidoIntegradoItem):
        produto = db.query(Produto).filter(
            Produto.sku == item.sku
        ).first()

        if not produto:
            raise ValueError(f"Produto com SKU {item.sku} não encontrado")

        reservado = EstoqueReservaService._quantidade_reservada(db, item.sku)
        disponivel = produto.estoque_atual - reservado

        if disponivel < item.quantidade:
            raise ValueError(
                f"Estoque insuficiente para SKU {item.sku}. "
                f"Disponível: {disponivel}, solicitado: {item.quantidade}"
            )

        # Reserva é lógica: só manter o item ativo
        return True

    @staticmethod
    def liberar(db: Session, item: PedidoIntegradoItem):
        item.liberado_em = datetime.utcnow()
        db.add(item)
        db.commit()

    @staticmethod
    def confirmar_venda(db: Session, item: PedidoIntegradoItem):
        item.vendido_em = datetime.utcnow()
        db.add(item)
        db.commit()
