"""Espécie/Raça mestre — dado de taxonomia compartilhado entre lojas do mesmo
grupo comercial. Ver Documentacao/Dominio/Plano-Camada-Geral.md, Checkpoint 1.

Prova de conceito do padrão "tabela mestre" que os próximos domínios (Produto,
Pet, Pessoa) vão repetir: escopado por grupo_id (não tenant_id — é dado do
grupo, atravessa lojas, igual GrupoComercial não herda BaseTenantModel),
`especies`/`racas` locais ganham FK opcional pra isso sem nenhuma mudança de
comportamento pra quem nunca vincular.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db import Base


class EspecieMestre(Base):
    __tablename__ = "especie_mestre"
    __table_args__ = (
        UniqueConstraint("grupo_id", "nome", name="uq_especie_mestre_grupo_nome"),
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


class RacaMestre(Base):
    __tablename__ = "raca_mestre"
    __table_args__ = (
        UniqueConstraint(
            "especie_mestre_id", "nome", name="uq_raca_mestre_especie_nome"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    especie_mestre_id = Column(
        Integer,
        ForeignKey("especie_mestre.id", ondelete="CASCADE"),
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
