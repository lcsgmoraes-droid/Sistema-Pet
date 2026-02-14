from sqlalchemy import Column, Integer, String, Numeric, Boolean, Text, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base


class FiscalEstadoPadrao(Base):
    __tablename__ = "fiscal_estado_padrao"

    id = Column(Integer, primary_key=True)
    uf = Column(String(2), nullable=False, unique=True)

    icms_aliquota_interna = Column(Numeric(5, 2), nullable=False)
    icms_aliquota_interestadual = Column(Numeric(5, 2), nullable=False)

    aplica_difal = Column(Boolean, nullable=False)

    cfop_venda_interna = Column(String(4), nullable=False)
    cfop_venda_interestadual = Column(String(4), nullable=False)
    cfop_compra = Column(String(4), nullable=False)

    regime_mais_comum = Column(String(50))
    observacoes_fiscais = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
