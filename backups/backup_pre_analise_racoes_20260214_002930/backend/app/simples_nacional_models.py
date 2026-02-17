"""
Model para histórico mensal do Simples Nacional
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.db import Base


class SimplesNacionalMensal(Base):
    """
    Histórico mensal do Simples Nacional.
    Registra faturamento, impostos e alíquota efetiva de cada mês.
    """
    
    __tablename__ = "simples_nacional_mensal"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    
    # Competência
    mes = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    
    # Faturamento
    faturamento_sistema = Column(
        Numeric(14, 2),
        nullable=True,
        comment="Apurado via NF do sistema"
    )
    faturamento_contador = Column(
        Numeric(14, 2),
        nullable=True,
        comment="Informado manualmente pelo contador (prioritário)"
    )
    
    # Impostos
    imposto_estimado = Column(
        Numeric(14, 2),
        nullable=True,
        comment="Provisões acumuladas no mês"
    )
    imposto_real = Column(
        Numeric(14, 2),
        nullable=True,
        comment="Valor real do DAS pago"
    )
    
    # Alíquotas
    aliquota_efetiva = Column(
        Numeric(6, 4),
        nullable=True,
        comment="Alíquota real calculada (imposto/faturamento)"
    )
    aliquota_sugerida = Column(
        Numeric(6, 4),
        nullable=True,
        comment="Sugestão para próximo mês"
    )
    
    # Controle
    fechado = Column(Boolean, default=False, server_default='false')
    observacoes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'ano', 'mes', name='uq_simples_mensal_competencia'),
    )
    
    def __repr__(self):
        return f"<SimplesNacionalMensal {self.mes}/{self.ano} - Alíquota: {self.aliquota_efetiva}%>"
    
    @property
    def faturamento_final(self):
        """Retorna o faturamento a ser considerado (contador tem prioridade)"""
        return self.faturamento_contador or self.faturamento_sistema
    
    @property
    def diferenca_imposto(self):
        """Diferença entre imposto estimado e real"""
        if self.imposto_estimado and self.imposto_real:
            return self.imposto_real - self.imposto_estimado
        return None
