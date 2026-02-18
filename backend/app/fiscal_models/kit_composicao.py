from sqlalchemy import (
    Column, Integer, Numeric, ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.sql import func
from app.db.base_class import Base


class KitComposicao(Base):
    __tablename__ = "kit_composicao"

    id = Column(Integer, primary_key=True)

    tenant_id = Column(Integer, nullable=False, index=True)

    # O kit pode ser um produto ou uma variação
    # TEMPORÁRIO: FKs desabilitadas - tabelas não existem ainda
    produto_kit_id = Column(Integer, nullable=False)  # ForeignKey("produto.id")

    # Item que compõe o kit (produto ou variação)
    produto_item_id = Column(Integer, nullable=False)  # ForeignKey("produto.id")
    variacao_item_id = Column(Integer, nullable=True)  # ForeignKey("produto_variacao.id")

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
