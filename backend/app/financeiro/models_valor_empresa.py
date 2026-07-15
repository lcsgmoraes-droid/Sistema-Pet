"""Configuracao persistida da avaliacao gerencial da empresa."""

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.base_models import BaseTenantModel


class ValorEmpresaConfiguracao(BaseTenantModel):
    """Premissas editaveis usadas na estimativa de valor do negocio."""

    __tablename__ = "valor_empresa_configuracoes"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_valor_empresa_configuracoes_tenant"),
    )

    periodo_dias = Column(Integer, nullable=False, default=60)
    canais = Column(String(300), nullable=False, default="loja_fisica")
    fornecedores_exclusoes = Column(JSON, nullable=False, default=list)

    folha_mensal_override = Column(Numeric(14, 2), nullable=True)
    despesas_fixas_mensais_override = Column(Numeric(14, 2), nullable=True)
    margem_contribuicao_override = Column(Numeric(7, 4), nullable=True)
    imobilizado_override = Column(Numeric(14, 2), nullable=True)
    outros_ativos = Column(Numeric(14, 2), nullable=False, default=0)
    incluir_dividas = Column(Boolean, nullable=False, default=False)
    percentual_dividas_assumidas = Column(Numeric(7, 4), nullable=False, default=100)

    desconto_estoque_conservador = Column(Numeric(7, 4), nullable=False, default=45)
    desconto_estoque_provavel = Column(Numeric(7, 4), nullable=False, default=25)
    desconto_estoque_otimista = Column(Numeric(7, 4), nullable=False, default=10)
    multiplo_lucro_conservador = Column(Numeric(7, 4), nullable=False, default=18)
    multiplo_lucro_provavel = Column(Numeric(7, 4), nullable=False, default=24)
    multiplo_lucro_otimista = Column(Numeric(7, 4), nullable=False, default=30)
    dias_estoque_lento = Column(Integer, nullable=False, default=365)
    observacoes = Column(Text, nullable=True)
