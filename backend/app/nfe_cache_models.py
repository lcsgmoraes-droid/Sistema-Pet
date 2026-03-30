from sqlalchemy import Column, String, Integer, DateTime, JSON, Numeric, UniqueConstraint
from sqlalchemy.sql import func

from app.base_models import BaseTenantModel


class BlingNotaFiscalCache(BaseTenantModel):
    __tablename__ = "bling_notas_fiscais_cache"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "bling_id",
            "modelo",
            name="uq_bling_notas_fiscais_cache_tenant_bling_modelo",
        ),
    )

    bling_id = Column(String(50), nullable=False)
    modelo = Column(Integer, nullable=False, default=55)
    tipo = Column(String(10), nullable=False, default="nfe")
    numero = Column(String(50), nullable=True)
    serie = Column(String(20), nullable=True)
    status = Column(String(30), nullable=True)
    chave = Column(String(64), nullable=True)
    data_emissao = Column(DateTime, nullable=True, index=True)
    valor = Column(Numeric(12, 2), nullable=True)

    cliente = Column(JSON, nullable=True)
    loja = Column(JSON, nullable=True)
    unidade_negocio = Column(JSON, nullable=True)

    canal = Column(String(50), nullable=True)
    canal_label = Column(String(100), nullable=True)
    numero_loja_virtual = Column(String(100), nullable=True)
    origem_loja_virtual = Column(String(100), nullable=True)
    origem_canal_venda = Column(String(100), nullable=True)
    numero_pedido_loja = Column(String(100), nullable=True)
    pedido_bling_id_ref = Column(String(50), nullable=True)

    source = Column(String(30), nullable=False, default="bling_api")
    resumo_payload = Column(JSON, nullable=True)
    detalhe_payload = Column(JSON, nullable=True)
    detalhada_em = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
