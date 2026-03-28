
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime

from app.produtos_models import Produto
from app.pedido_integrado_item_models import PedidoIntegradoItem

class EstoqueReservaService:
    """
    Serviço central de reserva de estoque.
    Trabalha por SKU.
    """

    @staticmethod
    def _skus_produto(produto: Produto) -> list[str]:
        skus = []
        for valor in (produto.codigo, produto.codigo_barras):
            texto = (valor or "").strip()
            if texto and texto not in skus:
                skus.append(texto)
        return skus

    @staticmethod
    def _quantidade_reservada(db: Session, tenant_id, skus: list[str]):
        if not skus:
            return 0

        return db.query(
            func.coalesce(func.sum(PedidoIntegradoItem.quantidade), 0)
        ).filter(
            PedidoIntegradoItem.tenant_id == tenant_id,
            PedidoIntegradoItem.sku.in_(skus),
            PedidoIntegradoItem.liberado_em.is_(None),
            PedidoIntegradoItem.vendido_em.is_(None)
        ).scalar()

    @staticmethod
    def reservar(db: Session, item: PedidoIntegradoItem):
        produto = db.query(Produto).filter(
            Produto.tenant_id == item.tenant_id,
            or_(Produto.codigo == item.sku, Produto.codigo_barras == item.sku)
        ).first()

        if not produto:
            raise ValueError(f"Produto com SKU {item.sku} não encontrado")

        reservado = EstoqueReservaService._quantidade_reservada(
            db,
            item.tenant_id,
            EstoqueReservaService._skus_produto(produto),
        )
        disponivel = produto.estoque_atual - reservado

        if disponivel < item.quantidade:
            import logging
            logging.getLogger(__name__).warning(
                f"[RESERVA] Estoque insuficiente para SKU {item.sku}. "
                f"Disponível: {disponivel}, solicitado: {item.quantidade}. "
                f"Item registrado mesmo assim."
            )
            return False  # reserva sem cobertura, mas item é salvo

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
