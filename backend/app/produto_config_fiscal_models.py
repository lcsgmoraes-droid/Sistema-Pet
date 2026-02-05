from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .db import Base


class ProdutoConfigFiscal(Base):
    __tablename__ = "produto_config_fiscal"

    id = Column(Integer, primary_key=True)

    # Multi-tenant
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Vínculo com produto
    produto_id = Column(Integer, ForeignKey("produto.id"), nullable=False, unique=True)

    # Herança
    herdado_da_empresa = Column(Boolean, nullable=False, default=True)

    # Identificação fiscal
    ncm = Column(String(10))
    cest = Column(String(10))
    origem_mercadoria = Column(String(1))  # 0 nacional, 1 estrangeira etc.

    # ICMS
    cst_icms = Column(String(3))
    icms_aliquota = Column(Numeric(5, 2))
    icms_st = Column(Boolean)

    # CFOP
    cfop_venda = Column(String(4))
    cfop_compra = Column(String(4))

    # PIS / COFINS
    pis_cst = Column(String(3))
    pis_aliquota = Column(Numeric(5, 2))
    cofins_cst = Column(String(3))
    cofins_aliquota = Column(Numeric(5, 2))

    # Campo livre para explicações / sugestões
    observacao_fiscal = Column(Text)

    # Controle
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
