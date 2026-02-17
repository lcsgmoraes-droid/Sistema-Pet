
from sqlalchemy import Column, String, Boolean, DateTime
from app.database.base import BaseTenantModel
from datetime import datetime

class IntegracaoBling(BaseTenantModel):
    """
    Controle da integração com o Bling.
    Um registro por tenant.
    """
    __tablename__ = "integracao_bling"

    api_token = Column(String(255), nullable=False)

    ativo = Column(Boolean, default=True)

    ultimo_evento = Column(String(100), nullable=True)
    ultimo_evento_em = Column(DateTime, nullable=True)

    ultima_sincronizacao = Column(DateTime, nullable=True)

    status = Column(String(30), default="inicial")  
    # inicial | ativo | erro | pausado

    erro_mensagem = Column(String(255), nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow)
