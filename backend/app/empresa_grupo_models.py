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
    JSON,
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
    usuario_referencia_id = Column(Integer, nullable=True)
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


class EmpresaGrupoTransferencia(Base):
    __tablename__ = "empresa_grupo_transferencias"
    __table_args__ = (
        UniqueConstraint(
            "empresa_origem_id",
            "chave_idempotencia",
            name="uq_empresa_grupo_transferencia_idempotencia",
        ),
        Index(
            "ix_empresa_grupo_transferencias_grupo_criado",
            "grupo_id",
            "criado_em",
        ),
        Index(
            "ix_empresa_grupo_transferencias_destino_criado",
            "empresa_destino_id",
            "criado_em",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("empresa_grupos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    empresa_origem_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    empresa_destino_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    usuario_origem_id = Column(Integer, nullable=False)
    usuario_destino_id = Column(Integer, nullable=True)
    chave_idempotencia = Column(String(36), nullable=False)
    documento = Column(String(100), nullable=False)
    status = Column(
        String(20), nullable=False, default="processando", server_default="processando"
    )
    conta_receber_origem_id = Column(Integer, nullable=True)
    conta_pagar_destino_id = Column(Integer, nullable=True)
    itens_snapshot = Column(JSON, nullable=False, default=list)
    resultado = Column(JSON, nullable=True)
    criado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    concluido_em = Column(DateTime(timezone=True), nullable=True)


class EmpresaGrupoProdutoVinculo(Base):
    """Equivalencia manual entre produtos de empresas do mesmo grupo.

    Os IDs de produto nao recebem chave estrangeira porque pertencem a tenants
    diferentes e podem se repetir. O servico sempre valida empresa, produto e
    participacao ativa antes de criar ou consultar o vinculo.
    """

    __tablename__ = "empresa_grupo_produto_vinculos"
    __table_args__ = (
        UniqueConstraint(
            "grupo_id",
            "empresa_a_id",
            "produto_a_id",
            "empresa_b_id",
            "produto_b_id",
            name="uq_empresa_grupo_produto_vinculo_par",
        ),
        Index(
            "ix_empresa_grupo_produto_vinculos_grupo_status",
            "grupo_id",
            "status",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("empresa_grupos.id", ondelete="CASCADE"),
        nullable=False,
    )
    empresa_a_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    produto_a_id = Column(Integer, nullable=False)
    empresa_b_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    produto_b_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="ativo", server_default="ativo")
    criado_por_empresa_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    criado_por_usuario_id = Column(Integer, nullable=False)
    criado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    removido_em = Column(DateTime(timezone=True), nullable=True)
