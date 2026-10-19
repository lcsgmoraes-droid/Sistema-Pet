"""Histórico de relacionamento para incentivar o uso do saldo de cashback."""

from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.base_models import BaseTenantModel


class CashbackContato(BaseTenantModel):
    """Evento imutável: abertura, anotação ou mudança de estágio gera nova linha."""

    __tablename__ = "cashback_contatos"

    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    operador_nome = Column(String(200), nullable=False)
    acao = Column(String(40), nullable=False)
    status = Column(String(30), nullable=False)
    mensagem = Column(Text)
    observacao = Column(Text)
    telefone = Column(String(20))
    proximo_contato_em = Column(Date)
    saldo_cashback = Column(Numeric(12, 2), nullable=False)
    chave_cliente = Column(String(36), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "cliente_id",
            "acao",
            "chave_cliente",
            name="uq_cashback_contatos_requisicao",
        ),
        Index(
            "ix_cashback_contatos_tenant_cliente_id", "tenant_id", "cliente_id", "id"
        ),
    )
