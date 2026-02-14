# -*- coding: utf-8 -*-
"""
Models para Opções de Classificação de Rações
Tabelas auxiliares para cadastros dinâmicos
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .db import Base


class LinhaRacao(Base):
    """Linhas de Ração: Premium, Super Premium, Premium Special, Standard"""
    __tablename__ = "linhas_racao"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(100), nullable=False, index=True)
    descricao = Column(String(255), nullable=True)
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)


class PorteAnimal(Base):
    """Portes: Pequeno, Médio, Médio/Grande, Grande, Gigante, Todos"""
    __tablename__ = "portes_animal"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(100), nullable=False, index=True)
    descricao = Column(String(255), nullable=True)
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)


class FasePublico(Base):
    """Fases/Público: Filhote, Adulto, Senior, Gestante"""
    __tablename__ = "fases_publico"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(100), nullable=False, index=True)
    descricao = Column(String(255), nullable=True)
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)


class TipoTratamento(Base):
    """Tipos de Tratamento: Obesidade, Renal, Light, Hipoalergênico"""
    __tablename__ = "tipos_tratamento"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(100), nullable=False, index=True)
    descricao = Column(String(255), nullable=True)
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)


class SaborProteina(Base):
    """Sabores/Proteínas: Frango, Carne, Peixe, Cordeiro"""
    __tablename__ = "sabores_proteina"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(100), nullable=False, index=True)
    descricao = Column(String(255), nullable=True)
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)


class ApresentacaoPeso(Base):
    """Apresentações (Peso): 1kg, 3kg, 10.1kg, 15kg, 20kg"""
    __tablename__ = "apresentacoes_peso"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    peso_kg = Column(Float, nullable=False, index=True)
    descricao = Column(String(100), nullable=True)  # Ex: "15kg", "10.1kg"
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
