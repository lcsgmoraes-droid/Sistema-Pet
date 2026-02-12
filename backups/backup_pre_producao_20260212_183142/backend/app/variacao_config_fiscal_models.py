from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.sql import func
from .db import Base


class VariacaoConfigFiscal(Base):
    __tablename__ = "variacao_config_fiscal"

    id = Column(Integer, primary_key=True)

    # Multi-tenant
    tenant_id = Column(Integer, nullable=False, index=True)

    # Vínculo com variação
    variacao_id = Column(Integer, ForeignKey("produto_variacao.id"), nullable=False, unique=True)

    # Herança
    produto_config_fiscal_id = Column(
        Integer,
        ForeignKey("produto_config_fiscal.id"),
        nullable=True
    )

    herdado_do_produto = Column(Boolean, nullable=False, default=True)

    # Identificação fiscal
    ncm = Column(String(10))
    cest = Column(String(10))
    origem_mercadoria = Column(String(1))

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

    # Observações
    observacao_fiscal = Column(Text)

    configuracao_sugerida = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
