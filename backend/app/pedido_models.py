from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime

from app.db import Base
from app.domain.policies.pedido_policy import PedidoPolicy
from app.domain.value_objects.money import Money


class Pedido(Base):
    """
    Aggregate root do Ecommerce.
    Pedido nasce antes do evento.
    """

    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)

    pedido_id = Column(String, unique=True, index=True)  # ID público
    cliente_id = Column(Integer, nullable=False)
    tenant_id = Column(String(36), nullable=False, index=True)

    total = Column(Float, nullable=False)

    origem = Column(String, nullable=False)  # web | app | marketplace

    status = Column(String, default="criado")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # =====================================
    # DDD Aggregate Methods (SAFE VERSION)
    # =====================================

    def adicionar_item(self, db, *, produto_id, nome, quantidade, preco_unitario, tenant_id):
        """
        Método de domínio SAFE.
        Não altera fluxo atual — apenas encapsula criação.
        """

        PedidoPolicy.validar_nome(nome)
        PedidoPolicy.validar_quantidade(quantidade)
        PedidoPolicy.validar_preco(preco_unitario)

        # proteção contra duplicação acidental
        existente = next(
            (
                i for i in db.new
                if isinstance(i, PedidoItem)
                and i.pedido_id == self.pedido_id
                and i.produto_id == produto_id
                and i.nome == nome
            ),
            None,
        )

        if existente:
            existente.quantidade += quantidade
            existente.subtotal = (Money(existente.preco_unitario) * existente.quantidade).value
            return existente

        subtotal = (Money(preco_unitario) * quantidade).value

        item = PedidoItem(
            pedido_id=self.pedido_id,
            produto_id=produto_id,
            nome=nome,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            subtotal=subtotal,
            tenant_id=tenant_id,
        )

        db.add(item)
        return item

    def recalcular_total(self, db):
        """
        Fonte única da verdade.
        FIXED VERSION — força dirty tracking.
        """
        itens_pendentes = [
            obj for obj in db.new
            if isinstance(obj, PedidoItem) and obj.pedido_id == self.pedido_id
        ]

        if itens_pendentes:
            items = itens_pendentes
        else:
            items = db.query(PedidoItem).filter(
                PedidoItem.pedido_id == self.pedido_id
            ).all()

        total_money = Money(0)

        for i in items:
            total_money = total_money + Money(i.subtotal)

        self.total = total_money.value
        flag_modified(self, "total")

        return self.total


# ===== PedidoItem (Checkout Engine v1) =====

class PedidoItem(Base):
    __tablename__ = "pedido_itens"

    id = Column(Integer, primary_key=True, index=True)

    pedido_id = Column(String, ForeignKey("pedidos.pedido_id"), index=True, nullable=False)

    produto_id = Column(Integer, nullable=False)
    nome = Column(String, nullable=False)

    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario = Column(Float, nullable=False)

    subtotal = Column(Float, nullable=False)

    tenant_id = Column(String(36), nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)