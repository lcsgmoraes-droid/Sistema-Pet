from app.base_models import BaseTenantModel
"""
ABA 6: Chat IA - Modelos de Banco de Dados

Tabelas:
- Conversas: Histórico de conversas do usuário
- Mensagens: Mensagens individuais (usuário e IA)
- ContextoChat: Dados de contexto usados na conversa
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class Conversa(BaseTenantModel):
    """Conversa do usuário com a IA"""
    __tablename__ = "conversas_ia"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=False, index=True)  # FK removida temporariamente
    titulo = Column(String(200), nullable=True)  # Gerado automaticamente pela primeira mensagem
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finalizada = Column(Boolean, default=False)
    
    # Relacionamentos
    mensagens = relationship("MensagemChat", back_populates="conversa", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversa {self.id}: {self.titulo or 'Nova conversa'}>"


class MensagemChat(BaseTenantModel):
    """Mensagem individual (usuário ou IA)"""
    __tablename__ = "mensagens_chat"

    id = Column(Integer, primary_key=True, index=True)
    conversa_id = Column(Integer, ForeignKey("conversas_ia.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)  # 'usuario' ou 'assistente'
    conteudo = Column(Text, nullable=False)
    tokens_usados = Column(Integer, default=0)  # Para tracking de custos
    modelo_usado = Column(String(50), nullable=True)  # ex: 'gpt-4', 'gpt-3.5-turbo'
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Contexto usado na resposta (JSON)
    contexto_usado = Column(JSON, nullable=True)  # Dados financeiros que a IA consultou
    
    # Relacionamentos
    conversa = relationship("Conversa", back_populates="mensagens")

    def __repr__(self):
        return f"<Mensagem {self.id} ({self.tipo}): {self.conteudo[:50]}...>"


class ContextoFinanceiro(BaseTenantModel):
    """Cache de contexto financeiro para acelerar respostas"""
    __tablename__ = "contexto_financeiro_chat"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=False, index=True)  # FK removida temporariamente
    tipo_contexto = Column(String(50), nullable=False)  # 'indices', 'projecoes', 'alertas', 'transacoes'
    dados = Column(JSON, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    valido_ate = Column(DateTime, nullable=False)  # Cache expira após X horas

    def __repr__(self):
        return f"<ContextoFinanceiro {self.id} ({self.tipo_contexto})>"
