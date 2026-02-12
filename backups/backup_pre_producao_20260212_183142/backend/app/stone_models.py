"""
Models para integração com Stone
Armazena transações e logs de pagamentos Stone
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
from .db import Base
from .base_models import BaseTenantModel
from app.utils.serialization import safe_decimal_to_float, safe_datetime_to_iso


class StoneTransaction(BaseTenantModel):
    """
    Registro de transações Stone
    Armazena todas as transações PIX e Cartão processadas via Stone
    """
    __tablename__ = "stone_transactions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # IDs de referência
    stone_payment_id = Column(String(100), unique=True, index=True, nullable=False)  # ID retornado pela Stone
    external_id = Column(String(100), unique=True, index=True, nullable=False)  # ID do nosso sistema
    
    # Relacionamento com vendas (opcional)
    venda_id = Column(Integer, ForeignKey('vendas.id'), nullable=True)
    conta_receber_id = Column(Integer, ForeignKey('contas_receber.id'), nullable=True)
    
    # Dados do pagamento
    payment_method = Column(String(20), nullable=False)  # pix, credit_card, debit_card
    amount = Column(Numeric(15, 2), nullable=False)  # Valor em reais
    description = Column(Text)
    installments = Column(Integer, default=1)
    
    # Status da transação
    status = Column(String(30), nullable=False, index=True)  # pending, approved, cancelled, refunded, failed
    stone_status = Column(String(50))  # Status original da Stone (pode ter mais detalhes)
    
    # Dados do cliente
    customer_name = Column(String(200))
    customer_document = Column(String(20))  # CPF/CNPJ
    customer_email = Column(String(200))
    
    # Dados PIX (quando aplicável)
    pix_qr_code = Column(Text)  # QR Code para pagamento PIX
    pix_qr_code_url = Column(String(500))  # URL da imagem do QR Code
    pix_copy_paste = Column(Text)  # Código PIX Copia e Cola
    pix_expiration = Column(DateTime)  # Quando o PIX expira
    
    # Dados do cartão (não armazena dados sensíveis)
    card_brand = Column(String(20))  # visa, mastercard, elo, etc
    card_last_digits = Column(String(4))  # Últimos 4 dígitos
    
    # Taxas e valores líquidos
    fee_amount = Column(Numeric(15, 2), default=0)  # Taxa cobrada pela Stone
    net_amount = Column(Numeric(15, 2))  # Valor líquido a receber
    
    # Datas importantes
    paid_at = Column(DateTime)  # Quando foi pago
    cancelled_at = Column(DateTime)  # Quando foi cancelado
    refunded_at = Column(DateTime)  # Quando foi estornado
    settlement_date = Column(DateTime)  # Data prevista de recebimento
    
    # Webhook e notificações
    last_webhook_at = Column(DateTime)  # Último webhook recebido
    webhook_count = Column(Integer, default=0)  # Quantos webhooks recebemos
    
    # Dados completos da Stone (JSON)
    stone_response = Column(JSON)  # Response completo da API Stone
    
    # Controle de erro
    error_message = Column(Text)  # Mensagem de erro se houver
    retry_count = Column(Integer, default=0)  # Tentativas de processamento
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    venda = relationship("Venda", foreign_keys=[venda_id], backref="stone_transactions")
    conta_receber = relationship("ContaReceber", foreign_keys=[conta_receber_id], backref="stone_transactions")
    user = relationship("User", foreign_keys=[user_id])
    logs = relationship("StoneTransactionLog", back_populates="transaction", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Serializa para dicionário"""
        return {
            'id': self.id,
            'stone_payment_id': self.stone_payment_id,
            'external_id': self.external_id,
            'venda_id': self.venda_id,
            'conta_receber_id': self.conta_receber_id,
            'payment_method': self.payment_method,
            'amount': safe_decimal_to_float(self.amount),
            'description': self.description,
            'installments': self.installments,
            'status': self.status,
            'stone_status': self.stone_status,
            'customer_name': self.customer_name,
            'customer_document': self.customer_document,
            'customer_email': self.customer_email,
            'pix_qr_code': self.pix_qr_code,
            'pix_qr_code_url': self.pix_qr_code_url,
            'pix_copy_paste': self.pix_copy_paste,
            'pix_expiration': safe_datetime_to_iso(self.pix_expiration),
            'card_brand': self.card_brand,
            'card_last_digits': self.card_last_digits,
            'fee_amount': safe_decimal_to_float(self.fee_amount),
            'net_amount': safe_decimal_to_float(self.net_amount),
            'paid_at': safe_datetime_to_iso(self.paid_at),
            'cancelled_at': safe_datetime_to_iso(self.cancelled_at),
            'refunded_at': safe_datetime_to_iso(self.refunded_at),
            'settlement_date': safe_datetime_to_iso(self.settlement_date),
            'last_webhook_at': safe_datetime_to_iso(self.last_webhook_at),
            'webhook_count': self.webhook_count,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'created_at': safe_datetime_to_iso(self.created_at),
            'updated_at': safe_datetime_to_iso(self.updated_at),
            'tenant_id': self.tenant_id
        }


class StoneTransactionLog(BaseTenantModel):
    """
    Log de eventos de transações Stone
    Registra todas as mudanças de status e webhooks recebidos
    """
    __tablename__ = "stone_transaction_logs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey('stone_transactions.id'), nullable=False, index=True)
    
    # Tipo de evento
    event_type = Column(String(50), nullable=False)  # webhook, status_change, api_call, error
    event_source = Column(String(30))  # stone_webhook, manual, system
    
    # Dados do evento
    old_status = Column(String(30))
    new_status = Column(String(30))
    
    # Detalhes
    description = Column(Text)
    webhook_data = Column(JSON)  # Dados completos do webhook
    error_details = Column(JSON)  # Detalhes de erro se houver
    
    # IP e user agent (para webhooks)
    source_ip = Column(String(50))
    user_agent = Column(Text)
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Pode ser NULL para webhooks
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    transaction = relationship("StoneTransaction", back_populates="logs")
    user = relationship("User", foreign_keys=[user_id])
    
    def to_dict(self):
        """Serializa para dicionário"""
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'event_type': self.event_type,
            'event_source': self.event_source,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'description': self.description,
            'source_ip': self.source_ip,
            'user_agent': self.user_agent,
            'created_at': safe_datetime_to_iso(self.created_at),
            'tenant_id': self.tenant_id
        }


class StoneConfig(BaseTenantModel):
    """
    Configurações da Stone por tenant
    Permite que cada tenant tenha suas próprias credenciais Stone
    """
    __tablename__ = "stone_configs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Credenciais Stone
    client_id = Column(String(200), nullable=False)
    client_secret = Column(String(200), nullable=False)  # Deve ser criptografado
    merchant_id = Column(String(200), nullable=False)
    webhook_secret = Column(String(200))  # Para validar webhooks
    
    # Ambiente
    sandbox = Column(Boolean, default=True)  # True = testes, False = produção
    
    # Configurações de pagamento
    enable_pix = Column(Boolean, default=True)
    enable_credit_card = Column(Boolean, default=True)
    enable_debit_card = Column(Boolean, default=False)
    max_installments = Column(Integer, default=12)
    
    # Configurações de webhook
    webhook_url = Column(String(500))  # URL para receber notificações
    webhook_enabled = Column(Boolean, default=True)
    
    # Status
    active = Column(Boolean, default=True)
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def to_dict(self):
        """Serializa para dicionário (sem expor secrets)"""
        return {
            'id': self.id,
            'merchant_id': self.merchant_id,
            'sandbox': self.sandbox,
            'enable_pix': self.enable_pix,
            'enable_credit_card': self.enable_credit_card,
            'enable_debit_card': self.enable_debit_card,
            'max_installments': self.max_installments,
            'webhook_url': self.webhook_url,
            'webhook_enabled': self.webhook_enabled,
            'active': self.active,
            'created_at': safe_datetime_to_iso(self.created_at),
            'updated_at': safe_datetime_to_iso(self.updated_at),
            'tenant_id': self.tenant_id
        }
