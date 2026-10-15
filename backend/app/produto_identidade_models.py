# -*- coding: utf-8 -*-
"""Identidade de produto compartilhada entre lojas do grupo comercial ("fase D").

Substitui o `ProdutoMestre` (copia unica, opt-in, nunca mais sincronizada) pelo
mesmo padrao ja usado em `Cliente`/`Pet`: `origem_tenant_id` + RLS de grupo,
leitura/escrita abertas pra qualquer loja ativa do mesmo grupo ativo, sem vinculo
manual. Diferenca de Cliente/Pet: aqui so os campos inerentes do produto (nome,
codigo de barras/GTIN, peso, dimensoes, foto, descricao, classificacao de racao)
vivem nesta tabela — preco, estoque, lote, fornecedor continuam 100% em `Produto`,
por loja, sem excecao. `produtos.produto_identidade_id` aponta pra ca; os campos
inerentes de `Produto` continuam existindo tambem, como espelho sincronizado (ver
`app/services/produto_identidade_service.py`), pra nao exigir join em nenhum dos
consumidores que ja leem `Produto.nome`/`Produto.codigo_barras` etc. direto.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import validates
from sqlalchemy.sql import func

from .base_models import BaseTenantModel, TenantScoped
from .db import Base


class ProdutoIdentidade(BaseTenantModel):
    """Dados do produto que independem da loja — fonte da verdade compartilhada."""

    __tablename__ = "produto_identidades"

    # Loja que criou esta identidade. Imutavel apos definida, mesmo padrao ja
    # usado em Produto/Cliente/Pet — nunca e a chave de permissao (isso e
    # resolvido dinamicamente via grupo_comercial_membros em app/tenancy/filters.py),
    # so registra a origem.
    origem_tenant_id = Column(PgUUID(as_uuid=True), nullable=True, index=True)

    @validates("origem_tenant_id")
    def _origem_imutavel(self, key, valor):
        atual = self.__dict__.get("origem_tenant_id")
        if atual is not None and valor != atual:
            raise ValueError(
                "A loja de origem da identidade e definida na criacao e nao pode ser alterada."
            )
        return valor

    nome = Column(String(200), nullable=False)
    descricao_curta = Column(Text, nullable=True)
    descricao_completa = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array, mesmo formato do Produto local

    codigo_barras = Column(String(20), nullable=True)
    codigos_barras_alternativos = Column(Text, nullable=True)  # JSON array
    gtin_ean = Column(String(20), nullable=True)
    gtin_ean_tributario = Column(String(20), nullable=True)

    # Chave normalizada de correspondencia automatica: codigo_barras OU (na
    # falta dele) gtin_ean, nunca gtin_ean_tributario (GTIN da unidade
    # tributaria pode legitimamente diferir do GTIN comercial do mesmo item —
    # misturar os dois arrisca falso-positivo entre caixa e unidade). Calculada
    # em Python por app/services/produto_identidade_service.py, nao via coluna
    # gerada, pra regra de normalizacao poder evoluir sem migration.
    chave_matching = Column(String(20), nullable=True, index=True)

    unidade = Column(String(10), nullable=True)
    condicao = Column(String(20), nullable=True)  # novo, usado, recondicionado
    e_granel = Column(Boolean, nullable=False, default=False)
    producao = Column(String(20), nullable=True)  # propria, terceiros

    peso_liquido = Column(Float, nullable=True)
    peso_bruto = Column(Float, nullable=True)
    largura = Column(Float, nullable=True)
    altura = Column(Float, nullable=True)
    profundidade = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    itens_por_caixa = Column(Integer, nullable=True)

    imagem_principal = Column(String(255), nullable=True)

    especie_compativel = Column(String(50), nullable=True)  # dog, cat, both

    # Identidade de racao — classificacao do item em si, nao da operacao da loja.
    classificacao_racao = Column(String(50), nullable=True)
    peso_embalagem = Column(Float, nullable=True)
    tabela_nutricional = Column(Text, nullable=True)  # JSON
    categoria_racao = Column(String(50), nullable=True)
    especies_indicadas = Column(String(100), nullable=True)
    tabela_consumo = Column(Text, nullable=True)  # JSON
    porte_animal = Column(JSONB, nullable=True)
    fase_publico = Column(JSONB, nullable=True)
    tipo_tratamento = Column(JSONB, nullable=True)
    sabor_proteina = Column(String(100), nullable=True)
    auto_classificar_nome = Column(Boolean, nullable=False, default=True)


class ProdutoIdentidadeHistoricoAlteracao(TenantScoped, Base):
    __tablename__ = "produto_identidades_historico_alteracoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    produto_identidade_id = Column(
        Integer,
        ForeignKey("produto_identidades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    campo = Column(String(100), nullable=False)
    valor_anterior = Column(Text, nullable=True)
    valor_novo = Column(Text, nullable=True)
    alterado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProdutoIdentidadeConflito(Base):
    """Correspondencias ambiguas (2+ identidades batendo na mesma chave) — nunca
    resolvidas sozinhas, ficam aqui ate revisao manual."""

    __tablename__ = "produto_identidade_conflitos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chave_matching = Column(String(20), nullable=False)
    # Lista de {"tenant_id": "...", "produto_id": N} envolvidos no conflito.
    produto_ids = Column(JSON, nullable=False)
    detectado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolvido = Column(Boolean, nullable=False, default=False, server_default="false")
    resolvido_por_usuario_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolvido_em = Column(DateTime(timezone=True), nullable=True)


class ProdutoIdentidadeBackfillRun(Base):
    """Registro de cada execucao da varredura de reconciliacao
    (backend/scripts/backfill_produto_identidades.py) — auditoria de cobertura,
    nunca usado pra logica de negocio."""

    __tablename__ = "produto_identidade_backfill_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(
        Integer,
        ForeignKey("grupos_comerciais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    executado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    dry_run = Column(Boolean, nullable=False, default=True, server_default="true")
    total_produtos_ativos = Column(Integer, nullable=False, default=0, server_default="0")
    total_com_gtin = Column(Integer, nullable=False, default=0, server_default="0")
    total_identidades_criadas = Column(Integer, nullable=False, default=0, server_default="0")
    total_vinculados = Column(Integer, nullable=False, default=0, server_default="0")
    total_sem_gtin = Column(Integer, nullable=False, default=0, server_default="0")
    total_conflitos = Column(Integer, nullable=False, default=0, server_default="0")
