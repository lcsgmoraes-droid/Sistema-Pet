"""
Modelo de Cargo para RH
Define salários base e percentuais de encargos trabalhistas
"""

from sqlalchemy import Column, String, Numeric, Boolean, Text

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
    regime_remuneracao = Column(String(30), nullable=False, default="clt", server_default="clt")
    
    # Encargos trabalhistas
    gera_encargos = Column(Boolean, nullable=False, default=True, server_default="1")
    inss_patronal_percentual = Column(Numeric, nullable=False, default=20)
    fgts_percentual = Column(Numeric, nullable=False, default=8)
    inss_funcionario_percentual = Column(Numeric, nullable=False, default=0, server_default="0")
    inss_funcionario_valor = Column(Numeric, nullable=False, default=0, server_default="0")
    desconto_transporte_valor = Column(Numeric, nullable=False, default=0, server_default="0")
    outros_descontos_valor = Column(Numeric, nullable=False, default=0, server_default="0")
    
    # Provisões automáticas
    gera_ferias = Column(Boolean, nullable=False, default=True)
    gera_decimo_terceiro = Column(Boolean, nullable=False, default=True)
    
    ativo = Column(Boolean, nullable=False, default=True)
    
    # created_at e updated_at vêm do BaseTenantModel
