"""Modelos dos orcamentos emitidos por empresas de um mesmo grupo."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class OrcamentoGrupoConfiguracao(BaseTenantModel):
    __tablename__ = "orcamento_grupo_configuracoes"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_orcamento_grupo_configuracoes_tenant"),
    )

    percentual_minimo = Column(Numeric(5, 2), nullable=False, default=10)
    percentual_maximo = Column(Numeric(5, 2), nullable=False, default=30)
    quantidade_empresas = Column(Integer, nullable=False, default=2)
    validade_dias = Column(Integer, nullable=False, default=15)
    observacoes_padrao = Column(Text, nullable=True)


class OrcamentoGrupoEmpresa(BaseTenantModel):
    __tablename__ = "orcamento_grupo_empresas"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "cliente_id",
            name="uq_orcamento_grupo_empresas_tenant_cliente",
        ),
        Index(
            "ix_orcamento_grupo_empresas_tenant_ativo",
            "tenant_id",
            "ativo",
        ),
    )

    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ativo = Column(Boolean, nullable=False, default=True)
    fixada_padrao = Column(Boolean, nullable=False, default=False)
    observacoes = Column(Text, nullable=True)

    cliente = relationship("Cliente", foreign_keys=[cliente_id])


class OrcamentoGrupo(BaseTenantModel):
    __tablename__ = "orcamentos_grupo"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "numero", name="uq_orcamentos_grupo_tenant_numero"
        ),
        Index(
            "ix_orcamentos_grupo_tenant_emissao",
            "tenant_id",
            "data_emissao",
        ),
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    numero = Column(String(40), nullable=True)
    titulo = Column(String(255), nullable=False, default="Orcamento")
    destinatario = Column(String(255), nullable=True)
    data_emissao = Column(Date, nullable=False)
    validade_dias = Column(Integer, nullable=False, default=15)
    percentual_minimo = Column(Numeric(5, 2), nullable=False)
    percentual_maximo = Column(Numeric(5, 2), nullable=False)
    observacoes = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="emitido")
    total_base = Column(Numeric(14, 2), nullable=False, default=0)

    itens = relationship(
        "OrcamentoGrupoItem",
        back_populates="orcamento",
        cascade="all, delete-orphan",
        order_by="OrcamentoGrupoItem.ordem",
    )
    cotacoes = relationship(
        "OrcamentoGrupoCotacao",
        back_populates="orcamento",
        cascade="all, delete-orphan",
        order_by="OrcamentoGrupoCotacao.ordem",
    )


class OrcamentoGrupoItem(BaseTenantModel):
    __tablename__ = "orcamento_grupo_itens"
    __table_args__ = (
        Index(
            "ix_orcamento_grupo_itens_tenant_orcamento",
            "tenant_id",
            "orcamento_id",
        ),
    )

    orcamento_id = Column(
        Integer,
        ForeignKey("orcamentos_grupo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordem = Column(Integer, nullable=False, default=0)
    descricao = Column(String(500), nullable=False)
    quantidade = Column(Numeric(12, 3), nullable=False, default=1)
    unidade = Column(String(30), nullable=True)
    preco_unitario_base = Column(Numeric(14, 2), nullable=False, default=0)
    total_base = Column(Numeric(14, 2), nullable=False, default=0)

    orcamento = relationship("OrcamentoGrupo", back_populates="itens")


class OrcamentoGrupoCotacao(BaseTenantModel):
    __tablename__ = "orcamento_grupo_cotacoes"
    __table_args__ = (
        Index(
            "ix_orcamento_grupo_cotacoes_tenant_orcamento",
            "tenant_id",
            "orcamento_id",
        ),
    )

    orcamento_id = Column(
        Integer,
        ForeignKey("orcamentos_grupo.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    empresa_grupo_id = Column(
        Integer,
        ForeignKey("orcamento_grupo_empresas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ordem = Column(Integer, nullable=False, default=0)
    emissor_principal = Column(Boolean, nullable=False, default=False)
    fixada = Column(Boolean, nullable=False, default=False)
    percentual_acrescimo = Column(Numeric(5, 2), nullable=False, default=0)
    empresa_snapshot = Column(JSON, nullable=False)
    itens_snapshot = Column(JSON, nullable=False)
    total = Column(Numeric(14, 2), nullable=False, default=0)

    orcamento = relationship("OrcamentoGrupo", back_populates="cotacoes")
    empresa_grupo = relationship(
        "OrcamentoGrupoEmpresa", foreign_keys=[empresa_grupo_id]
    )
