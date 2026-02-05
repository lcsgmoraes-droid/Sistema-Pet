"""
Modelo de controle de processamento mensal para provisões e fechamentos.
Garante que processos mensais sejam executados apenas uma vez por tenant/período.
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db import Base


class ControleProcessamentoMensal(Base):
    """
    Controla a execução de processamentos mensais recorrentes (provisões, fechamentos, etc).
    
    Garante idempotência: cada tipo de processamento roda apenas 1x por tenant/mês/ano.
    """
    __tablename__ = "controle_processamento_mensal"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(String, nullable=False, index=True)
    
    # Tipo de processamento: PROVISAO_TRABALHISTA, PROVISAO_COMISSOES, FECHAMENTO_MENSAL, etc.
    tipo = Column(String(50), nullable=False, index=True)
    
    # Período processado
    mes = Column(Integer, nullable=False)  # 1-12
    ano = Column(Integer, nullable=False)  # 2024, 2025, etc.
    
    # Data/hora do processamento
    processado_em = Column(DateTime, server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<ControleProcessamento {self.tipo} - {self.tenant_id} - {self.mes}/{self.ano}>"
