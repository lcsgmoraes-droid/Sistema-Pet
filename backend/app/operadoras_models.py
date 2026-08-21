"""
Models para Operadoras de Cartão
Gerenciamento de operadoras (Stone, Cielo, Rede, Getnet, Sumup, etc)
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Numeric,
    Text,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from datetime import datetime
from app.base_models import BaseTenantModel
from app.utils.serialization import safe_decimal_to_float, safe_datetime_to_iso


class OperadoraCartao(BaseTenantModel):
    """Operadoras de Cartão (Stone, Cielo, Rede, Getnet, Sumup, etc)

    Responsável por:
    - Gerenciar múltiplas operadoras por tenant
    - Controlar parcelamento máximo por operadora
    - Taxas específicas por operadora e tipo de transação
    - Integração via API quando disponível
    - Prevenir conflitos de NSU entre diferentes operadoras
    """

    __tablename__ = "operadoras_cartao"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)

    # Identificação
    nome = Column(
        String(100), nullable=False
    )  # Stone, Cielo, Rede, Getnet, Sumup, Legacy (Histórico)
    codigo = Column(String(50), index=True)  # STONE, CIELO, REDE, GETNET, SUMUP, LEGACY

    # Configurações de Parcelamento
    max_parcelas = Column(
        Integer, default=12, nullable=False
    )  # Máximo de parcelas permitidas

    # Configurações Gerais
    padrao = Column(
        Boolean, default=False, nullable=False, index=True
    )  # Operadora padrão do tenant
    ativo = Column(Boolean, default=True, nullable=False, index=True)
    bandeira_padrao = Column(String(30), nullable=True)

    # Taxas (percentuais)
    taxa_debito = Column(Numeric(5, 2), nullable=True)  # Ex: 2.50 para 2.5%
    taxa_credito_vista = Column(Numeric(5, 2), nullable=True)  # Ex: 3.00 para 3%
    taxa_credito_parcelado = Column(Numeric(5, 2), nullable=True)  # Ex: 4.50 para 4.5%

    # Integração API
    api_enabled = Column(Boolean, default=False, nullable=False)
    api_endpoint = Column(String(255), nullable=True)
    api_token_encrypted = Column(Text, nullable=True)  # Token criptografado

    # UI (Interface)
    cor = Column(String(7), nullable=True)  # Cor hex para exibição (#00A868 para Stone)
    icone = Column(String(50), nullable=True)  # Nome do ícone Lucide

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    # TEMPORARIAMENTE DESABILITADO - modelos não têm back_populates correspondente
    # formas_pagamento = relationship("FormaPagamento", back_populates="operadora_cartao")
    # venda_pagamentos = relationship("VendaPagamento", back_populates="operadora_cartao")

    def to_dict(self):
        """Serializa modelo para dict"""
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "nome": self.nome,
            "codigo": self.codigo,
            "max_parcelas": self.max_parcelas,
            "padrao": self.padrao,
            "ativo": self.ativo,
            "bandeira_padrao": self.bandeira_padrao,
            "taxa_debito": safe_decimal_to_float(self.taxa_debito),
            "taxa_credito_vista": safe_decimal_to_float(self.taxa_credito_vista),
            "taxa_credito_parcelado": safe_decimal_to_float(
                self.taxa_credito_parcelado
            ),
            "api_enabled": self.api_enabled,
            "api_endpoint": self.api_endpoint,
            "cor": self.cor,
            "icone": self.icone,
            "user_id": self.user_id,
            "created_at": safe_datetime_to_iso(self.created_at),
            "updated_at": safe_datetime_to_iso(self.updated_at),
        }


class OperadoraCartaoTaxa(BaseTenantModel):
    """Regra de taxa por operadora, bandeira, modalidade e parcelas."""

    __tablename__ = "operadoras_cartao_taxas"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "operadora_id",
            "bandeira",
            "modalidade",
            "parcelas",
            name="uq_operadora_taxa_contexto",
        ),
        CheckConstraint(
            "parcelas >= 1 AND parcelas <= 24", name="ck_operadora_taxa_parcelas"
        ),
        CheckConstraint(
            "taxa_percentual >= 0 AND taxa_percentual <= 100",
            name="ck_operadora_taxa_percentual",
        ),
        {"extend_existing": True},
    )

    operadora_id = Column(
        Integer,
        ForeignKey("operadoras_cartao.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bandeira = Column(String(30), nullable=False, index=True)
    modalidade = Column(String(20), nullable=False, index=True)
    parcelas = Column(Integer, nullable=False)
    taxa_percentual = Column(Numeric(7, 4), nullable=False, default=0)
    taxa_fixa = Column(Numeric(10, 2), nullable=False, default=0)
    prazo_recebimento_dias = Column(Integer, nullable=False, default=0)
    ativo = Column(Boolean, nullable=False, default=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "operadora_id": self.operadora_id,
            "bandeira": self.bandeira,
            "modalidade": self.modalidade,
            "parcelas": self.parcelas,
            "taxa_percentual": safe_decimal_to_float(self.taxa_percentual) or 0,
            "taxa_fixa": safe_decimal_to_float(self.taxa_fixa) or 0,
            "prazo_recebimento_dias": self.prazo_recebimento_dias or 0,
            "ativo": self.ativo,
            "created_at": safe_datetime_to_iso(self.created_at),
            "updated_at": safe_datetime_to_iso(self.updated_at),
        }
