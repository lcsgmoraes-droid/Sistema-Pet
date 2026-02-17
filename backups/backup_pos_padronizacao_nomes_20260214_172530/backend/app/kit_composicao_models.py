from sqlalchemy import (
    Column, Integer, Numeric, ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.sql import func
from .db import Base


class KitComposicao(Base):
    __tablename__ = "kit_composicao"

    id = Column(Integer, primary_key=True)

    tenant_id = Column(Integer, nullable=False, index=True)

    # O kit pode ser um produto ou uma variação
    produto_kit_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)

    # Item que compõe o kit (produto ou variação)
    produto_item_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    variacao_item_id = Column(Integer, ForeignKey("produtos.id"), nullable=True)

    quantidade = Column(Numeric(10, 3), nullable=False, default=1)

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "produto_kit_id",
            "produto_item_id",
            "variacao_item_id",
            name="uq_kit_composicao_item"
        ),
    )
