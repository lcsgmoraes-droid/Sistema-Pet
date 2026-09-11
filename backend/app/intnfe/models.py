"""Vinculo fiscal independente do cadastro comercial da empresa."""

from sqlalchemy import Boolean, Column, DateTime, String, Text, UniqueConstraint

from app.base_models import BaseTenantModel
from app.security.tenant_config_crypto import decrypt_secret_strict, encrypt_secret


class IntNFeConnection(BaseTenantModel):
    __tablename__ = "intnfe_connections"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_intnfe_tenant"),
        UniqueConstraint("cnpj", name="uq_intnfe_cnpj"),
        UniqueConstraint("emitente_id", name="uq_intnfe_emitente"),
    )

    cnpj = Column(String(14), nullable=False)
    razao_social = Column(String(60), nullable=False)
    nome_fantasia = Column(String(60), nullable=False)
    integrador_id = Column(String(128), nullable=False)
    emitente_id = Column(String(128), nullable=True)
    client_id = Column(String(128), nullable=True)
    client_secret_encrypted = Column(Text, nullable=True)
    status = Column(String(40), nullable=False, default="nao_vinculado")
    # Gravado ANTES do POST externo. Resposta perdida nao autoriza nova criacao.
    criacao_iniciada = Column(Boolean, nullable=False, default=False)
    operacao_id = Column(String(36), nullable=True)
    operacao_iniciada_em = Column(DateTime(timezone=True), nullable=True)
    ultimo_codigo = Column(String(64), nullable=True)
    correlation_id = Column(String(128), nullable=True)
    vinculado_em = Column(DateTime(timezone=True), nullable=True)
    certificado_valido_ate = Column(DateTime(timezone=True), nullable=True)

    @property
    def client_secret(self) -> str:
        return decrypt_secret_strict(self.client_secret_encrypted)

    @client_secret.setter
    def client_secret(self, value: str) -> None:
        self.client_secret_encrypted = encrypt_secret(value)
