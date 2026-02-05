
from sqlalchemy import Column, String, Integer, Numeric
from app.database.base import BaseTenantModel

class NotaFiscalItemRateioCanal(BaseTenantModel):
    """
    Rateio de ITEM de Nota Fiscal por canal.
    A fonte da verdade é a QUANTIDADE.
    Valor e percentual são calculados no backend.
    """
    __tablename__ = "nota_fiscal_item_rateio_canal"

    nota_fiscal_item_id = Column(String, nullable=False)
    canal = Column(String(50), nullable=False)

    quantidade = Column(Integer, nullable=False)

    valor_calculado = Column(Numeric(12, 2), nullable=False)
    percentual_calculado = Column(Numeric(5, 2), nullable=False)

    observacao = Column(String(255), nullable=True)
