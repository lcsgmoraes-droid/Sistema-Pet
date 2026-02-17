from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db import Base


class ConfiguracaoCustoMoto(Base):
    __tablename__ = "configuracoes_custo_moto"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(ForeignKey("tenants.id"), nullable=False, unique=True)

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
