"""Configuração e caixa de saída persistente de XMLs para a contabilidade."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from app.base_models import BaseTenantModel


class XmlContabilidadeConfig(BaseTenantModel):
    __tablename__ = "xml_contabilidade_config"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_xml_contabilidade_config_tenant"),
    )

    email_contador = Column(String(254), nullable=True)
    envio_automatico = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    envio_automatico_desde = Column(DateTime(timezone=True), nullable=True)
    envio_mensal = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    dia_envio_mensal = Column(Integer, nullable=False, default=1, server_default="1")
    hora_envio_mensal = Column(
        String(5), nullable=False, default="08:00", server_default="08:00"
    )
    proximo_envio_mensal = Column(DateTime(timezone=True), nullable=True)


class XmlContabilidadeEnvio(BaseTenantModel):
    __tablename__ = "xml_contabilidade_envios"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_xml_contabilidade_envio_dedupe"
        ),
        Index(
            "ix_xml_contabilidade_envios_pendentes",
            "tenant_id",
            "status",
            "proxima_tentativa_em",
        ),
    )

    origem = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pendente")
    email_destino = Column(String(254), nullable=False)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    agendado_para = Column(DateTime(timezone=True), nullable=True)
    proxima_tentativa_em = Column(DateTime(timezone=True), nullable=False)
    processamento_iniciado_em = Column(DateTime(timezone=True), nullable=True)
    enviado_em = Column(DateTime(timezone=True), nullable=True)
    tentativas = Column(Integer, nullable=False, default=0, server_default="0")
    quantidade_xml = Column(Integer, nullable=True)
    ultimo_erro = Column(String(500), nullable=True)
    nome_arquivo = Column(String(150), nullable=True)
    idempotency_key = Column(String(200), nullable=True)
    provider = Column(String(20), nullable=True)
    documento_id = Column(String(128), nullable=True)
    documento_status = Column(String(20), nullable=True)
