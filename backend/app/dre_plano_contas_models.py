
from sqlalchemy import Column, String, Integer, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.base_models import BaseTenantModel
import enum

# ============================================================
# ENUMS
# ============================================================

class NaturezaDRE(enum.Enum):
    RECEITA = "receita"
    CUSTO = "custo"
    DESPESA = "despesa"
    RESULTADO = "resultado"

class TipoCusto(enum.Enum):
    DIRETO = "direto"
    INDIRETO_RATEAVEL = "indireto_rateavel"
    CORPORATIVO = "corporativo"

class BaseRateio(enum.Enum):
    FATURAMENTO = "faturamento"
    PEDIDOS = "pedidos"
    PERCENTUAL = "percentual"
    MANUAL = "manual"

class EscopoRateio(enum.Enum):
    LOJA_FISICA = "loja_fisica"
    ONLINE = "online"
    AMBOS = "ambos"

# ============================================================
# MODELS
# ============================================================

class DRECategoria(BaseTenantModel):
    """
    Categoria principal da DRE (agrupamento visual).
    Ex: Receita Bruta, Despesas Operacionais
    """
    __tablename__ = "dre_categorias"
    __table_args__ = {'extend_existing': True}

    nome = Column(String(100), nullable=False)
    ordem = Column(Integer, default=0)
    natureza = Column(Enum(NaturezaDRE, values_callable=lambda x: [e.value for e in x]), nullable=False)
    ativo = Column(Boolean, default=True)

    subcategorias = relationship(
        "DRESubcategoria",
        back_populates="categoria",
        cascade="all, delete-orphan"
    )


class DRESubcategoria(BaseTenantModel):
    """
    SUBCATEGORIA = BASE DA DRE
    Tudo acontece a partir dela.
    """
    __tablename__ = "dre_subcategorias"
    __table_args__ = {'extend_existing': True}

    categoria_id = Column(
        Integer,
        ForeignKey("dre_categorias.id"),
        nullable=False
    )

    nome = Column(String(150), nullable=False)

    # Comportamento
    tipo_custo = Column(Enum(TipoCusto, values_callable=lambda x: [e.value for e in x]), nullable=False)
    base_rateio = Column(Enum(BaseRateio, values_callable=lambda x: [e.value for e in x]), nullable=True)
    escopo_rateio = Column(Enum(EscopoRateio, values_callable=lambda x: [e.value for e in x]), nullable=False)

    ativo = Column(Boolean, default=True)
    custo_pe = Column(String(10), nullable=True)  # 'fixo' | 'variavel' | null (para Ponto de Equilíbrio)
    categoria_financeira_id = Column(Integer, ForeignKey("categorias_financeiras.id", ondelete="SET NULL"), nullable=True)

    categoria = relationship("DRECategoria", back_populates="subcategorias")
