from app.base_models import BaseTenantModel
"""
Models para o Sistema de Controle de Caixa
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base
from app.utils.serialization import safe_decimal_to_float, safe_datetime_to_iso


class Caixa(BaseTenantModel):
    """Model para controle de caixas"""
    __tablename__ = 'caixas'
    
    id = Column(Integer, primary_key=True, index=True)
    numero_caixa = Column(Integer, nullable=False)
    usuario_id = Column(Integer, nullable=False)
    usuario_nome = Column(String(200), nullable=False)
    data_abertura = Column(DateTime, default=datetime.now, nullable=False)
    data_fechamento = Column(DateTime)
    valor_abertura = Column(Float, default=0.0, nullable=False)
    valor_esperado = Column(Float)
    valor_informado = Column(Float)
    diferenca = Column(Float)
    status = Column(String(20), default='aberto', nullable=False)  # aberto, fechado
    conta_origem_id = Column(Integer)
    conta_origem_nome = Column(String(200))
    observacoes_abertura = Column(Text)
    observacoes_fechamento = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relacionamentos
    movimentacoes = relationship("MovimentacaoCaixa", back_populates="caixa", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero_caixa': self.numero_caixa,
            'usuario_id': self.usuario_id,
            'usuario_nome': self.usuario_nome,
            'data_abertura': safe_datetime_to_iso(self.data_abertura),
            'data_fechamento': safe_datetime_to_iso(self.data_fechamento),
            'valor_abertura': safe_decimal_to_float(self.valor_abertura) or 0.0,
            'valor_esperado': safe_decimal_to_float(self.valor_esperado),
            'valor_informado': safe_decimal_to_float(self.valor_informado),
            'diferenca': safe_decimal_to_float(self.diferenca),
            'status': self.status,
            'conta_origem_id': self.conta_origem_id,
            'conta_origem_nome': self.conta_origem_nome,
            'observacoes_abertura': self.observacoes_abertura,
            'observacoes_fechamento': self.observacoes_fechamento,
            'created_at': safe_datetime_to_iso(self.created_at),
            'updated_at': safe_datetime_to_iso(self.updated_at),
            'movimentacoes': [m.to_dict() for m in self.movimentacoes] if hasattr(self, 'movimentacoes') else []
        }


class MovimentacaoCaixa(BaseTenantModel):
    """Model para movimentações de caixa"""
    __tablename__ = 'movimentacoes_caixa'
    
    id = Column(Integer, primary_key=True, index=True)
    caixa_id = Column(Integer, ForeignKey('caixas.id', ondelete='CASCADE'), nullable=False)
    tipo = Column(String(50), nullable=False)  # venda, suprimento, sangria, despesa, transferencia, devolucao
    valor = Column(Float, nullable=False)
    forma_pagamento = Column(String(50))
    descricao = Column(Text)
    categoria = Column(String(100))
    conta_origem_id = Column(Integer)
    conta_origem_nome = Column(String(200))
    conta_destino_id = Column(Integer)
    conta_destino_nome = Column(String(200))
    fornecedor_id = Column(Integer)
    fornecedor_nome = Column(String(200))
    documento = Column(String(100))
    venda_id = Column(Integer, ForeignKey('vendas.id'))
    usuario_id = Column(Integer, nullable=False)
    usuario_nome = Column(String(200), nullable=False)
    data_movimento = Column(DateTime, default=datetime.now, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relacionamentos
    caixa = relationship("Caixa", back_populates="movimentacoes")
    venda = relationship("Venda", foreign_keys=[venda_id], backref="movimentacoes_caixa")
    
    def to_dict(self):
        return {
            'id': self.id,
            'caixa_id': self.caixa_id,
            'tipo': self.tipo,
            'valor': safe_decimal_to_float(self.valor) or 0.0,
            'forma_pagamento': self.forma_pagamento,
            'descricao': self.descricao,
            'categoria': self.categoria,
            'conta_origem_id': self.conta_origem_id,
            'conta_origem_nome': self.conta_origem_nome,
            'conta_destino_id': self.conta_destino_id,
            'conta_destino_nome': self.conta_destino_nome,
            'fornecedor_id': self.fornecedor_id,
            'fornecedor_nome': self.fornecedor_nome,
            'documento': self.documento,
            'venda_id': self.venda_id,
            'venda_numero': self.venda.numero_venda if self.venda else None,
            'usuario_id': self.usuario_id,
            'usuario_nome': self.usuario_nome,
            'data_movimento': safe_datetime_to_iso(self.data_movimento),
            'created_at': safe_datetime_to_iso(self.created_at)
        }
