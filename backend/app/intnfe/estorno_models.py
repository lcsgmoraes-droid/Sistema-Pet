"""Documento inverso independente da venda e da NFC-e original."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)

from app.base_models import BaseTenantModel


class IntNFeEstorno(BaseTenantModel):
    __tablename__ = "intnfe_estornos"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "venda_id",
            "ambiente_codigo",
            name="uq_intnfe_estorno_venda_ambiente",
        ),
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_intnfe_estorno_idempotency"
        ),
    )

    venda_id = Column(
        Integer, ForeignKey("vendas.id", ondelete="RESTRICT"), nullable=False
    )
    ambiente_codigo = Column(SmallInteger, nullable=False)
    original_chave = Column(String(44), nullable=False)
    original_xml_hash = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    snapshot = Column(JSON, nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    status = Column(String(20), nullable=False)
    motivo_operacao = Column(String(500), nullable=False)
    declarado_nao_realizada = Column(Boolean, nullable=False)
    solicitado_por = Column(Integer, nullable=True)
    tentativa_em = Column(DateTime(timezone=True), nullable=False)
    correlation_id = Column(String(128), nullable=True)
    numero = Column(Integer, nullable=True)
    serie = Column(Integer, nullable=True)
    chave = Column(String(44), nullable=True)
    protocolo = Column(String(50), nullable=True)
    codigo = Column(String(80), nullable=True)
    motivo = Column(String(500), nullable=True)
    xml = Column(Text, nullable=True)
    xml_validado = Column(Boolean, nullable=False, default=False)
    autorizado_em = Column(DateTime(timezone=True), nullable=True)
