from app.base_models import BaseTenantModel
"""
Models para Formas de Pagamento e Taxas por Parcela
Utilizado para análise de vendas no PDV
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base


class FormaPagamentoTaxa(BaseTenantModel):
    """Taxas específicas por número de parcelas"""
    __tablename__ = "formas_pagamento_taxas"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    forma_pagamento_id = Column(Integer, ForeignKey('formas_pagamento.id'), nullable=False)
    parcelas = Column(Integer, nullable=False)  # 1, 2, 3, etc
    taxa_percentual = Column(Numeric(5, 2), nullable=False, default=0)  # Ex: 2.5, 3.8, 4.5
    descricao = Column(String(100))  # Ex: "À vista", "2x sem juros", "3x sem juros"
    
    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    forma_pagamento = relationship("FormaPagamento", foreign_keys=[forma_pagamento_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'forma_pagamento_id': self.forma_pagamento_id,
            'parcelas': self.parcelas,
            'taxa_percentual': float(self.taxa_percentual) if self.taxa_percentual else 0,
            'descricao': self.descricao
        }


class ConfiguracaoImposto(BaseTenantModel):
    """Configuração de impostos para cálculo de margem"""
    __tablename__ = "configuracao_impostos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)  # Ex: "Simples Nacional", "Lucro Presumido"
    percentual = Column(Numeric(5, 2), nullable=False, default=0)  # Ex: 5.0 para 5%
    ativo = Column(Boolean, default=True)
    padrao = Column(Boolean, default=False)  # Se é a configuração padrão
    descricao = Column(Text)
    
    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'percentual': float(self.percentual) if self.percentual else 0,
            'ativo': self.ativo,
            'padrao': self.padrao,
            'descricao': self.descricao
        }


# ====================
# FORMAS PAGAMENTO COMISSÕES (ÓRFÃ)
# Schema baseado em RELATORIO_SCHEMA_TABELAS_ORFAS.md - Fase 5.4
# ====================

class FormaPagamentoComissao(Base):
    """
    Formas de pagamento disponíveis para comissões.
    Tabela compartilhada entre tenants (sem tenant_id).
    
    ⚠️ NOTA: Esta tabela NÃO possui tenant_id (configuração global)
    """
    __tablename__ = "formas_pagamento_comissoes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, unique=True)
    descricao = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
