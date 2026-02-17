
from sqlalchemy import Column, String, JSON
from app.database.base import BaseTenantModel

class ConfiguracaoSistema(BaseTenantModel):
    """
    Configuração central do sistema.
    Cada registro representa um BLOCO de configuração.
    Ex:
    - fiscal
    - dre
    - bling
    - ia
    - whatsapp
    """
    __tablename__ = "configuracoes_sistema"

    chave = Column(String(50), nullable=False, index=True)
    valores = Column(JSON, nullable=False)

    descricao = Column(String(255), nullable=True)
