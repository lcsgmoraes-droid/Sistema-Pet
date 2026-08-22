"""Modelos globais para grupos que conectam duas ou mais empresas.

Estas tabelas nao herdam ``BaseTenantModel`` porque um grupo atravessa tenants.
O acesso deve acontecer somente pelo servico de grupos, que valida explicitamente
o tenant ator em todas as consultas e mutacoes.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db import Base


class EmpresaGrupo(Base):
    __tablename__ = "empresa_grupos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(150), nullable=False)
    criado_por_empresa_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    criado_por_usuario_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="ativo", server_default="ativo")
    versao_membros = Column(Integer, nullable=False, default=1, server_default="1")
    criado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EmpresaGrupoMembro(Base):
    __tablename__ = "empresa_grupo_membros"
    __table_args__ = (
        UniqueConstraint(
            "grupo_id", "empresa_id", name="uq_empresa_grupo_membro_empresa"
        ),
        Index(
            "ix_empresa_grupo_membros_empresa_status",
            "empresa_id",
            "status",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("empresa_grupos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    empresa_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    papel = Column(
        String(20), nullable=False, default="membro", server_default="membro"
    )
    status = Column(String(20), nullable=False, default="ativo", server_default="ativo")
    entrou_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    removido_em = Column(DateTime(timezone=True), nullable=True)


class EmpresaGrupoCodigo(Base):
    __tablename__ = "empresa_grupo_codigos"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "competencia", name="uq_empresa_grupo_codigo_competencia"
        ),
        Index(
            "ix_empresa_grupo_codigos_empresa_validade",
            "empresa_id",
            "expira_em",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    competencia = Column(String(7), nullable=False)
    codigo = Column(String(12), nullable=False, unique=True, index=True)
    criado_por_usuario_id = Column(Integer, nullable=False)
    criado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expira_em = Column(DateTime(timezone=True), nullable=False)


class EmpresaGrupoConvite(Base):
    __tablename__ = "empresa_grupo_convites"
    __table_args__ = (
        UniqueConstraint(
            "grupo_id",
            "empresa_convidada_id",
            name="uq_empresa_grupo_convite_empresa",
        ),
        Index(
            "ix_empresa_grupo_convites_destino_status",
            "empresa_convidada_id",
            "status",
            "expira_em",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("empresa_grupos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    empresa_convidada_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    convidado_por_empresa_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    convidado_por_usuario_id = Column(Integer, nullable=False)
    respondido_por_usuario_id = Column(Integer, nullable=True)
    status = Column(
        String(20), nullable=False, default="pendente", server_default="pendente"
    )
    criado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expira_em = Column(DateTime(timezone=True), nullable=False)
    respondido_em = Column(DateTime(timezone=True), nullable=True)
