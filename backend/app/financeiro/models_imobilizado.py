"""Modelos do cadastro de bens do imobilizado."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.base_models import BaseTenantModel


class BemImobilizado(BaseTenantModel):
    """Bem duravel pertencente ao patrimonio da empresa."""

    __tablename__ = "bens_imobilizados"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_bens_imobilizados_quantidade"),
        CheckConstraint(
            "valor_aquisicao >= 0 AND valor_residual >= 0",
            name="ck_bens_imobilizados_valores",
        ),
        CheckConstraint(
            "valor_residual <= valor_aquisicao",
            name="ck_bens_imobilizados_residual",
        ),
        UniqueConstraint(
            "tenant_id",
            "codigo_patrimonial",
            name="uq_bens_imobilizados_tenant_codigo",
        ),
        Index("ix_bens_imobilizados_tenant_status", "tenant_id", "status"),
        Index("ix_bens_imobilizados_tenant_categoria", "tenant_id", "categoria"),
    )

    nome = Column(String(180), nullable=False)
    codigo_patrimonial = Column(String(60), nullable=True)
    categoria = Column(String(40), nullable=False, default="outros")
    descricao = Column(Text, nullable=True)
    localizacao = Column(String(150), nullable=True)
    fornecedor = Column(String(180), nullable=True)
    documento = Column(String(100), nullable=True)
    documento_url = Column(String(500), nullable=True)

    quantidade = Column(Integer, nullable=False, default=1)
    data_aquisicao = Column(Date, nullable=False)
    valor_aquisicao = Column(Numeric(14, 2), nullable=False)
    valor_residual = Column(Numeric(14, 2), nullable=False, default=0)
    valor_mercado = Column(Numeric(14, 2), nullable=True)
    depreciar = Column(Boolean, nullable=False, default=True)
    vida_util_meses = Column(Integer, nullable=True)

    status = Column(String(30), nullable=False, default="ativo")
    data_baixa = Column(Date, nullable=True)
    motivo_baixa = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
