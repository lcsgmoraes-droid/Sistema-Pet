from sqlalchemy import Column, Integer, Numeric, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db import Base
from app.base_models import TenantScoped


class ConfiguracaoCustoMoto(TenantScoped, Base):
    """
    Configuração de custos da moto da loja (um registro por tenant).

    Adota o mixin ``TenantScoped`` para entrar no filtro global de tenant + fail-fast.
    ``tenant_id`` passa a ser UUID (alinhado ao contexto de tenant, que é UUID) — antes
    era ``FK -> tenants.id`` (String(36)), fora do filtro. A FK foi removida (tipos
    incompatíveis UUID vs varchar(36)); o vínculo lógico com a loja é garantido pelo
    filtro automático. A coluna local sobrescreve o ``tenant_id`` do mixin para
    preservar o ``UNIQUE`` ("um config por loja").
    """

    __tablename__ = "configuracoes_custo_moto"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)

    # Combustível
    preco_combustivel = Column(Numeric(10, 2), nullable=False)
    km_por_litro = Column(Numeric(10, 2), nullable=False)

    # Manutenções por KM
    km_troca_oleo = Column(Integer)
    custo_troca_oleo = Column(Numeric(10, 2))

    km_troca_pneu_dianteiro = Column(Integer)
    custo_pneu_dianteiro = Column(Numeric(10, 2))

    km_troca_pneu_traseiro = Column(Integer)
    custo_pneu_traseiro = Column(Numeric(10, 2))

    km_troca_kit_traseiro = Column(Integer)
    custo_kit_traseiro = Column(Numeric(10, 2))

    km_manutencao_geral = Column(Integer)
    custo_manutencao_geral = Column(Numeric(10, 2))

    # Custos fixos mensais
    seguro_mensal = Column(Numeric(10, 2))
    licenciamento_mensal = Column(Numeric(10, 2))
    ipva_mensal = Column(Numeric(10, 2))
    outros_custos_mensais = Column(Numeric(10, 2))

    # Controle
    km_medio_mensal = Column(Numeric(10, 2))

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_configuracoes_custo_moto_tenant"),
    )
