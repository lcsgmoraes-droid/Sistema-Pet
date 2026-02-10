# -*- coding: utf-8 -*-
"""
Models para o módulo de Produtos
Sistema completo com categorias, marcas, lotes e FIFO
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base
from .base_models import BaseTenantModel
from .models import User, Cliente  # Importar models existentes


class Categoria(BaseTenantModel):
    """Categorias de produtos com hierarquia"""
    __tablename__ = "categorias"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    categoria_pai_id = Column(Integer, ForeignKey('categorias.id'), nullable=True)
    descricao = Column(Text, nullable=True)
    icone = Column(String(50), nullable=True)
    cor = Column(String(7), nullable=True)  # Hex color
    ordem = Column(Integer, default=0)
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    categoria_pai = relationship("Categoria", remote_side=[id], backref="subcategorias")
    produtos = relationship("Produto", back_populates="categoria")
    user = relationship("User")


class Marca(BaseTenantModel):
    """Marcas de produtos"""
    __tablename__ = "marcas"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    logo = Column(String(255), nullable=True)
    site = Column(String(255), nullable=True)
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    produtos = relationship("Produto", back_populates="marca")
    user = relationship("User")


class Departamento(BaseTenantModel):
    """Departamentos/setores de produtos"""
    __tablename__ = "departamentos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    produtos = relationship("Produto", back_populates="departamento")
    user = relationship("User")


class Produto(BaseTenantModel):
    """Produto completo com todos os campos"""
    __tablename__ = "produtos"
    
    id = Column(Integer, primary_key=True)
    
    # Informações Básicas
    codigo = Column(String(50), unique=True, nullable=False)  # SKU
    nome = Column(String(200), nullable=False)
    tipo = Column(String(20), default='produto')  # produto, servico, produto_servico
    situacao = Column(Boolean, default=True)  # ativo/inativo
    
    # ========== SPRINT 2: PRODUTOS COM VARIA��O ==========
    # tipo_produto: Define a estrutura do produto
    # - SIMPLES: Produto tradicional (padr�o)
    # - PAI: Produto agrupador (n�o vend�vel, sem pre�o/estoque)
    # - VARIACAO: Produto filho de um PAI (vend�vel, com pre�o/estoque)
    # - KIT: Produto composto por outros produtos
    tipo_produto = Column(String(20), default='SIMPLES', nullable=False)  # SIMPLES, PAI, VARIACAO, KIT
    produto_pai_id = Column(Integer, ForeignKey('produtos.id'), nullable=True)  # FK para produto PAI
    
    # Flags para controle de varia��o (Sprint 2 - Nova Estrutura)
    is_parent = Column(Boolean, default=False, nullable=False)  # Indica se � produto pai (agrupador)
    is_sellable = Column(Boolean, default=True, nullable=False)  # Indica se pode ser vendido
    
    # ========== SPRINT 2: ATRIBUTOS DE VARIA��O ==========
    variation_attributes = Column(JSON, nullable=True)  # Ex: {"cor": "azul", "tamanho": "G"}
    variation_signature = Column(String(255), nullable=True, index=True)  # Ex: "cor:azul|tamanho:G"
    
    # ========== SPRINT 4: PRODUTOS KIT ==========
    # tipo_kit: Define como o custo/estoque do KIT � tratado
    # - VIRTUAL: Custo = soma dos componentes, estoque = menor dispon�vel dos componentes
    # - FISICO: Custo pr�prio, estoque pr�prio (KIT j� montado/pr�-embalado)
    tipo_kit = Column(String(20), default='VIRTUAL', nullable=True)  # VIRTUAL, FISICO (s� para tipo_produto=KIT)
    
    descricao_curta = Column(Text, nullable=True)
    descricao_completa = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array
    
    # Código de Barras
    codigo_barras = Column(String(13), nullable=True)
    codigos_barras_alternativos = Column(Text, nullable=True)  # JSON array
    
    # Relacionamentos (FKs)
    categoria_id = Column(Integer, ForeignKey('categorias.id'), nullable=True)
    subcategoria = Column(String(100), nullable=True)  # Subcategoria (campo texto)
    marca_id = Column(Integer, ForeignKey('marcas.id'), nullable=True)
    fornecedor_id = Column(Integer, ForeignKey('clientes.id'), nullable=True)
    departamento_id = Column(Integer, ForeignKey('departamentos.id'), nullable=True)
    
    # Preços
    preco_custo = Column(Float, default=0)
    preco_venda = Column(Float, nullable=True, default=0)  # Nullable para produtos PAI
    preco_promocional = Column(Float, nullable=True)
    promocao_inicio = Column(DateTime, nullable=True)
    promocao_fim = Column(DateTime, nullable=True)
    promocao_ativa = Column(Boolean, default=False)
    
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
    unidade = Column(String(10), default='UN')
    condicao = Column(String(20), default='novo')  # novo, usado, recondicionado
    
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
    gtin_ean = Column(String(13), nullable=True)
    gtin_ean_tributario = Column(String(13), nullable=True)
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
    tipo_recorrencia = Column(String(20), nullable=True)  # daily, weekly, monthly, yearly
    intervalo_dias = Column(Integer, nullable=True)  # N�mero de dias entre doses/compras
    numero_doses = Column(Integer, nullable=True)  # N�mero total de doses no ciclo (ex: 3 para vacina V8)
    observacoes_recorrencia = Column(Text, nullable=True)  # Ex: "Nexgard para c�es 4-10kg, repetir a cada 30 dias"
    
    # ========== RECORR�NCIA E COMPATIBILIDADE (NOVO) ==========
    # Sistema de lembretes para produtos recorrentes (medicamentos, ra��es, etc)
    tem_recorrencia = Column(Boolean, default=False)  # Indica se � produto recorrente
    tipo_recorrencia = Column(String(20), nullable=True)  # daily, weekly, monthly, yearly
    intervalo_dias = Column(Integer, nullable=True)  # N�mero de dias entre doses/compras
    numero_doses = Column(Integer, nullable=True)  # N�mero total de doses no ciclo (ex: 3 para vacina V8)
    observacoes_recorrencia = Column(Text, nullable=True)  # Ex: "Nexgard para c�es 4-10kg, repetir a cada 30 dias"
    
    # Compatibilidade de esp�cie
    especie_compativel = Column(String(50), nullable=True)  # dog, cat, both (para ra��es, medicamentos)
    
    # ========== RA��O - CALCULADORA (FASE 2) ==========
    classificacao_racao = Column(String(50), nullable=True)  # super_premium, premium, especial, standard
    peso_embalagem = Column(Float, nullable=True)  # Peso da embalagem em kg
    tabela_nutricional = Column(Text, nullable=True)  # JSON: {"proteina": 28, "gordura": 15, "fibra": 3, "umidade": 10}
    categoria_racao = Column(String(50), nullable=True)  # filhote, adulto, senior, gestante, etc
    especies_indicadas = Column(String(100), nullable=True)  # dog, cat, both (espec�fico para ra��es)
    tabela_consumo = Column(Text, nullable=True)  # JSON com tabela de consumo da embalagem (peso x idade x quantidade di�ria)
    
    # Imagem Principal
    imagem_principal = Column(String(255), nullable=True)
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete - data de exclus�o
    
    # ========== SISTEMA DE PREDECESSOR/SUCESSOR ==========
    # Permite vincular produtos que substituem outros, mantendo histórico consolidado
    # Ex: Ração 350g → Ração 300g (mudança de embalagem)
    produto_predecessor_id = Column(Integer, ForeignKey('produtos.id'), nullable=True)  # Produto que este substitui
    data_descontinuacao = Column(DateTime, nullable=True)  # Quando foi substituído por outro
    motivo_descontinuacao = Column(String(255), nullable=True)  # Ex: Mudança de embalagem, Reformulação
    
    # Relationships
    categoria = relationship("Categoria", back_populates="produtos")
    marca = relationship("Marca", back_populates="produtos")
    departamento = relationship("Departamento", back_populates="produtos")
    fornecedor = relationship("Cliente", foreign_keys=[fornecedor_id])
    imagens = relationship("ProdutoImagem", back_populates="produto", cascade="all, delete-orphan")
    lotes = relationship("ProdutoLote", back_populates="produto", cascade="all, delete-orphan")
    fornecedores_alternativos = relationship("ProdutoFornecedor", back_populates="produto", cascade="all, delete-orphan")
    listas_preco = relationship("ProdutoListaPreco", back_populates="produto", cascade="all, delete-orphan")
    movimentacoes = relationship("EstoqueMovimentacao", back_populates="produto")
    bling_sync = relationship("ProdutoBlingSync", back_populates="produto", uselist=False)
    user = relationship("User")
    
    # ========== PREDECESSOR/SUCESSOR ==========
    # Relacionamento para cadeia de evolução de produtos
    predecessor = relationship("Produto", remote_side=[id], foreign_keys=[produto_predecessor_id], backref="sucessores")
    # Acesso: produto.predecessor (produto anterior)
    # Acesso: produto.sucessores (lista de produtos que substituem este)
    
    # ========== SPRINT 2: VARIA��ES ==========
    # Relacionamento pai/filhos para produtos com varia��o
    produto_pai = relationship("Produto", remote_side=[id], foreign_keys=[produto_pai_id], backref="variacoes")
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
        Index('idx_produtos_categoria', 'categoria_id'),
        Index('idx_produtos_marca', 'marca_id'),
        Index('idx_produtos_user', 'user_id'),        Index('idx_produtos_variation_signature', 'tenant_id', 'variation_signature'),  # Sprint 2: Varia��es        {'extend_existing': True}
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
        
        lotes_ativos = [l for l in self.lotes if l.status == 'ativo' and l.quantidade_disponivel > 0]
        if not lotes_ativos:
            return None
        
        return min(l.data_validade for l in lotes_ativos)


class ProdutoImagem(BaseTenantModel):
    """Imagens do produto"""
    __tablename__ = "produto_imagens"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id', ondelete='CASCADE'), nullable=False)
    url = Column(String(255), nullable=False)
    ordem = Column(Integer, default=0)
    e_principal = Column(Boolean, default=False)
    tamanho = Column(Integer, nullable=True)  # bytes
    largura = Column(Integer, nullable=True)  # pixels
    altura = Column(Integer, nullable=True)  # pixels
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    produto = relationship("Produto", back_populates="imagens")

class ProdutoKitComponente(BaseTenantModel):
    """
    Componentes de um produto KIT
    
    Define quais produtos fazem parte de um KIT e em que quantidade.
    Exemplo: Kit Banho = Shampoo (1un) + Condicionador (1un) + Toalha (2un)
    
    ?? RESTRI��ES DE DOM�NIO (OBRIGAT�RIAS):
    ========================================
    
    1. kit_id - DEVE referenciar Produto com tipo_produto='KIT'
       ? PROIBIDO: tipo_produto IN ('SIMPLES', 'PAI', 'VARIACAO')
    
    2. produto_componente_id - DEVE referenciar:
       ? Produtos com tipo_produto='SIMPLES'
       ? Produtos com tipo_produto='VARIACAO'
       ? PROIBIDO: tipo_produto='KIT' (KIT n�o pode conter outro KIT)
       ? PROIBIDO: tipo_produto='PAI' (PAI n�o � vend�vel/utiliz�vel)
    
    3. quantidade - DEVE ser maior que 0 (zero)
    
    4. Produto componente N�O pode ser o pr�prio KIT (evitar recurs�o)
    
    Comportamento por tipo_kit:
    - VIRTUAL: Custo do KIT = soma(componente.preco_custo * quantidade)
    - FISICO: Custo do KIT = preco_custo do pr�prio KIT (ignora componentes para custo)
    
    ?? VALIDA��ES devem ser implementadas na camada de Service (kit_custo_service.py)
    """
    __tablename__ = "produto_kit_componentes"
    __table_args__ = (
        Index('idx_kit_componentes_kit', 'kit_id'),
        Index('idx_kit_componentes_produto', 'produto_componente_id'),
        # Um produto n�o pode ser componente duplicado no mesmo kit
        Index('idx_kit_componentes_unique', 'kit_id', 'produto_componente_id', unique=True),
        {'extend_existing': True}
    )
    
    id = Column(Integer, primary_key=True)
    
    # ?? PROTE��O: kit_id DEVE ser tipo_produto='KIT'
    kit_id = Column(Integer, ForeignKey('produtos.id', ondelete='CASCADE'), nullable=False)
    
    # ?? PROTE��O: produto_componente_id DEVE ser tipo_produto IN ('SIMPLES', 'VARIACAO')
    # ? N�O aceitar tipo_produto='KIT' ou 'PAI'
    produto_componente_id = Column(Integer, ForeignKey('produtos.id'), nullable=False)
    
    # Quantidade do componente no KIT
    quantidade = Column(Float, nullable=False, default=1.0)
    
    # Componente � opcional? (para kits customiz�veis no futuro)
    opcional = Column(Boolean, default=False)
    
    # Ordem de exibi��o
    ordem = Column(Integer, default=0)
    
    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    kit = relationship("Produto", foreign_keys=[kit_id], backref="componentes_kit")
    produto_componente = relationship("Produto", foreign_keys=[produto_componente_id])

class ProdutoLote(BaseTenantModel):
    """Lotes de produtos com controle FIFO"""
    __tablename__ = "produto_lotes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id', ondelete='CASCADE'), nullable=False)
    
    # ========== SPRINT 2: SUPORTE A VARIA��ES ==========
    # CORRIGIDO: N�o existe tabela product_variations separada
    # Varia��es s�o produtos com tipo_produto='VARIACAO' na tabela produtos
    product_variation_id = Column(Integer, nullable=True)  # ?? DEPRECATED: usar produto_id
    
    nome_lote = Column(String(50), nullable=False)
    data_fabricacao = Column(DateTime, nullable=True)
    data_validade = Column(DateTime, nullable=True)
    deposito = Column(String(50), nullable=True)
    
    # Quantidades
    quantidade_inicial = Column(Float, nullable=False)
    quantidade_disponivel = Column(Float, nullable=False)
    quantidade_reservada = Column(Float, default=0)
    
    limite_dias = Column(Integer, default=30)
    codigo_agregacao = Column(String(50), nullable=True)
    status = Column(String(20), default='ativo')  # ativo, vencido, bloqueado, esgotado
    ordem_entrada = Column(Integer, nullable=False)  # Timestamp Unix para FIFO
    custo_unitario = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    produto = relationship("Produto", back_populates="lotes")
    
    # ========== SPRINT 2: SUPORTE A VARIA��ES ==========
    # ? DESABILITADO: ProductVariation removido - causava conflitos
    # variation = relationship("ProductVariation", backref="lotes")
    
    @property
    def dias_para_vencer(self):
        """Calcula quantos dias faltam para vencer"""
        if not self.data_validade:
            return None
        delta = self.data_validade - datetime.utcnow()
        return delta.days
    
    @property
    def alerta_vencimento(self):
        """Verifica se está próximo ao vencimento"""
        dias = self.dias_para_vencer
        return dias is not None and dias <= self.limite_dias and dias > 0
    
    @property
    def vencido(self):
        """Verifica se está vencido"""
        dias = self.dias_para_vencer
        return dias is not None and dias <= 0


class ProdutoFornecedor(BaseTenantModel):
    """Fornecedores alternativos do produto"""
    __tablename__ = "produto_fornecedores"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id', ondelete='CASCADE'), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey('clientes.id'), nullable=False)
    codigo_fornecedor = Column(String(50), nullable=True)
    preco_custo = Column(Float, nullable=True)
    prazo_entrega = Column(Integer, nullable=True)  # dias
    estoque_fornecedor = Column(Float, nullable=True)
    e_principal = Column(Boolean, default=False)
    
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    produto = relationship("Produto", back_populates="fornecedores_alternativos")
    fornecedor = relationship("Cliente")


class ListaPreco(BaseTenantModel):
    """Listas de preço (atacado, varejo, VIP, etc)"""
    __tablename__ = "listas_preco"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    produtos = relationship("ProdutoListaPreco", back_populates="lista_preco")
    user = relationship("User")


class ProdutoListaPreco(BaseTenantModel):
    """Preços por lista"""
    __tablename__ = "produto_listas_preco"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id', ondelete='CASCADE'), nullable=False)
    lista_preco_id = Column(Integer, ForeignKey('listas_preco.id', ondelete='CASCADE'), nullable=False)
    preco = Column(Float, nullable=False)
    desconto_percentual = Column(Float, nullable=True)
    desconto_valor = Column(Float, nullable=True)
    ativo = Column(Boolean, default=True)
    
    # Relationships
    produto = relationship("Produto", back_populates="listas_preco")
    lista_preco = relationship("ListaPreco", back_populates="produtos")


class EstoqueMovimentacao(BaseTenantModel):
    """Movimentações de estoque com rastreamento de lotes"""
    __tablename__ = "estoque_movimentacoes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=False)
    tipo = Column(String(20), nullable=False)  # entrada, saida, transferencia
    motivo = Column(String(50), nullable=True)  # compra, venda, ajuste, devolucao, perda, transferencia, balanco
    
    quantidade = Column(Float, nullable=False)
    quantidade_anterior = Column(Float, nullable=True)
    quantidade_nova = Column(Float, nullable=True)
    
    custo_unitario = Column(Float, nullable=True)
    valor_total = Column(Float, nullable=True)
    
    # Lotes
    lote_id = Column(Integer, ForeignKey('produto_lotes.id'), nullable=True)  # Lote principal (para entradas)
    lotes_consumidos = Column(Text, nullable=True)  # JSON: [{"lote_id": 1, "quantidade": 5}]
    
    # Origem/Destino
    estoque_origem = Column(String(20), nullable=True)  # fisico, ecommerce
    estoque_destino = Column(String(20), nullable=True)
    
    # Referências
    documento = Column(String(50), nullable=True)  # Número NFe, número venda, etc
    referencia_id = Column(Integer, nullable=True)  # ID da venda, compra, etc
    referencia_tipo = Column(String(20), nullable=True)  # venda, compra, ajuste
    
    observacao = Column(Text, nullable=True)
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    produto = relationship("Produto", back_populates="movimentacoes")
    lote = relationship("ProdutoLote")
    user = relationship("User")


class ProdutoBlingSync(BaseTenantModel):
    """Sincroniza��o de produtos com Bling"""
    __tablename__ = "produto_bling_sync"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=False, unique=True)
    bling_produto_id = Column(String(50), nullable=True)
    sincronizar = Column(Boolean, default=True)
    estoque_compartilhado = Column(Boolean, default=True)
    ultima_sincronizacao = Column(DateTime, nullable=True)
    status = Column(String(20), default='ativo')  # ativo, pausado, erro
    erro_mensagem = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    produto = relationship("Produto", back_populates="bling_sync")


# ============================================================================
# PEDIDOS DE COMPRA
# ============================================================================

class PedidoCompra(BaseTenantModel):
    """Pedidos de compra de produtos (com suporte futuro para IA)"""
    __tablename__ = "pedidos_compra"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    numero_pedido = Column(String(50), unique=True, nullable=False, index=True)
    fornecedor_id = Column(Integer, nullable=False, index=True)  # FK para clientes
    
    # Status: rascunho, enviado, confirmado, recebido_parcial, recebido_total, cancelado
    status = Column(String(20), nullable=False, default="rascunho", index=True)
    
    # Valores
    valor_total = Column(Float, nullable=False, default=0)
    valor_frete = Column(Float, default=0)
    valor_desconto = Column(Float, default=0)
    valor_final = Column(Float, nullable=False, default=0)
    
    # Datas
    data_pedido = Column(DateTime, nullable=False, default=datetime.utcnow)
    data_prevista_entrega = Column(DateTime)
    data_recebimento = Column(DateTime)
    data_envio = Column(DateTime)
    data_confirmacao = Column(DateTime)
    
    # Observa��es e IA
    observacoes = Column(Text)
    foi_alterado_apos_envio = Column(Boolean, default=False)  # Flag para alertar mudan�as
    sugestao_ia = Column(Boolean, default=False)  # Se foi sugerido por IA
    confianca_ia = Column(Float)  # 0-1: Confian�a da sugest�o
    dados_ia = Column(Text)  # JSON com an�lise da IA
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    itens = relationship("PedidoCompraItem", back_populates="pedido", cascade="all, delete-orphan")
    user = relationship("User", foreign_keys=[user_id])


class PedidoCompraItem(BaseTenantModel):
    """Itens de pedidos de compra"""
    __tablename__ = "pedidos_compra_itens"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_compra_id = Column(Integer, ForeignKey('pedidos_compra.id'), nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=False, index=True)
    
    # Quantidades
    quantidade_pedida = Column(Float, nullable=False)
    quantidade_recebida = Column(Float, default=0)
    
    # Valores
    preco_unitario = Column(Float, nullable=False)
    desconto_item = Column(Float, default=0)
    valor_total = Column(Float, nullable=False)
    
    # Status do item
    status = Column(String(20), default="pendente")  # pendente, recebido_parcial, recebido_total, cancelado
    
    # IA
    sugestao_ia = Column(Boolean, default=False)
    motivo_ia = Column(Text)  # Por que a IA sugeriu este item
    
    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    pedido = relationship("PedidoCompra", back_populates="itens")
    produto = relationship("Produto")


# ============================================================================
# NOTAS DE ENTRADA (NF-e de Fornecedores)
# ============================================================================

class NotaEntrada(BaseTenantModel):
    """Notas fiscais de entrada (NF-e de fornecedores)"""
    __tablename__ = "notas_entrada"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    numero_nota = Column(String(20), nullable=False, index=True)
    serie = Column(String(5), nullable=False)
    chave_acesso = Column(String(44), unique=True, nullable=False, index=True)
    
    # Fornecedor
    fornecedor_cnpj = Column(String(18), nullable=False)
    fornecedor_nome = Column(String(255), nullable=False)
    fornecedor_id = Column(Integer, index=True)  # Link com clientes (fornecedores)
    
    # Datas
    data_emissao = Column(DateTime, nullable=False)
    data_entrada = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Valores
    valor_produtos = Column(Float, nullable=False)
    valor_frete = Column(Float, default=0)
    valor_desconto = Column(Float, default=0)
    valor_total = Column(Float, nullable=False)
    
    # XML
    xml_content = Column(Text, nullable=False)
    
    # Status: pendente, processada, erro
    status = Column(String(20), default="pendente", index=True)
    erro_mensagem = Column(Text)
    
    # Processamento
    processada_em = Column(DateTime)
    produtos_vinculados = Column(Integer, default=0)
    produtos_nao_vinculados = Column(Integer, default=0)
    entrada_estoque_realizada = Column(Boolean, default=False)
    
    # Rateio Online vs Loja Física (apenas informativo/analítico - estoque é UNIFICADO)
    tipo_rateio = Column(String(20), default="loja")  # 'online', 'loja', 'parcial'
    percentual_online = Column(Float, default=0)  # % do valor total que é online
    percentual_loja = Column(Float, default=100)  # % do valor total que é loja
    valor_online = Column(Float, default=0)  # R$ referente a online
    valor_loja = Column(Float, default=0)  # R$ referente a loja física
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    itens = relationship("NotaEntradaItem", back_populates="nota", cascade="all, delete-orphan")
    user = relationship("User", foreign_keys=[user_id])


class NotaEntradaItem(BaseTenantModel):
    """Itens da nota fiscal de entrada"""
    __tablename__ = "notas_entrada_itens"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    nota_entrada_id = Column(Integer, ForeignKey('notas_entrada.id'), nullable=False, index=True)
    
    # Dados do XML
    numero_item = Column(Integer, nullable=False)
    codigo_produto = Column(String(100))
    descricao = Column(String(500), nullable=False)
    ncm = Column(String(8))
    cest = Column(String(7))  # C�digo CEST do produto
    cfop = Column(String(4))
    origem = Column(String(1))  # Origem da mercadoria (0-8)
    aliquota_icms = Column(Float, default=0)  # Al�quota ICMS (%)
    aliquota_pis = Column(Float, default=0)  # Al�quota PIS (%)
    aliquota_cofins = Column(Float, default=0)  # Al�quota COFINS (%)
    unidade = Column(String(10))
    quantidade = Column(Float, nullable=False)
    valor_unitario = Column(Float, nullable=False)
    valor_total = Column(Float, nullable=False)
    ean = Column(String(14))  # C�digo de barras EAN
    lote = Column(String(50))  # Lote do produto
    data_validade = Column(Date)  # Data de validade
    
    # Vincula��o
    produto_id = Column(Integer, ForeignKey('produtos.id'), index=True)
    vinculado = Column(Boolean, default=False)
    confianca_vinculo = Column(Float)  # 0-1
    
    # Status: pendente, vinculado, nao_vinculado, processado
    status = Column(String(20), default="pendente")
    
    # Rateio (apenas para análise/relatórios - estoque é UNIFICADO)
    quantidade_online = Column(Float, default=0)  # Quantidade deste item que é do online
    valor_online = Column(Float, default=0)  # Valor calculado: quantidade_online × valor_unitario
    
    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    nota = relationship("NotaEntrada", back_populates="itens")
    produto = relationship("Produto", foreign_keys=[produto_id])


class ProdutoHistoricoPreco(BaseTenantModel):
    """Hist�rico de altera��es de pre�os de produtos"""
    __tablename__ = "produtos_historico_precos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=False, index=True)
    
    # Pre�os anteriores e novos
    preco_custo_anterior = Column(Float)
    preco_custo_novo = Column(Float)
    preco_venda_anterior = Column(Float)
    preco_venda_novo = Column(Float)
    margem_anterior = Column(Float)
    margem_nova = Column(Float)
    
    # Varia��es percentuais
    variacao_custo_percentual = Column(Float)  # % de varia��o do custo
    variacao_venda_percentual = Column(Float)  # % de varia��o do pre�o venda
    
    # Contexto da altera��o
    motivo = Column(String(100))  # 'nfe_entrada', 'manual', 'promocao', 'reajuste'
    nota_entrada_id = Column(Integer, ForeignKey('notas_entrada.id'), nullable=True, index=True)
    referencia = Column(String(100))  # n�mero da nota, descri��o, etc
    observacoes = Column(Text)
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    produto = relationship("Produto", foreign_keys=[produto_id])
    nota_entrada = relationship("NotaEntrada", foreign_keys=[nota_entrada_id])
    user = relationship("User", foreign_keys=[user_id])


# ====================
# LEMBRETES E NOTIFICA��ES
# ====================

class Lembrete(BaseTenantModel):
    """Sistema de lembretes para produtos recorrentes (medicamentos, ra��es, etc)"""
    __tablename__ = "lembretes"
    
    id = Column(Integer, primary_key=True)
    
    # Relacionamentos
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False, index=True)
    pet_id = Column(Integer, ForeignKey('pets.id'), nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey('produtos.id'), nullable=False, index=True)
    venda_id = Column(Integer, ForeignKey('vendas.id'), nullable=True, index=True)  # Venda que originou o lembrete
    
    # Datas
    data_compra = Column(DateTime, nullable=True)  # Quando foi comprado
    data_proxima_dose = Column(DateTime, nullable=False, index=True)  # Quando deve tomar/comprar novamente
    data_notificacao_7_dias = Column(DateTime, nullable=True)  # Quando enviar notifica��o (7 dias antes)
    data_notificacao_enviada = Column(DateTime, nullable=True)  # Quando foi efetivamente enviado
    data_completado = Column(DateTime, nullable=True)  # Quando o cliente confirmou a compra/dose
    
    # Status
    status = Column(String(20), default='pendente')  # pendente, notificado, completado, cancelado
    metodo_notificacao = Column(String(50), default='whatsapp')  # whatsapp, email, sms, app
    notificacao_enviada = Column(Boolean, default=False)
    
    # Informa��es adicionais
    observacoes = Column(Text, nullable=True)
    quantidade_recomendada = Column(Float, nullable=True)  # Quantidade a comprar/usar
    preco_estimado = Column(Float, nullable=True)  # Pre�o estimado na pr�xima compra
    
    # Controle de doses
    dose_atual = Column(Integer, default=1)  # Qual dose o cliente est� (1, 2, 3...)
    dose_total = Column(Integer, nullable=True)  # Total de doses necess�rias (ex: 3)
    historico_doses = Column(Text, nullable=True)  # JSON com hist�rico [{dose: 1, data: '2026-01-13', comprou: true}]
    
    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    cliente = relationship("Cliente")
    pet = relationship("Pet")
    produto = relationship("Produto")


# ============================================================================
# SISTEMA DE ATRIBUTOS E VARIA��ES DE PRODUTOS
# ============================================================================

class ProdutoAtributo(BaseTenantModel):
    """
    Atributos de produtos PAI que definem suas varia��es
    
    Exemplos:
    - Produto PAI: "Ra��o Golden Adulto"
      - Atributo 1: "Peso" (op��es: 1kg, 3kg, 15kg)
      - Atributo 2: "Sabor" (op��es: Carne, Frango, Cordeiro)
    
    Regras:
    - Apenas produtos tipo PAI podem ter atributos
    - Cada atributo pode ter m�ltiplas op��es
    - Combina��es de op��es geram varia��es
    """
    __tablename__ = "produtos_atributos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    
    # Relacionamento com produto PAI
    produto_pai_id = Column(Integer, ForeignKey('produtos.id'), nullable=False)
    
    # Dados do atributo
    nome = Column(String(100), nullable=False)  # Ex: "Peso", "Sabor", "Cor", "Tamanho"
    ordem = Column(Integer, default=0)  # Ordem de exibi��o
    obrigatorio = Column(Boolean, default=True)  # Se obrigat�rio na cria��o de varia��o
    
    # Auditoria
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    produto_pai = relationship("Produto", foreign_keys=[produto_pai_id], backref="atributos")
    opcoes = relationship("ProdutoAtributoOpcao", back_populates="atributo", cascade="all, delete-orphan")
    user = relationship("User")
    
    # �ndices
    __table_args__ = (
        Index('idx_atributos_produto_pai', 'produto_pai_id'),
        Index('idx_atributos_user', 'user_id'),
        {'extend_existing': True}
    )


class ProdutoAtributoOpcao(BaseTenantModel):
    """
    Op��es/valores de um atributo de produto
    
    Exemplos:
    - Atributo "Peso" pode ter op��es: "1kg", "3kg", "15kg"
    - Atributo "Sabor" pode ter op��es: "Carne", "Frango", "Cordeiro"
    
    Regras:
    - Cada op��o pertence a um atributo
    - Varia��es referenciam combina��es de op��es
    """
    __tablename__ = "produtos_atributos_opcoes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    
    # Relacionamento com atributo
    atributo_id = Column(Integer, ForeignKey('produtos_atributos.id'), nullable=False)
    
    # Dados da op��o
    valor = Column(String(100), nullable=False)  # Ex: "15kg", "Carne", "Vermelho"
    ordem = Column(Integer, default=0)  # Ordem de exibi��o
    ajuste_preco = Column(Float, default=0)  # Ajuste de pre�o em rela��o ao produto PAI
    ajuste_preco_tipo = Column(String(20), default='fixo')  # fixo, percentual
    codigo_extra = Column(String(50), nullable=True)  # C�digo adicional para varia��o (ex: SKU extra)
    
    # Auditoria
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    atributo = relationship("ProdutoAtributo", back_populates="opcoes")
    
    # �ndices
    __table_args__ = (
        Index('idx_opcoes_atributo', 'atributo_id'),
        {'extend_existing': True}
    )


class ProdutoVariacaoAtributo(BaseTenantModel):
    """
    Tabela de associa��o entre varia��es e op��es de atributos
    
    Mapeia quais op��es de atributos comp�em uma varia��o espec�fica
    
    Exemplo:
    - Varia��o "Ra��o Golden Adulto 15kg Carne"
      - Atributo "Peso" ? Op��o "15kg"
      - Atributo "Sabor" ? Op��o "Carne"
    
    Regras:
    - Apenas produtos tipo VARIACAO podem ter entradas aqui
    - Cada varia��o deve ter uma op��o de cada atributo obrigat�rio do PAI
    """
    __tablename__ = "produtos_variacoes_atributos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    
    # Relacionamentos
    variacao_id = Column(Integer, ForeignKey('produtos.id'), nullable=False)  # FK para produto VARIACAO
    atributo_id = Column(Integer, ForeignKey('produtos_atributos.id'), nullable=False)
    opcao_id = Column(Integer, ForeignKey('produtos_atributos_opcoes.id'), nullable=False)
    
    # Auditoria
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    variacao = relationship("Produto", foreign_keys=[variacao_id], backref="atributos_variacao")
    atributo = relationship("ProdutoAtributo")
    opcao = relationship("ProdutoAtributoOpcao")
    
    # �ndices e constraints
    __table_args__ = (
        Index('idx_var_atributos_variacao', 'variacao_id'),
        Index('idx_var_atributos_atributo', 'atributo_id'),
        Index('idx_var_atributos_opcao', 'opcao_id'),
        # Constraint: Uma varia��o n�o pode ter a mesma op��o de atributo duplicada
        Index('idx_var_atributos_unique', 'variacao_id', 'atributo_id', unique=True),
        {'extend_existing': True}
    )
