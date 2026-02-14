from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey
)
from sqlalchemy.sql import func
from app.db.base_class import Base


class EmpresaConfigFiscal(Base):
    __tablename__ = "empresa_config_fiscal"

    id = Column(Integer, primary_key=True)

    tenant_id = Column(Integer, nullable=False, index=True)

    fiscal_estado_padrao_id = Column(
        Integer,
        ForeignKey("fiscal_estado_padrao.id"),
        nullable=False
    )

    uf = Column(String(2), nullable=False)

    regime_tributario = Column(String(50), nullable=False)
    cnae_principal = Column(String(10))
    contribuinte_icms = Column(Boolean, nullable=False)

    icms_aliquota_interna = Column(Numeric(5, 2), nullable=False)
    icms_aliquota_interestadual = Column(Numeric(5, 2), nullable=False)
    aplica_difal = Column(Boolean, nullable=False)

    cfop_venda_interna = Column(String(4), nullable=False)
    cfop_venda_interestadual = Column(String(4), nullable=False)
    cfop_compra = Column(String(4), nullable=False)

    pis_cst_padrao = Column(String(3))
    pis_aliquota = Column(Numeric(5, 2))
    cofins_cst_padrao = Column(String(3))
    cofins_aliquota = Column(Numeric(5, 2))

    municipio_iss = Column(String(100))
    iss_aliquota = Column(Numeric(5, 2))
    iss_retido = Column(Boolean, default=False)

    herdado_do_estado = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
