"""Configuração e caixa de saída persistente de XMLs para a contabilidade."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    JSON,
    LargeBinary,
    ForeignKeyConstraint,
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
        Index(
            "uq_xml_contabilidade_envios_tenant_id_id", "tenant_id", "id", unique=True
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


class XmlContabilidadeMonitor(BaseTenantModel):
    """Cursor durável: também consulta eventos de notas emitidas anteriormente."""

    __tablename__ = "xml_contabilidade_documentos_monitor"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider",
            "documento_id",
            name="uq_xml_contabilidade_monitor_documento",
        ),
        Index(
            "ix_xml_contabilidade_monitor_consulta", "tenant_id", "proxima_consulta_em"
        ),
    )

    provider = Column(String(20), nullable=False)
    documento_id = Column(String(128), nullable=False)
    ultima_consulta_em = Column(DateTime(timezone=True), nullable=True)
    proxima_consulta_em = Column(DateTime(timezone=True), nullable=False)


class XmlContabilidadeEvento(BaseTenantModel):
    """Somente comprovantes fiscais oficiais já validados; XML original intacto."""

    __tablename__ = "xml_contabilidade_eventos_recebidos"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "identidade",
            "protocolo",
            name="uq_xml_contabilidade_evento_protocolo",
        ),
        Index("ix_xml_contabilidade_eventos_registro", "tenant_id", "registrado_em"),
    )

    provider = Column(String(20), nullable=False)
    documento_id = Column(String(128), nullable=False)
    chave = Column(String(44), nullable=False)
    identidade = Column(String(54), nullable=False)
    tipo = Column(String(6), nullable=False)
    sequencia = Column(Integer, nullable=False)
    protocolo = Column(String(15), nullable=False)
    registrado_em = Column(DateTime(timezone=True), nullable=False)
    nome_arquivo = Column(String(100), nullable=False)
    xml = Column(LargeBinary, nullable=False)


class XmlContabilidadeTentativa(BaseTenantModel):
    """Relatório final por tentativa; inserção única, sem reescrever o histórico."""

    __tablename__ = "xml_contabilidade_tentativas"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "envio_id",
            "numero_tentativa",
            name="uq_xml_contabilidade_tentativa_numero",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "envio_id"],
            ["xml_contabilidade_envios.tenant_id", "xml_contabilidade_envios.id"],
            ondelete="RESTRICT",
        ),
        Index("ix_xml_contabilidade_tentativas_envio", "tenant_id", "envio_id", "id"),
    )

    envio_id = Column(Integer, nullable=False)
    numero_tentativa = Column(Integer, nullable=False)
    iniciado_em = Column(DateTime(timezone=True), nullable=False)
    concluido_em = Column(DateTime(timezone=True), nullable=False)
    resultado = Column(String(30), nullable=False)
    resumo = Column(JSON, nullable=False)
    snapshot = Column(JSON, nullable=False)


from sqlalchemy import event  # noqa: E402


@event.listens_for(XmlContabilidadeTentativa, "before_update")
@event.listens_for(XmlContabilidadeTentativa, "before_delete")
def _preservar_tentativa(_mapper, _connection, _target):
    raise ValueError("Relatórios de tentativas são imutáveis.")
