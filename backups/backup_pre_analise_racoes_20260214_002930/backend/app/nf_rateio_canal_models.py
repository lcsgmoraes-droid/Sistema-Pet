
from sqlalchemy import Column, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import BaseTenantModel

class NotaFiscalRateioCanal(BaseTenantModel):
    """
    Rateio analítico de uma Nota Fiscal por canal de venda.
    Percentual total deve somar 100%.
    """
    __tablename__ = "nota_fiscal_rateio_canal"

    nota_fiscal_id = Column(String, nullable=False)
    canal = Column(String(50), nullable=False)
    percentual = Column(Numeric(5, 2), nullable=False)

    observacao = Column(String(255), nullable=True)
