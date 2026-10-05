"""Eventos imutáveis de devolução para o regime de competência da DRE."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
)

from app.base_models import BaseTenantModel


class VendaDevolucao(BaseTenantModel):
    __tablename__ = "vendas_devolucoes"
    __table_args__ = (
        Index(
            "ix_vendas_devolucoes_tenant_data_canal",
            "tenant_id",
            "data_competencia",
            "canal",
        ),
        Index("ix_vendas_devolucoes_tenant_venda", "tenant_id", "venda_id"),
    )

    venda_id = Column(ForeignKey("vendas.id", ondelete="RESTRICT"), nullable=False)
    user_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    data_competencia = Column(Date, nullable=False)
    canal = Column(String(50), nullable=False)
    forma_estorno = Column(String(20), nullable=False)  # dinheiro ou credito
    motivo = Column(Text, nullable=False)
    valor_devolvido = Column(Numeric(12, 2), nullable=False)
    custo_produtos_estornado = Column(Numeric(12, 2), nullable=False)
    custo_servicos_estornado = Column(Numeric(12, 2), nullable=False)
    custo_pendente = Column(Boolean, nullable=False, default=False)
    historico_pre_evento = Column(Boolean, nullable=False, default=False)
    itens = Column(JSON, nullable=False)
    movimentacao_caixa_id = Column(ForeignKey("movimentacoes_caixa.id"), nullable=True)
