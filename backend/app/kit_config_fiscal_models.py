from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .db import Base


class KitConfigFiscal(Base):
    __tablename__ = "kit_config_fiscal"

    id = Column(Integer, primary_key=True)

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Kit vinculado a produto
    produto_kit_id = Column(Integer, ForeignKey("produtos.id"), nullable=True)

    # Controle de herança
    herdado_da_empresa = Column(Boolean, nullable=False, default=True)

    # Identificação fiscal
    ncm = Column(String(10))
    cest = Column(String(10))
    origem_mercadoria = Column(String(1))

    # ICMS
    cst_icms = Column(String(3))
    icms_aliquota = Column(Numeric(5, 2))
    icms_st = Column(Boolean)

    # CFOP (único campo na tabela)
    cfop = Column(String(4))

    # PIS / COFINS
    pis_aliquota = Column(Numeric(5, 2))
    cofins_aliquota = Column(Numeric(5, 2))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
