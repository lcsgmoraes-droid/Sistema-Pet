"""Rascunho fiscal independente: clonar não cria uma nova venda."""

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text

from app.base_models import BaseTenantModel


class NotaFiscalClone(BaseTenantModel):
    __tablename__ = "notas_fiscais_clones"

    origem = Column(JSON, nullable=False)
    dados = Column(JSON, nullable=False)
    xml_origem = Column(Text, nullable=False)
    modelo = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False, default="rascunho")
    idempotency_key = Column(String(128), nullable=True)
    enviado_em = Column(DateTime(timezone=True), nullable=True)
    correlation_id = Column(String(128), nullable=True)
    numero = Column(String(20), nullable=True)
    chave = Column(String(44), nullable=True)
    protocolo = Column(String(128), nullable=True)
    motivo = Column(Text, nullable=True)
    xml = Column(Text, nullable=True)
    cancelamento_status = Column(String(20), nullable=True)
    cancelamento_codigo = Column(String(80), nullable=True)
    cancelamento_motivo = Column(Text, nullable=True)
    cancelamento_solicitado_em = Column(DateTime(timezone=True), nullable=True)
