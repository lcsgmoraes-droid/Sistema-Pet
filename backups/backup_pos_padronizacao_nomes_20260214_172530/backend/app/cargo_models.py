"""
Modelo de Cargo para RH
Define salários base e percentuais de encargos trabalhistas
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db import Base
from app.base_models import BaseTenantModel


class Cargo(BaseTenantModel):
    """
    Cargo define salário base e encargos trabalhistas.
    Funcionários (clientes com tipo_cadastro='funcionario') apontam para um cargo.
    
    Schema baseado em RELATORIO_SCHEMA_TABELAS_ORFAS.md - Fase 5.4
    """
    __tablename__ = "cargos"
    __table_args__ = {'extend_existing': True}
    
    # id e tenant_id vêm do BaseTenantModel
    
    nome = Column(String(100), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    salario_base = Column(Numeric, nullable=False)
    
    # Encargos trabalhistas
    inss_patronal_percentual = Column(Numeric, nullable=False, default=20)
    fgts_percentual = Column(Numeric, nullable=False, default=8)
    
    # Provisões automáticas
    gera_ferias = Column(Boolean, nullable=False, default=True)
    gera_decimo_terceiro = Column(Boolean, nullable=False, default=True)
    
    ativo = Column(Boolean, nullable=False, default=True)
    
    # created_at e updated_at vêm do BaseTenantModel
