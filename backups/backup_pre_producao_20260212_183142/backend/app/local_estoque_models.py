
from sqlalchemy import Column, String, Boolean
from app.database.base import BaseTenantModel

class LocalEstoque(BaseTenantModel):
    """
    Representa um LOCAL REAL de estoque.
    Ex:
    - Loja Física
    - Full Mercado Livre
    - Full Shopee
    """
    __tablename__ = "locais_estoque"

    nome = Column(String(100), nullable=False)
    tipo = Column(String(30), nullable=False)  
    # interno | full

    origem_padrao = Column(Boolean, default=False)
    ativo = Column(Boolean, default=True)
