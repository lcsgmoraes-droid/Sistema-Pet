"""
Modelo: Operadoras de Cartão (Cadastro do Usuário)

SEPARAÇÃO CLARA:
- adquirentes_templates = TEMPLATES DO SISTEMA (Stone v1.0, Cielo v1.0)
- operadoras_cartao = CADASTRO DO USUÁRIO ("Minha Stone - Loja 1")

Analogia:
- Templates = "tipos de banco" (Banco do Brasil, Itaú)
- Operadoras Cartão = "suas contas" ("BB Conta Corrente 12345")
"""

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Index, Text, DECIMAL
from sqlalchemy.orm import relationship
from app.db import Base
from datetime import datetime


class OperadoraCartao(Base):
    """
    Cadastro das operadoras que o usuário utiliza.
    
    Exemplo:
    - nome: "Stone - Loja Centro"
    - template_id: 1 (Stone v1.0)
    - ativo: True
    
    - nome: "Cielo - Loja Shopping"
    - template_id: 2 (Cielo v1.0)
    - ativo: True
    """
    __tablename__ = 'operadoras_cartao'
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    
    # Identificação
    nome = Column(String(200), nullable=False)  # "Stone - Loja Centro"
    codigo = Column(String(50), nullable=True)
    descricao = Column(Text, nullable=True)     # "Operadora da loja física"
    
    # Taxas de cartão
    taxa_debito = Column(DECIMAL(5, 2), nullable=True)
    taxa_credito_vista = Column(DECIMAL(5, 2), nullable=True)
    taxa_credito_parcelado = Column(DECIMAL(5, 2), nullable=True)
    max_parcelas = Column(Integer, nullable=True)
    
    # Vínculo ao template (se usar conciliação)
    template_id = Column(Integer, ForeignKey('adquirentes_templates.id'), nullable=True)
    template = relationship("AdquirenteTemplate", foreign_keys=[template_id])
    
    # Configurações específicas
    codigo_estabelecimento = Column(String(100), nullable=True)  # Código/EC da loja na operadora
    taxa_mdr_padrao = Column(String(10), nullable=True)           # "2.5%" (informativo)
    dias_recebimento_debito = Column(Integer, nullable=True)      # 1 dia
    dias_recebimento_credito = Column(Integer, nullable=True)     # 30 dias
    
    # Status
    ativo = Column(Boolean, default=True, nullable=False)
    padrao = Column(Boolean, default=False, nullable=False)  # Operadora padrão do tenant
    
    # Auditoria
    criado_em = Column(String(30), default=lambda: datetime.utcnow().isoformat())
    atualizado_em = Column(String(30), default=lambda: datetime.utcnow().isoformat(), onupdate=lambda: datetime.utcnow().isoformat())
    criado_por = Column(Integer, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('ix_operadoras_cartao_tenant_ativo', 'tenant_id', 'ativo'),
        Index('ix_operadoras_cartao_tenant_padrao', 'tenant_id', 'padrao'),
    )
