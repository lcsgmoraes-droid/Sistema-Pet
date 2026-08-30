"""Modelos globais do catalogo mestre de produtos.

O catalogo mestre e deliberadamente separado das tabelas ``produtos`` dos
tenants. A origem pode ser uma loja autorizada, mas nenhuma FK aponta de volta
para o cadastro operacional e nenhuma sincronizacao deste modulo altera lojas.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db import Base


class CatalogoMestreProduto(Base):
    """Registro canonico compartilhado, sem preco, estoque ou fornecedor."""

    __tablename__ = "catalogo_mestre_produtos"
    __table_args__ = (
        UniqueConstraint(
            "origem_tenant_id",
            "origem_produto_id",
            name="uq_catalogo_mestre_produtos_origem",
        ),
        CheckConstraint(
            "imagem_meta_quantidade >= 1",
            name="ck_catalogo_mestre_produtos_imagem_meta_positiva",
        ),
        CheckConstraint(
            "imagem_quantidade >= 0 AND imagem_faltantes >= 0",
            name="ck_catalogo_mestre_produtos_imagens_nao_negativas",
        ),
        CheckConstraint(
            "qualidade_percentual >= 0 AND qualidade_percentual <= 100",
            name="ck_catalogo_mestre_produtos_qualidade_intervalo",
        ),
        Index("ix_catalogo_mestre_produtos_gtin", "gtin"),
        Index(
            "ix_catalogo_mestre_produtos_fila",
            "status",
            "imagem_faltantes",
            "qualidade_percentual",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(30), nullable=False, default="em_curadoria", index=True)
    ativo = Column(Boolean, nullable=False, default=True, index=True)

    fonte_primaria = Column(String(50), nullable=False, default="tenant_produto")
    origem_tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    origem_produto_id = Column(Integer, nullable=False)
    origem_atualizado_em = Column(DateTime(timezone=True), nullable=True)
    codigo_origem = Column(String(100), nullable=True)

    nome = Column(String(500), nullable=False, index=True)
    tipo_catalogo = Column(String(30), nullable=False, default="outro", index=True)
    gtin = Column(String(14), nullable=True)
    gtin_status = Column(String(30), nullable=False, default="ausente", index=True)
    codigos_barras = Column(JSON, nullable=True)

    marca = Column(String(255), nullable=True, index=True)
    categoria = Column(String(255), nullable=True, index=True)
    departamento = Column(String(255), nullable=True, index=True)
    subcategoria = Column(String(255), nullable=True)
    descricao_curta = Column(Text, nullable=True)
    descricao_completa = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    unidade = Column(String(20), nullable=True)

    ncm = Column(String(10), nullable=True, index=True)
    cest = Column(String(10), nullable=True, index=True)
    origem_mercadoria = Column(String(2), nullable=True)
    dados_fiscais_referencia = Column(JSON, nullable=True)
    dados_fisicos = Column(JSON, nullable=True)
    dados_racao = Column(JSON, nullable=True)

    registro_mapa = Column(String(120), nullable=True, index=True)
    principio_ativo = Column(Text, nullable=True)
    fabricante = Column(String(255), nullable=True)
    forma_farmaceutica = Column(String(150), nullable=True)
    especies_indicadas = Column(JSON, nullable=True)
    bula_url = Column(String(1000), nullable=True)
    bula_conteudo = Column(JSON, nullable=True)
    posologia = Column(JSON, nullable=True)
    conteudo_veterinario_status = Column(
        String(30), nullable=False, default="nao_verificado", index=True
    )

    imagem_quantidade = Column(Integer, nullable=False, default=0)
    imagem_meta_quantidade = Column(Integer, nullable=False, default=5)
    imagem_faltantes = Column(Integer, nullable=False, default=5, index=True)
    qualidade_percentual = Column(Float, nullable=False, default=0)
    lacunas = Column(JSON, nullable=True)

    proveniencia = Column(JSON, nullable=False)
    snapshot_origem = Column(JSON, nullable=False)
    snapshot_origem_hash = Column(String(64), nullable=False, index=True)
    ultima_sincronizacao_em = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    imagens = relationship(
        "CatalogoMestreImagem",
        back_populates="produto",
        cascade="all, delete-orphan",
    )
    pendencias = relationship(
        "CatalogoMestrePendencia",
        back_populates="produto",
        cascade="all, delete-orphan",
    )


class CatalogoMestreImagem(Base):
    """Imagem com proveniencia, direitos de uso e revisao independentes."""

    __tablename__ = "catalogo_mestre_imagens"
    __table_args__ = (
        UniqueConstraint(
            "produto_id",
            "url_origem",
            name="uq_catalogo_mestre_imagens_produto_url_origem",
        ),
        CheckConstraint("ordem >= 0", name="ck_catalogo_mestre_imagens_ordem"),
        Index(
            "ix_catalogo_mestre_imagens_revisao",
            "status_revisao",
            "direitos_uso_status",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    produto_id = Column(
        Integer,
        ForeignKey("catalogo_mestre_produtos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_origem = Column(String(40), nullable=False)
    url_origem = Column(String(1000), nullable=True)
    arquivo_url = Column(String(1000), nullable=True)
    hash_arquivo = Column(String(64), nullable=True, index=True)
    ordem = Column(Integer, nullable=False, default=0)
    e_principal = Column(Boolean, nullable=False, default=False)
    gerada_por_ia = Column(Boolean, nullable=False, default=False, index=True)
    modelo_geracao = Column(String(120), nullable=True)
    versao_prompt = Column(String(120), nullable=True)
    direitos_uso_status = Column(
        String(30), nullable=False, default="nao_verificado", index=True
    )
    status_revisao = Column(String(30), nullable=False, default="pendente", index=True)
    revisada_por_id = Column(Integer, nullable=True)
    revisada_em = Column(DateTime(timezone=True), nullable=True)
    largura = Column(Integer, nullable=True)
    altura = Column(Integer, nullable=True)
    tamanho_bytes = Column(Integer, nullable=True)
    metadados = Column(JSON, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    produto = relationship("CatalogoMestreProduto", back_populates="imagens")


class CatalogoMestreProdutoCandidato(Base):
    """EAN ainda sem identidade oficial suficiente para virar produto mestre."""

    __tablename__ = "catalogo_mestre_produto_candidatos"
    __table_args__ = (
        UniqueConstraint("gtin", name="uq_cat_mestre_candidato_gtin"),
        CheckConstraint(
            "decisao_escopo_sugerida IN "
            "('provavel_elegivel', 'provavel_fora_escopo', 'revisao_necessaria')",
            name="ck_cat_mestre_cand_escopo",
        ),
        Index("ix_cat_mestre_cand_status", "status", "decisao_escopo_sugerida"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    gtin = Column(String(14), nullable=False)
    nome_sugerido = Column(String(500), nullable=False)
    tipo_catalogo_sugerido = Column(String(30), nullable=True, index=True)
    decisao_escopo_sugerida = Column(
        String(30), nullable=False, default="revisao_necessaria"
    )
    motivo_sugestao = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="pendente")
    produto_mestre_id = Column(
        Integer,
        ForeignKey("catalogo_mestre_produtos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fonte_identidade_status = Column(
        String(40), nullable=False, default="nao_verificada"
    )
    metadados = Column(JSON, nullable=True)
    revisada_por_id = Column(Integer, nullable=True)
    revisada_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    produto_mestre = relationship("CatalogoMestreProduto")
    evidencias = relationship(
        "CatalogoMestreCandidatoEvidencia",
        back_populates="candidato",
        cascade="all, delete-orphan",
    )


class CatalogoMestreCandidatoEvidencia(Base):
    """Arquivo privado que ajuda a identificar um candidato, sem publica-lo."""

    __tablename__ = "catalogo_mestre_candidato_evidencias"
    __table_args__ = (
        UniqueConstraint(
            "candidato_id",
            "hash_arquivo",
            name="uq_cat_mestre_cand_evid_hash",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidato_id = Column(
        Integer,
        ForeignKey("catalogo_mestre_produto_candidatos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_ref = Column(String(300), nullable=False)
    fonte_relatorio = Column(String(100), nullable=True)
    nome_arquivo_original = Column(String(500), nullable=False)
    hash_arquivo = Column(String(64), nullable=False, index=True)
    staging_path = Column(String(1000), nullable=False)
    formato = Column(String(20), nullable=False)
    largura = Column(Integer, nullable=True)
    altura = Column(Integer, nullable=True)
    tamanho_bytes = Column(Integer, nullable=True)
    direitos_uso_status = Column(
        String(30), nullable=False, default="nao_verificado", index=True
    )
    metadados = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    candidato = relationship(
        "CatalogoMestreProdutoCandidato", back_populates="evidencias"
    )


class CatalogoMestrePendencia(Base):
    """Fila continua de enriquecimento; uma posicao representa uma lacuna."""

    __tablename__ = "catalogo_mestre_pendencias"
    __table_args__ = (
        UniqueConstraint(
            "produto_id",
            "tipo",
            "posicao_alvo",
            name="uq_catalogo_mestre_pendencias_produto_tipo_posicao",
        ),
        CheckConstraint(
            "posicao_alvo >= 0",
            name="ck_catalogo_mestre_pendencias_posicao_nao_negativa",
        ),
        Index(
            "ix_catalogo_mestre_pendencias_fila",
            "status",
            "prioridade",
            "tipo",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    produto_id = Column(
        Integer,
        ForeignKey("catalogo_mestre_produtos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo = Column(String(50), nullable=False, index=True)
    posicao_alvo = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="pendente", index=True)
    prioridade = Column(Integer, nullable=False, default=100, index=True)
    origem_preferida = Column(String(50), nullable=True)
    detalhes = Column(JSON, nullable=True)
    tentativas = Column(Integer, nullable=False, default=0)
    proxima_tentativa_em = Column(DateTime(timezone=True), nullable=True, index=True)
    reservada_por = Column(String(120), nullable=True, index=True)
    reserva_expira_em = Column(DateTime(timezone=True), nullable=True, index=True)
    ultima_execucao_em = Column(DateTime(timezone=True), nullable=True, index=True)
    ultimo_erro = Column(Text, nullable=True)
    resolvida_em = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    produto = relationship("CatalogoMestreProduto", back_populates="pendencias")


class CatalogoMestreEnriquecimentoExecucao(Base):
    """Auditoria persistente de cada tentativa feita pelo robo de enriquecimento."""

    __tablename__ = "catalogo_mestre_enriquecimento_execucoes"
    __table_args__ = (
        Index(
            "ix_catalogo_mestre_enriquecimento_execucoes_dia",
            "iniciada_em",
            "tipo",
        ),
        Index(
            "ix_catalogo_mestre_enriquecimento_execucoes_status",
            "status",
            "iniciada_em",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    pendencia_id = Column(
        Integer,
        ForeignKey("catalogo_mestre_pendencias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    produto_id = Column(
        Integer,
        ForeignKey("catalogo_mestre_produtos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tipo = Column(String(50), nullable=False, index=True)
    provedor = Column(String(50), nullable=False)
    modelo = Column(String(120), nullable=False)
    versao_prompt = Column(String(120), nullable=False)
    worker_id = Column(String(120), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="processando")
    erro = Column(Text, nullable=True)
    metadados = Column(JSON, nullable=True)
    iniciada_em = Column(DateTime(timezone=True), nullable=False)
    concluida_em = Column(DateTime(timezone=True), nullable=True)


class CatalogoMestreSincronizacao(Base):
    """Auditoria de cada carga aplicada ao catalogo mestre."""

    __tablename__ = "catalogo_mestre_sincronizacoes"
    __table_args__ = (
        Index(
            "ix_catalogo_mestre_sincronizacoes_origem_inicio",
            "origem_tenant_id",
            "iniciada_em",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    origem_tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    origem_identificador = Column(String(255), nullable=True)
    modo = Column(String(20), nullable=False, default="apply")
    status = Column(String(30), nullable=False, default="executando", index=True)
    imagem_meta_quantidade = Column(Integer, nullable=False, default=5)
    resumo = Column(JSON, nullable=True)
    erro = Column(Text, nullable=True)
    iniciada_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    concluida_em = Column(DateTime(timezone=True), nullable=True)
