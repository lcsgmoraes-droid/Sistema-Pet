from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.sql import func

from .db import Base
from .base_models import TenantScoped


class VariacaoConfigFiscal(TenantScoped, Base):
    """
    Configuração fiscal por variação de produto.

    Mantém esquema próprio (``id`` autoincrement, ``created_at``/``updated_at``) por
    isso não herda ``BaseTenantModel``; adota o mixin ``TenantScoped`` para entrar no
    filtro global de tenant (``tenant_id`` vem do mixin: UUID NOT NULL, indexado).

    Correção de bug: ``tenant_id`` era ``Integer`` (incompatível com o restante do
    sistema multi-tenant, que usa ``UUID``). Passa a vir do mixin como ``UUID``.

    Obs.: ``variacao_id`` aponta para a tabela ``produto_variacao``, que NÃO possui
    modelo ORM mapeado nem migration (idem ForeignKey comentada em
    ``fiscal_models/kit_composicao.py``). Por isso não declaramos ``ForeignKey`` aqui
    — apenas a coluna + unicidade — evitando FK pendurada que quebra
    ``create_all``/registry.
    """
    __tablename__ = "variacao_config_fiscal"

    id = Column(Integer, primary_key=True)

    # Vínculo com variação (produto_variacao não tem modelo ORM — sem ForeignKey)
    variacao_id = Column(Integer, nullable=False, unique=True)

    # Herança a partir do produto
    produto_config_fiscal_id = Column(
        Integer,
        ForeignKey("produto_config_fiscal.id"),
        nullable=True,
    )

    herdado_do_produto = Column(Boolean, nullable=False, default=True)

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

    # Observações
    observacao_fiscal = Column(Text)

    configuracao_sugerida = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
