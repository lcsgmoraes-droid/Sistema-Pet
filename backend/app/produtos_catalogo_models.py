# -*- coding: utf-8 -*-
"""Modelos centrais do catalogo de produtos."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base_models import BaseTenantModel
from .services.product_image_storage import build_product_thumbnail_url


class Categoria(BaseTenantModel):
    """Categorias de produtos com hierarquia"""

    __tablename__ = "categorias"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    categoria_pai_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=True)
    descricao = Column(Text, nullable=True)
    icone = Column(String(50), nullable=True)
    cor = Column(String(7), nullable=True)  # Hex color
    ordem = Column(Integer, default=0)

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    categoria_pai = relationship("Categoria", remote_side=[id], backref="subcategorias")
    departamento = relationship("Departamento", back_populates="categorias")
    produtos = relationship("Produto", back_populates="categoria")
    user = relationship("User")


class Marca(BaseTenantModel):
    """Marcas de produtos"""

    __tablename__ = "marcas"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    logo = Column(String(255), nullable=True)
    site = Column(String(255), nullable=True)

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    produtos = relationship("Produto", back_populates="marca")
    user = relationship("User")


class Departamento(BaseTenantModel):
    """Departamentos/setores de produtos"""

    __tablename__ = "departamentos"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    produtos = relationship("Produto", back_populates="departamento")
    categorias = relationship("Categoria", back_populates="departamento")
    user = relationship("User")


class Produto(BaseTenantModel):
    """Produto completo com todos os campos"""

    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True)

    # Informações Básicas
    codigo = Column(String(50), nullable=False)  # SKU
    nome = Column(String(200), nullable=False)
    tipo = Column(String(20), default="produto")  # produto, servico, produto_servico
    situacao = Column(Boolean, default=True)  # ativo/inativo

    # ========== SPRINT 2: PRODUTOS COM VARIA��O ==========
    # tipo_produto: Define a estrutura do produto
    # - SIMPLES: Produto tradicional (padr�o)
    # - PAI: Produto agrupador (n�o vend�vel, sem pre�o/estoque)
    # - VARIACAO: Produto filho de um PAI (vend�vel, com pre�o/estoque)
    # - KIT: Produto composto por outros produtos
    tipo_produto = Column(
        String(20), default="SIMPLES", nullable=False
    )  # SIMPLES, PAI, VARIACAO, KIT
    produto_pai_id = Column(
        Integer, ForeignKey("produtos.id"), nullable=True
    )  # FK para produto PAI

    # Flags para controle de varia��o (Sprint 2 - Nova Estrutura)
    is_parent = Column(
        Boolean, default=False, nullable=False
    )  # Indica se � produto pai (agrupador)
    is_sellable = Column(
        Boolean, default=True, nullable=False
    )  # Indica se pode ser vendido

    # ========== SPRINT 2: ATRIBUTOS DE VARIA��O ==========
    variation_attributes = Column(
        JSON, nullable=True
    )  # Ex: {"cor": "azul", "tamanho": "G"}
    variation_signature = Column(
        String(255), nullable=True, index=True
    )  # Ex: "cor:azul|tamanho:G"

    # ========== SPRINT 4: PRODUTOS KIT ==========
    # tipo_kit: Define como o custo/estoque do KIT � tratado
    # - VIRTUAL: Custo = soma dos componentes, estoque = menor dispon�vel dos componentes
    # - FISICO: Custo pr�prio, estoque pr�prio (KIT j� montado/pr�-embalado)
    tipo_kit = Column(
        String(20), nullable=True
    )  # VIRTUAL, FISICO (somente quando produto possui composicao)

    descricao_curta = Column(Text, nullable=True)
    descricao_completa = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array

    # Código de Barras
    codigo_barras = Column(
        String(20), nullable=True
    )  # Aumentado para suportar EAN-14 e outros formatos
    codigos_barras_alternativos = Column(Text, nullable=True)  # JSON array

    # Relacionamentos (FKs)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)
    subcategoria = Column(String(100), nullable=True)  # Subcategoria (campo texto)
    marca_id = Column(Integer, ForeignKey("marcas.id"), nullable=True)
    fornecedor_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=True)

    # Preços
    preco_custo = Column(Float, default=0)
    preco_venda = Column(Float, nullable=True, default=0)  # Nullable para produtos PAI
    preco_promocional = Column(Float, nullable=True)
    promocao_inicio = Column(DateTime, nullable=True)
    promocao_fim = Column(DateTime, nullable=True)
    promocao_ativa = Column(Boolean, default=False)

    # Preços por canal — se NULL usa o preco_venda padrão
    preco_ecommerce = Column(Float, nullable=True)
    preco_ecommerce_promo = Column(Float, nullable=True)
    preco_ecommerce_promo_inicio = Column(DateTime(timezone=True), nullable=True)
    preco_ecommerce_promo_fim = Column(DateTime(timezone=True), nullable=True)
    preco_app = Column(Float, nullable=True)
    preco_app_promo = Column(Float, nullable=True)
    preco_app_promo_inicio = Column(DateTime(timezone=True), nullable=True)
    preco_app_promo_fim = Column(DateTime(timezone=True), nullable=True)
    anunciar_ecommerce = Column(Boolean, nullable=False, default=True)
    anunciar_app = Column(Boolean, nullable=False, default=True)

    # Estoque
    estoque_atual = Column(Float, default=0)
    estoque_minimo = Column(Float, default=0)
    estoque_maximo = Column(Float, default=0)
    estoque_fisico = Column(Float, default=0)
    estoque_ecommerce = Column(Float, default=0)
    localizacao = Column(String(50), nullable=True)
    crossdocking_dias = Column(Integer, default=0)
    controle_lote = Column(Boolean, default=False)

    # Unidade e Condição
    unidade = Column(String(10), default="UN")
    condicao = Column(String(20), default="novo")  # novo, usado, recondicionado
    e_granel = Column(
        Boolean, default=False, nullable=False
    )  # Produto fisico em kg derivado de uma racao/pacote pai
    participa_sugestao_compra = Column(Boolean, default=True, nullable=False)

    # Características Físicas
    peso_liquido = Column(Float, nullable=True)
    peso_bruto = Column(Float, nullable=True)
    largura = Column(Float, nullable=True)
    altura = Column(Float, nullable=True)
    profundidade = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)  # calculado
    itens_por_caixa = Column(Integer, nullable=True)
    frete_gratis = Column(Boolean, default=False)
    producao = Column(String(20), nullable=True)  # propria, terceiros

    # Fiscal
    ncm = Column(String(8), nullable=True)
    cest = Column(String(7), nullable=True)
    gtin_ean = Column(String(20), nullable=True)
    gtin_ean_tributario = Column(String(20), nullable=True)
    origem = Column(String(1), nullable=True)  # 0-8
    perfil_tributario = Column(String(50), nullable=True)
    forma_aquisicao = Column(String(50), nullable=True)
    tipo_item = Column(String(50), nullable=True)
    percentual_tributos = Column(Float, nullable=True)

    # ICMS
    icms_base_retencao = Column(Float, nullable=True)
    icms_valor_retencao = Column(Float, nullable=True)
    icms_valor_proprio = Column(Float, nullable=True)

    # IPI
    ipi_codigo_excecao = Column(String(20), nullable=True)

    # PIS/COFINS
    pis_valor_fixo = Column(Float, nullable=True)
    cofins_valor_fixo = Column(Float, nullable=True)

    # CFOP e Al�quotas (campos adicionais para NF-e)
    cfop = Column(String(10), nullable=True)
    aliquota_icms = Column(Float, nullable=True)
    aliquota_pis = Column(Float, nullable=True)
    aliquota_cofins = Column(Float, nullable=True)

    # Informações Adicionais
    informacoes_adicionais_nf = Column(Text, nullable=True)

    # Comissão e Desconto
    comissao_padrao = Column(Float, default=0)
    limite_desconto = Column(Float, default=0)

    # Validade
    data_validade = Column(DateTime, nullable=True)

    # ========== RECORR�NCIA E COMPATIBILIDADE (NOVO) ==========
    # Sistema de lembretes para produtos recorrentes (medicamentos, ra��es, etc)
    tem_recorrencia = Column(Boolean, default=False)  # Indica se � produto recorrente
    tipo_recorrencia = Column(
        String(20), nullable=True
    )  # daily, weekly, monthly, yearly
    intervalo_dias = Column(
        Integer, nullable=True
    )  # N�mero de dias entre doses/compras
    numero_doses = Column(
        Integer, nullable=True
    )  # N�mero total de doses no ciclo (ex: 3 para vacina V8)
    observacoes_recorrencia = Column(
        Text, nullable=True
    )  # Ex: "Nexgard para c�es 4-10kg, repetir a cada 30 dias"

    # ========== RECORR�NCIA E COMPATIBILIDADE (NOVO) ==========
    # Sistema de lembretes para produtos recorrentes (medicamentos, ra��es, etc)
    tem_recorrencia = Column(Boolean, default=False)  # Indica se � produto recorrente
    tipo_recorrencia = Column(
        String(20), nullable=True
    )  # daily, weekly, monthly, yearly
    intervalo_dias = Column(
        Integer, nullable=True
    )  # N�mero de dias entre doses/compras
    numero_doses = Column(
        Integer, nullable=True
    )  # N�mero total de doses no ciclo (ex: 3 para vacina V8)
    observacoes_recorrencia = Column(
        Text, nullable=True
    )  # Ex: "Nexgard para c�es 4-10kg, repetir a cada 30 dias"

    # Compatibilidade de esp�cie
    especie_compativel = Column(
        String(50), nullable=True
    )  # dog, cat, both (para ra��es, medicamentos)

    # ========== RA��O - CALCULADORA (FASE 2) ==========
    classificacao_racao = Column(
        String(50), nullable=True
    )  # super_premium, premium, especial, standard
    peso_embalagem = Column(Float, nullable=True)  # Peso da embalagem em kg
    tabela_nutricional = Column(
        Text, nullable=True
    )  # JSON: {"proteina": 28, "gordura": 15, "fibra": 3, "umidade": 10}
    categoria_racao = Column(
        String(50), nullable=True
    )  # filhote, adulto, senior, gestante, etc
    especies_indicadas = Column(
        String(100), nullable=True
    )  # dog, cat, both (espec�fico para ra��es)
    tabela_consumo = Column(
        Text, nullable=True
    )  # JSON com tabela de consumo da embalagem (peso x idade x quantidade di�ria)

    # ========== CLASSIFICA��O INTELIGENTE DE RA��ES (FASE 3 - IA) ==========
    # Arrays para suportar m�ltiplas classifica��es (ex: "todas as ra�as", "todos os portes")
    porte_animal = Column(
        JSONB, nullable=True
    )  # ["Pequeno", "M�dio", "Grande", "Gigante", "Todos"]
    fase_publico = Column(
        JSONB, nullable=True
    )  # ["Filhote", "Adulto", "Senior", "Gestante", "Todos"]
    tipo_tratamento = Column(
        JSONB, nullable=True
    )  # ["Obesidade", "Alergia", "Sens�vel", "Digestivo", "Urin�rio", "Renal", "Hipoalerg�nico", "Light"]
    sabor_proteina = Column(
        String(100), nullable=True
    )  # Frango, Carne, Peixe, Cordeiro, Soja, Mix, etc.
    auto_classificar_nome = Column(
        Boolean, default=True, nullable=False
    )  # Ativa auto-classifica��o via IA
    # ========== OPÇÕES DE RAÇÃO - SISTEMA DINÂMICO (FOREIGN KEYS) ==========
    # Relacionamentos com tabelas de opções dinâmicas configuradas pelo usuário
    # DESABILITADO TEMPORARIAMENTE: Tabelas não existem ainda
    # linha_racao_id = Column(Integer, ForeignKey('linhas_racao.id', ondelete='SET NULL'), nullable=True)
    # porte_animal_id = Column(Integer, ForeignKey('portes_animal.id', ondelete='SET NULL'), nullable=True)
    # fase_publico_id = Column(Integer, ForeignKey('fases_publico.id', ondelete='SET NULL'), nullable=True)
    # tipo_tratamento_id = Column(Integer, ForeignKey('tipos_tratamento.id', ondelete='SET NULL'), nullable=True)
    # sabor_proteina_id = Column(Integer, ForeignKey('sabores_proteina.id', ondelete='SET NULL'), nullable=True)
    # apresentacao_peso_id = Column(Integer, ForeignKey('apresentacoes_peso.id', ondelete='SET NULL'), nullable=True)
    linha_racao_id = Column(Integer, nullable=True)
    porte_animal_id = Column(Integer, nullable=True)
    fase_publico_id = Column(Integer, nullable=True)
    tipo_tratamento_id = Column(Integer, nullable=True)
    sabor_proteina_id = Column(Integer, nullable=True)
    apresentacao_peso_id = Column(Integer, nullable=True)

    # Imagem Principal
    imagem_principal = Column(String(255), nullable=True)

    # Auditoria
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete - data de exclus�o

    # ========== SISTEMA DE PREDECESSOR/SUCESSOR ==========
    # Permite vincular produtos que substituem outros, mantendo histórico consolidado
    # Ex: Ração 350g → Ração 300g (mudança de embalagem)
    produto_predecessor_id = Column(
        Integer, ForeignKey("produtos.id"), nullable=True
    )  # Produto que este substitui
    data_descontinuacao = Column(
        DateTime, nullable=True
    )  # Quando foi substituído por outro
    motivo_descontinuacao = Column(
        String(255), nullable=True
    )  # Ex: Mudança de embalagem, Reformulação

    # Relationships
    categoria = relationship("Categoria", back_populates="produtos")
    marca = relationship("Marca", back_populates="produtos")
    departamento = relationship("Departamento", back_populates="produtos")
    fornecedor = relationship("Cliente", foreign_keys=[fornecedor_id])
    imagens = relationship(
        "ProdutoImagem", back_populates="produto", cascade="all, delete-orphan"
    )
    lotes = relationship(
        "ProdutoLote", back_populates="produto", cascade="all, delete-orphan"
    )
    fornecedores_alternativos = relationship(
        "ProdutoFornecedor", back_populates="produto", cascade="all, delete-orphan"
    )
    listas_preco = relationship(
        "ProdutoListaPreco", back_populates="produto", cascade="all, delete-orphan"
    )
    movimentacoes = relationship("EstoqueMovimentacao", back_populates="produto")
    bling_sync = relationship(
        "ProdutoBlingSync", back_populates="produto", uselist=False
    )
    bling_sync_queue_items = relationship(
        "ProdutoBlingSyncQueue", back_populates="produto"
    )
    user = relationship("User")

    # ========== PREDECESSOR/SUCESSOR ==========
    # Relacionamento para cadeia de evolução de produtos
    predecessor = relationship(
        "Produto",
        remote_side=[id],
        foreign_keys=[produto_predecessor_id],
        backref="sucessores",
    )
    # Acesso: produto.predecessor (produto anterior)
    # Acesso: produto.sucessores (lista de produtos que substituem este)

    # ========== SPRINT 2: VARIA��ES ==========
    # Relacionamento pai/filhos para produtos com varia��o
    produto_pai = relationship(
        "Produto", remote_side=[id], foreign_keys=[produto_pai_id], backref="variacoes"
    )

    @property
    def eh_racao(self) -> bool:
        tipo = (self.tipo or "").strip().lower()
        classificacao = (self.classificacao_racao or "").strip().lower()

        if tipo in {"ração", "racao"}:
            return True

        if getattr(self, "linha_racao_id", None):
            return True

        if classificacao in {
            "sim",
            "standard",
            "premium",
            "super_premium",
            "especial",
            "terapeutica",
        }:
            return True

        if self.peso_embalagem and float(self.peso_embalagem or 0) > 0:
            return True

        return False

    # Acesso via: produto_pai.variacoes (lista de varia��es)

    # ? DESABILITADO: ProductVariation n�o existe mais
    # variations = relationship(
    #     "ProductVariation",
    #     back_populates="parent",
    #     cascade="all, delete-orphan",
    #     passive_deletes=True,
    # )

    # Índices adicionais
    __table_args__ = (
        Index(
            "ux_produtos_tenant_codigo_lower",
            "tenant_id",
            func.lower(func.trim(codigo)),
            unique=True,
            postgresql_where=(codigo.isnot(None) & (func.trim(codigo) != "")),
        ),
        Index("idx_produtos_categoria", "categoria_id"),
        Index("idx_produtos_marca", "marca_id"),
        Index("idx_produtos_user", "user_id"),
        Index(
            "idx_produtos_variation_signature", "tenant_id", "variation_signature"
        ),  # Sprint 2: Varia��es        {'extend_existing': True}
    )

    @property
    def markup_percentual(self):
        """Calcula o markup em %"""
        if self.preco_custo and self.preco_custo > 0:
            return ((self.preco_venda - self.preco_custo) / self.preco_custo) * 100
        return 0

    @property
    def margem_lucro(self):
        """Calcula a margem de lucro em %"""
        if self.preco_venda and self.preco_venda > 0:
            return ((self.preco_venda - self.preco_custo) / self.preco_venda) * 100
        return 0

    @property
    def validade_proxima(self):
        """Retorna a validade mais próxima dos lotes ativos"""
        if not self.controle_lote or not self.lotes:
            return self.data_validade

        lotes_ativos = [
            lote
            for lote in self.lotes
            if lote.status == "ativo" and lote.quantidade_disponivel > 0
        ]
        if not lotes_ativos:
            return None

        return min(lote.data_validade for lote in lotes_ativos)

    @property
    def imagem_principal_thumbnail(self):
        return build_product_thumbnail_url(self.imagem_principal)
