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


class KitConfigFiscal(TenantScoped, Base):
    """
    Configuração fiscal de KIT, vinculada a um produto do tipo KIT.

    Definição ORM canônica e ÚNICA, alinhada ao schema real (migration
    ``bda1c213cae2``). Antes existia uma cópia divergente em
    ``app/fiscal_models/kit_config_fiscal.py``; esta é a versão correta segundo a
    tabela real: ``cfop_venda``/``cfop_compra`` (e NÃO um campo único ``cfop``),
    ``pis_cst``/``cofins_cst``, ``observacao_fiscal`` e ``produto_kit_id`` NOT NULL.

    Mantém esquema próprio (``id`` autoincrement, ``created_at``/``updated_at``) por
    isso não herda ``BaseTenantModel``; adota o mixin ``TenantScoped`` para entrar no
    filtro global de tenant (``tenant_id`` vem do mixin: UUID NOT NULL, indexado —
    schema idêntico ao que já estava na tabela).
    """
    __tablename__ = "kit_config_fiscal"

    id = Column(Integer, primary_key=True)

    # Kit vinculado a produto (NOT NULL conforme schema real)
    produto_kit_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)

    # Controle de herança
    herdado_da_empresa = Column(Boolean, nullable=False, default=True)

    # Identificação fiscal
    ncm = Column(String(10))
    cest = Column(String(10))
    origem_mercadoria = Column(String(1))

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

    observacao_fiscal = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
