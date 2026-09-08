"""Identidades comerciais preservadas e auditoria de consolidacao de produtos."""

from sqlalchemy import Column, ForeignKey, Integer, JSON, String, Text, UniqueConstraint

from app.base_models import BaseTenantModel


class ProdutoSkuAlias(BaseTenantModel):
    __tablename__ = "produto_sku_aliases"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "sku_normalizado", name="uq_produto_sku_alias_tenant_sku"
        ),
    )

    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)
    sku = Column(String(100), nullable=False)
    sku_normalizado = Column(String(200), nullable=False)
    origem = Column(String(40), nullable=False)
    motivo = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)


class ProdutoFusaoLog(BaseTenantModel):
    __tablename__ = "produto_fusao_logs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "duplicado_id", name="uq_produto_fusao_tenant_duplicado"
        ),
    )

    # Intentionally not product FKs: generic history transfer must never rewrite an audit.
    principal_id = Column(Integer, nullable=False)
    duplicado_id = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    estrategia_estoque = Column(String(30), nullable=False)
    motivo = Column(Text, nullable=False)
    antes = Column(JSON, nullable=False)
    depois = Column(JSON, nullable=False)
    referencias = Column(JSON, nullable=False)
