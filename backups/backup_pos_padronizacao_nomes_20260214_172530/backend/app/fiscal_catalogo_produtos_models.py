from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime
)
from sqlalchemy.sql import func
from .db import Base


class FiscalCatalogoProdutos(Base):
    __tablename__ = "fiscal_catalogo_produtos"

    id = Column(Integer, primary_key=True)

    # Matching
    palavras_chave = Column(Text, nullable=False)
    categoria_fiscal = Column(String(100), nullable=False)

    # Fiscal sugerido
    ncm = Column(String(10))
    cest = Column(String(10))
    cst_icms = Column(String(3))
    icms_st = Column(Boolean)

    pis_cst = Column(String(3))
    cofins_cst = Column(String(3))

    # Texto explicativo para UI
    observacao = Column(Text)

    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
