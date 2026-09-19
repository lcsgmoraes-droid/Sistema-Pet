"""Produto mestre — Checkpoint 2 da camada geral do grupo comercial.

Mesmo padrão do Checkpoint 1 (ver especie_raca_mestre_models.py): tabelas
escopadas por grupo_id, guardam só identidade (nome/descrição/fotos/ficha
técnica/GTIN/taxonomia); preço, estoque e disponibilidade continuam 100%
locais em cada loja, sem exceção — ver Documentacao/Dominio/
Plano-Camada-Geral.md, Checkpoint 2.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db import Base


class CategoriaMestre(Base):
    __tablename__ = "categoria_mestre"
    __table_args__ = (
        UniqueConstraint("grupo_id", "nome", name="uq_categoria_mestre_grupo_nome"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome = Column(String(100), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
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


class MarcaMestre(Base):
    __tablename__ = "marca_mestre"
    __table_args__ = (
        UniqueConstraint("grupo_id", "nome", name="uq_marca_mestre_grupo_nome"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome = Column(String(100), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
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


class DepartamentoMestre(Base):
    __tablename__ = "departamento_mestre"
    __table_args__ = (
        UniqueConstraint(
            "grupo_id", "nome", name="uq_departamento_mestre_grupo_nome"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome = Column(String(100), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
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


class ProdutoMestre(Base):
    """Identidade do produto, compartilhada entre lojas do grupo.

    Preço, estoque, disponibilidade, fornecedor e tudo que é operacional
    continuam só em `Produto` (local, por loja) — aqui só o que é igual em
    qualquer loja: nome, descrição, ficha técnica, GTIN, taxonomia e a
    dimensão/peso físico do item.
    """

    __tablename__ = "produto_mestre"
    __table_args__ = (
        UniqueConstraint("grupo_id", "nome", name="uq_produto_mestre_grupo_nome"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome = Column(String(200), nullable=False)
    descricao_curta = Column(Text, nullable=True)
    descricao_completa = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array, mesmo formato do Produto local
    imagem_principal = Column(String(255), nullable=True)

    categoria_mestre_id = Column(
        Integer, ForeignKey("categoria_mestre.id", ondelete="SET NULL"), nullable=True
    )
    marca_mestre_id = Column(
        Integer, ForeignKey("marca_mestre.id", ondelete="SET NULL"), nullable=True
    )
    departamento_mestre_id = Column(
        Integer,
        ForeignKey("departamento_mestre.id", ondelete="SET NULL"),
        nullable=True,
    )

    ncm = Column(String(8), nullable=True)
    cest = Column(String(7), nullable=True)
    gtin_ean = Column(String(20), nullable=True, index=True)
    gtin_ean_tributario = Column(String(20), nullable=True)

    unidade = Column(String(10), nullable=True)
    peso_liquido = Column(Float, nullable=True)
    peso_bruto = Column(Float, nullable=True)
    largura = Column(Float, nullable=True)
    altura = Column(Float, nullable=True)
    profundidade = Column(Float, nullable=True)
    itens_por_caixa = Column(Integer, nullable=True)

    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
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
