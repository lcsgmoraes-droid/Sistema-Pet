"""Historico de alteracoes feitas pela equipe da plataforma (OPS) nos dados de uma loja.

Fica fora do isolamento por loja de proposito: quem le e a equipe da plataforma,
que precisa ver o historico de qualquer loja.
"""

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base


class OpsTenantChangeLog(Base):
    __tablename__ = "ops_tenant_change_log"
    __table_args__ = (
        Index("ix_ops_tenant_change_log_tenant_data", "tenant_id", "criado_em"),
        Index("ix_ops_tenant_change_log_data", "criado_em"),
    )

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    criado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    admin_id = Column(Integer, nullable=True)
    admin_email = Column(String(255), nullable=False)
    # modulo | comercial | acompanhamento
    categoria = Column(String(30), nullable=False)
    # codigo do modulo ou nome do campo alterado
    campo = Column(String(80), nullable=False)
    antes = Column(Text, nullable=True)
    depois = Column(Text, nullable=True)
