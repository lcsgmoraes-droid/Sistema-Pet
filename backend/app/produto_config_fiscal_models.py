from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.sql import func

from .db import Base
from .base_models import TenantScoped


class ProdutoConfigFiscal(TenantScoped, Base):
    """
    Configuração fiscal de produto (V2). Definição ORM canônica e ÚNICA, alinhada
    ao schema real (migration ``bda1c213cae2``). Antes existia uma cópia idêntica
    em ``app/fiscal_models/produto_config_fiscal.py``.

    Mantém esquema próprio (``id`` autoincrement, ``created_at``/``updated_at``) por
    isso não herda ``BaseTenantModel``; adota o mixin ``TenantScoped`` para entrar no
    filtro global de tenant (``tenant_id`` vem do mixin: UUID NOT NULL, indexado —
    schema idêntico ao que já estava na tabela).
    """

    __tablename__ = "produto_config_fiscal"

    id = Column(Integer, primary_key=True)

    # Vínculo com produto
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, unique=True)

    # Herança
    herdado_da_empresa = Column(Boolean, nullable=False, default=True)

    # Identificação fiscal
    ncm = Column(String(10))
    cest = Column(String(10))
    origem_mercadoria = Column(String(1))  # 0 nacional, 1 estrangeira etc.

    # ICMS
    cst_icms = Column(String(3))
    icms_aliquota = Column(Numeric(5, 2))
    icms_st = Column(Boolean)

    # CFOP
    cfop_venda = Column(String(4))
    cfop_compra = Column(String(4))

    # PIS / COFINS
    pis_cst = Column(String(3))
    pis_aliquota = Column(Numeric(5, 2))
    cofins_cst = Column(String(3))
    cofins_aliquota = Column(Numeric(5, 2))

    # Campo livre para explicações / sugestões
    observacao_fiscal = Column(Text)

    # Controle
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
