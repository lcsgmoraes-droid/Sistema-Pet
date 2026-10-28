"""Vinculo explicito e auditavel de pedido iFood com a venda ERP comprovada."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)

from app.base_models import BaseTenantModel


class IfoodFinancialSaleLink(BaseTenantModel):
    __tablename__ = "ifood_financial_sale_links"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "merchant_id",
            "mode",
            "order_id",
            name="uq_ifood_fin_sale_link_order",
        ),
        # A venda nao pode provar o custo de dois pedidos/lojas distintos.
        UniqueConstraint(
            "tenant_id",
            "mode",
            "venda_id",
            name="uq_ifood_fin_sale_link_sale",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "venda_id"],
            ["vendas.tenant_id", "vendas.id"],
            name="fk_ifood_fin_sale_link_tenant_sale",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "source = 'explicit_confirmation'", name="ck_ifood_fin_link_source"
        ),
        CheckConstraint("mode = 'homologation'", name="ck_ifood_fin_link_mode"),
        CheckConstraint("actor_id > 0", name="ck_ifood_fin_link_actor"),
    )

    merchant_id = Column(String(36), nullable=False)
    mode = Column(String(20), nullable=False)
    order_id = Column(String(80), nullable=False)
    venda_id = Column(Integer, nullable=False)
    source = Column(String(40), nullable=False)
    source_note = Column(String(1000), nullable=False)
    actor_id = Column(Integer, nullable=False)
    # Apenas IDs, quantidades e hashes; nenhum cadastro/PII ou custo atual.
    item_manifest = Column(JSON, nullable=False)
