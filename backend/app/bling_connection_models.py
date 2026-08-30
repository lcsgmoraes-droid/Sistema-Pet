"""Credenciais e roteamento multi-tenant da integracao Bling."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.base_models import BaseTenantModel
from app.db import Base
from app.security.tenant_config_crypto import decrypt_secret, encrypt_secret


class BlingConnection(BaseTenantModel):
    """Conexao OAuth do Bling isolada por tenant."""

    __tablename__ = "bling_connections"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_bling_connections_tenant"),
    )

    _access_token_encrypted = Column("access_token_encrypted", Text, nullable=True)
    _refresh_token_encrypted = Column("refresh_token_encrypted", Text, nullable=True)
    oauth_client_id = Column(String(255), nullable=True)
    _oauth_client_secret_encrypted = Column(
        "oauth_client_secret_encrypted", Text, nullable=True
    )
    company_id = Column(String(100), nullable=True, index=True)
    status = Column(
        String(24), nullable=False, default="active", server_default="active"
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    connected_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_refresh_at = Column(DateTime(timezone=True), nullable=True)
    renewal_count = Column(Integer, nullable=False, default=0, server_default="0")
    last_error = Column(Text, nullable=True)

    @property
    def access_token(self) -> str:
        return decrypt_secret(self._access_token_encrypted)

    @access_token.setter
    def access_token(self, value: str | None) -> None:
        self._access_token_encrypted = encrypt_secret(value)

    @property
    def refresh_token(self) -> str:
        return decrypt_secret(self._refresh_token_encrypted)

    @refresh_token.setter
    def refresh_token(self, value: str | None) -> None:
        self._refresh_token_encrypted = encrypt_secret(value)

    @property
    def oauth_client_secret(self) -> str:
        return decrypt_secret(self._oauth_client_secret_encrypted)

    @oauth_client_secret.setter
    def oauth_client_secret(self, value: str | None) -> None:
        self._oauth_client_secret_encrypted = encrypt_secret(value)


class BlingCompanyTenantLink(Base):
    """Indice global minimo: companyId autenticado do webhook -> tenant."""

    __tablename__ = "bling_company_tenant_links"

    company_id = Column(String(100), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
