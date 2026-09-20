"""Modelos globais para grupos que conectam duas ou mais empresas.

Estas tabelas nao herdam ``BaseTenantModel`` porque um grupo atravessa tenants.
O acesso deve acontecer somente pelo servico de grupos, que valida explicitamente
o tenant ator em todas as consultas e mutacoes.
"""

from sqlalchemy import (
    Boolean,
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


class GrupoComercial(Base):
    __tablename__ = "grupos_comerciais"

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


class GrupoComercialMembro(Base):
    __tablename__ = "grupo_comercial_membros"
    __table_args__ = (
        UniqueConstraint(
            "grupo_id", "empresa_id", name="uq_grupo_comercial_membro_empresa"
        ),
        Index(
            "ix_grupo_comercial_membros_empresa_status",
            "empresa_id",
            "status",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
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


class GrupoComercialGestor(Base):
    """Usuario com acesso a tela de gestao do grupo (ver/gerenciar lojas,
    billing consolidado). So o usuario master do grupo concede ou revoga
    esta linha - nao e um vinculo que o proprio gestor possa repassar.
    """

    __tablename__ = "grupo_comercial_gestores"
    __table_args__ = (
        UniqueConstraint(
            "grupo_id", "user_id", name="uq_grupo_comercial_gestor_usuario"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concedido_por_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status = Column(String(20), nullable=False, default="ativo", server_default="ativo")
    concedido_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revogado_em = Column(DateTime(timezone=True), nullable=True)


class GrupoComercialTransferencia(Base):
    __tablename__ = "grupo_comercial_transferencias"
    __table_args__ = (
        UniqueConstraint(
            "empresa_origem_id",
            "chave_idempotencia",
            name="uq_grupo_comercial_transferencia_idempotencia",
        ),
        Index(
            "ix_grupo_comercial_transferencias_grupo_criado",
            "grupo_id",
            "criado_em",
        ),
        Index(
            "ix_grupo_comercial_transferencias_destino_criado",
            "empresa_destino_id",
            "criado_em",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="RESTRICT"),
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


class GrupoComercialProdutoVinculo(Base):
    """Equivalencia manual entre produtos de empresas do mesmo grupo.

    Os IDs de produto nao recebem chave estrangeira porque pertencem a tenants
    diferentes e podem se repetir. O servico sempre valida empresa, produto e
    participacao ativa antes de criar ou consultar o vinculo.
    """

    __tablename__ = "grupo_comercial_produto_vinculos"
    __table_args__ = (
        UniqueConstraint(
            "grupo_id",
            "empresa_a_id",
            "produto_a_id",
            "empresa_b_id",
            "produto_b_id",
            name="uq_grupo_comercial_produto_vinculo_par",
        ),
        Index(
            "ix_grupo_comercial_produto_vinculos_grupo_status",
            "grupo_id",
            "status",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
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


class GrupoComercialEstoqueCompartilhado(Base):
    """Autoriza uma empresa do grupo a vender o saldo de outra empresa.

    O produto e o estoque continuam pertencendo exclusivamente ao tenant de
    origem. Este registro apenas concede leitura e uso no PDV da empresa
    consumidora; ele nunca transfere saldo entre empresas.
    """

    __tablename__ = "grupo_comercial_estoques_compartilhados"
    __table_args__ = (
        UniqueConstraint(
            "grupo_id",
            "empresa_origem_id",
            "produto_origem_id",
            "empresa_consumidora_id",
            name="uq_grupo_comercial_estoque_compartilhado",
        ),
        Index(
            "ix_grupo_comercial_estoque_compartilhado_consumidora_status",
            "empresa_consumidora_id",
            "status",
        ),
        Index(
            "ix_grupo_comercial_estoque_compartilhado_origem_status",
            "empresa_origem_id",
            "status",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
        nullable=False,
    )
    empresa_origem_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    produto_origem_id = Column(
        Integer, ForeignKey("produtos.id", ondelete="RESTRICT"), nullable=False
    )
    empresa_consumidora_id = Column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    acesso_catalogo_completo = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    status = Column(String(20), nullable=False, default="ativo", server_default="ativo")
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
