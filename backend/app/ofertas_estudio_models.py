"""Modelos persistentes do Estudio de Ofertas."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.base_models import BaseTenantModel
from app.db import Base


class OfertaPublicacao(BaseTenantModel):
    """Snapshot imutavel de uma arte publicada por uma empresa."""

    __tablename__ = "oferta_publicacoes"

    titulo = Column(String(160), nullable=False)
    periodicidade = Column(String(20), nullable=False, default="avulsa")
    tipo_arte = Column(String(24), nullable=False, default="jornal")
    formato = Column(String(24), nullable=False, default="quadrado")
    inicio_em = Column(DateTime(timezone=True), nullable=False)
    fim_em = Column(DateTime(timezone=True), nullable=False)
    expira_em = Column(DateTime(timezone=True), nullable=False)
    desativada_em = Column(DateTime(timezone=True), nullable=True)
    imagens_urls = Column(JSON, nullable=False, default=list)
    produtos_snapshot = Column(JSON, nullable=False, default=list)
    configuracao = Column(JSON, nullable=False, default=dict)
    criado_por_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    indice_publico = relationship(
        "OfertaPublicacaoToken",
        back_populates="publicacao",
        uselist=False,
        cascade="all, delete-orphan",
    )


class OfertaPublicacaoToken(Base):
    """Indice global minimo: token opaco -> tenant/publicacao."""

    __tablename__ = "oferta_publicacao_tokens"

    token = Column(String(64), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    publicacao_id = Column(
        Integer,
        ForeignKey("oferta_publicacoes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    publicacao = relationship("OfertaPublicacao", back_populates="indice_publico")
