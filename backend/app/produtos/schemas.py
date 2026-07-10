"""Schemas Pydantic do modulo de produtos.

Mantem os contratos de request/response fora do arquivo de rotas.
A ordem das classes preserva o comportamento historico de ProdutoResponse e LoteResponse.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================
# SCHEMAS - CATEGORIAS
# ==========================================


class CategoriaBase(BaseModel):
    nome: str
    categoria_pai_id: Optional[int] = None
    departamento_id: Optional[int] = None
    descricao: Optional[str] = None
    icone: Optional[str] = None
    cor: Optional[str] = None
    ordem: Optional[int] = 0


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(CategoriaBase):
    pass


class CategoriaResponse(CategoriaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ativo: bool
    created_at: datetime
    updated_at: datetime
    nivel: Optional[int] = None
    total_filhos: Optional[int] = 0
    total_produtos: Optional[int] = 0
    departamento_nome: Optional[str] = None


# ==========================================
# SCHEMAS - MARCAS
# ==========================================


class MarcaBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    logo: Optional[str] = None
    site: Optional[str] = None


class MarcaCreate(MarcaBase):
    pass


class MarcaUpdate(MarcaBase):
    pass


class MarcaResponse(MarcaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ativo: bool
    created_at: datetime


# ==========================================
# SCHEMAS - DEPARTAMENTOS
# ==========================================


class DepartamentoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None


class DepartamentoCreate(DepartamentoBase):
    pass


class DepartamentoUpdate(DepartamentoBase):
    pass


class DepartamentoResponse(DepartamentoBase):
    id: int
    ativo: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ==========================================
# SCHEMAS - GERADOR DE CÃ“DIGO DE BARRAS
# ==========================================


class GerarCodigoBarrasRequest(BaseModel):
    sku: str  # CÃ³digo do produto (ex: PROD-00123)


class GerarCodigoBarrasResponse(BaseModel):
    codigo_barras: str
    sku_usado: str
    formato: str
    valido: bool


# ==========================================
# SCHEMAS - KIT COMPONENTES
# ==========================================


class KitComponenteBase(BaseModel):
    """Schema base para componente de KIT"""

    produto_componente_id: int  # ID do produto que faz parte do KIT
    quantidade: float  # Quantidade necessÃ¡ria do componente no KIT
    ordem: int = 0
    opcional: bool = False


class KitComponenteCreate(KitComponenteBase):
    """Schema para criar componente de KIT (enviado pelo frontend)"""

    pass


class KitComponenteResponse(BaseModel):
    """Schema de resposta com dados completos do componente"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    produto_id: int
    produto_nome: str
    produto_sku: str
    produto_tipo: str
    quantidade: float
    estoque_componente: float
    estoque_reservado: float = 0
    estoque_disponivel: float = 0
    kits_possiveis: int
    ordem: int
    opcional: bool


# ==========================================
# SCHEMAS - PRODUTOS
# ==========================================


class ProdutoBase(BaseModel):
    codigo: str  # SKU
    nome: str
    descricao_curta: Optional[str] = None
    descricao_completa: Optional[str] = None
    codigo_barras: Optional[str] = None
    gtin_ean: Optional[str] = None
    gtin_ean_tributario: Optional[str] = None
    codigos_barras_alternativos: Optional[str] = None
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None
    departamento_id: Optional[int] = None
    unidade: str = "UN"
    e_granel: Optional[bool] = False
    participa_sugestao_compra: Optional[bool] = True
    peso_bruto: Optional[float] = None
    peso_liquido: Optional[float] = None
    preco_custo: Optional[float] = 0
    preco_venda: Optional[float] = None  # Opcional porque produto PAI não tem preço
    preco_promocional: Optional[float] = None
    promocao_inicio: Optional[datetime] = None
    promocao_fim: Optional[datetime] = None
    # Preços por canal — None = usar preco_venda padrão
    preco_ecommerce: Optional[float] = None
    preco_ecommerce_promo: Optional[float] = None
    preco_ecommerce_promo_inicio: Optional[datetime] = None
    preco_ecommerce_promo_fim: Optional[datetime] = None
    preco_app: Optional[float] = None
    preco_app_promo: Optional[float] = None
    preco_app_promo_inicio: Optional[datetime] = None
    preco_app_promo_fim: Optional[datetime] = None
    anunciar_ecommerce: Optional[bool] = True
    anunciar_app: Optional[bool] = True
    controle_lote: Optional[bool] = False
    estoque_minimo: Optional[float] = 0
    estoque_maximo: Optional[float] = None
    ncm: Optional[str] = None
    cest: Optional[str] = None
    origem: Optional[str] = None
    cfop: Optional[str] = None
    aliquota_icms: Optional[float] = None
    aliquota_pis: Optional[float] = None
    aliquota_cofins: Optional[float] = None
    # RecorrÃªncia (Fase 1)
    tem_recorrencia: Optional[bool] = False
    tipo_recorrencia: Optional[str] = None
    intervalo_dias: Optional[int] = None
    numero_doses: Optional[int] = None
    especie_compativel: Optional[str] = None
    observacoes_recorrencia: Optional[str] = None
    # RaÃ§Ã£o - Calculadora (Fase 2)
    eh_racao: Optional[bool] = None
    classificacao_racao: Optional[str] = None
    peso_embalagem: Optional[float] = None
    tabela_nutricional: Optional[str] = None  # JSON string
    categoria_racao: Optional[str] = None
    especies_indicadas: Optional[str] = None
    tabela_consumo: Optional[str] = None  # JSON com tabela de consumo da embalagem
    # OpÃ§Ãµes de RaÃ§Ã£o - Sistema DinÃ¢mico (Foreign Keys)
    linha_racao_id: Optional[int] = None
    porte_animal_id: Optional[int] = None
    fase_publico_id: Optional[int] = None
    tipo_tratamento_id: Optional[int] = None
    sabor_proteina_id: Optional[int] = None
    apresentacao_peso_id: Optional[int] = None
    # Sprint 2: Produtos com variaÃ§Ã£o
    tipo_produto: Optional[str] = "SIMPLES"  # SIMPLES, PAI, VARIACAO, KIT
    produto_pai_id: Optional[int] = None  # FK para produto PAI (se for VARIACAO)
    # Sprint 4: Produtos KIT
    tipo_kit: Optional[str] = (
        None  # VIRTUAL (estoque calculado) ou FISICO (estoque prÃ³prio)
    )
    e_kit_fisico: Optional[bool] = None  # Alias para tipo_kit (usado pelo frontend)
    # Sistema Predecessor/Sucessor
    produto_predecessor_id: Optional[int] = None  # ID do produto que este substitui
    motivo_descontinuacao: Optional[str] = None  # Motivo da substituiÃ§Ã£o


class ProdutoCreate(ProdutoBase):
    """
    Schema para criaÃ§Ã£o de produto.
    Nota: preco_venda Ã© opcional - produto PAI nÃ£o precisa ter preÃ§o.
    A validaÃ§Ã£o de preÃ§o obrigatÃ³rio para produtos SIMPLES/VARIACAO Ã© feita no service.

    Para produtos KIT:
    - Se tipo_produto='KIT', pode enviar composicao_kit (lista de componentes)
    - Se e_kit_fisico=False (padrÃ£o), estoque serÃ¡ calculado automaticamente
    - Se e_kit_fisico=True, terÃ¡ estoque prÃ³prio controlado manualmente
    """

    composicao_kit: Optional[List[KitComponenteCreate]] = Field(default_factory=list)


class ProdutoUpdate(BaseModel):
    codigo: Optional[str] = None
    nome: Optional[str] = None
    descricao_curta: Optional[str] = None
    descricao_completa: Optional[str] = None
    codigo_barras: Optional[str] = None
    gtin_ean: Optional[str] = None
    gtin_ean_tributario: Optional[str] = None
    codigos_barras_alternativos: Optional[str] = None
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None
    departamento_id: Optional[int] = None
    unidade: Optional[str] = None
    e_granel: Optional[bool] = None
    participa_sugestao_compra: Optional[bool] = None
    peso_bruto: Optional[float] = None
    peso_liquido: Optional[float] = None
    preco_custo: Optional[float] = None
    preco_venda: Optional[float] = None
    preco_promocional: Optional[float] = None
    promocao_inicio: Optional[datetime] = None
    promocao_fim: Optional[datetime] = None
    # Preços por canal
    preco_ecommerce: Optional[float] = None
    preco_ecommerce_promo: Optional[float] = None
    preco_ecommerce_promo_inicio: Optional[datetime] = None
    preco_ecommerce_promo_fim: Optional[datetime] = None
    preco_app: Optional[float] = None
    preco_app_promo: Optional[float] = None
    preco_app_promo_inicio: Optional[datetime] = None
    preco_app_promo_fim: Optional[datetime] = None
    anunciar_ecommerce: Optional[bool] = None
    anunciar_app: Optional[bool] = None
    controle_lote: Optional[bool] = None
    estoque_minimo: Optional[float] = None
    estoque_maximo: Optional[float] = None
    ncm: Optional[str] = None
    cest: Optional[str] = None
    origem: Optional[str] = None
    cfop: Optional[str] = None
    aliquota_icms: Optional[float] = None
    aliquota_pis: Optional[float] = None
    aliquota_cofins: Optional[float] = None
    # RecorrÃªncia (Fase 1)
    tem_recorrencia: Optional[bool] = None
    tipo_recorrencia: Optional[str] = None
    intervalo_dias: Optional[int] = None
    numero_doses: Optional[int] = None
    especie_compativel: Optional[str] = None
    observacoes_recorrencia: Optional[str] = None
    # RaÃ§Ã£o - Calculadora (Fase 2)
    eh_racao: Optional[bool] = None
    classificacao_racao: Optional[str] = None
    peso_embalagem: Optional[float] = None
    tabela_nutricional: Optional[str] = None
    categoria_racao: Optional[str] = None
    especies_indicadas: Optional[str] = None
    tabela_consumo: Optional[str] = None
    # OpÃ§Ãµes de RaÃ§Ã£o - Sistema DinÃ¢mico (Foreign Keys)
    linha_racao_id: Optional[int] = None
    porte_animal_id: Optional[int] = None
    fase_publico_id: Optional[int] = None
    tipo_tratamento_id: Optional[int] = None
    sabor_proteina_id: Optional[int] = None
    apresentacao_peso_id: Optional[int] = None
    # Sprint 2: Produtos com variaÃ§Ã£o
    tipo_produto: Optional[str] = None
    produto_pai_id: Optional[int] = None
    # Sprint 4: Produtos KIT
    tipo_kit: Optional[str] = None
    e_kit_fisico: Optional[bool] = None
    composicao_kit: Optional[List[KitComponenteCreate]] = None
    # Sistema Predecessor/Sucessor
    produto_predecessor_id: Optional[int] = None
    motivo_descontinuacao: Optional[str] = None


class ProdutoAtivoUpdate(BaseModel):
    ativo: bool


class ProdutoFusaoPreviewRequest(BaseModel):
    produto_principal_id: int = Field(..., gt=0)
    produto_duplicado_id: int = Field(..., gt=0)


class ProdutoFusaoExecutarRequest(ProdutoFusaoPreviewRequest):
    decisoes_campos: dict[str, str] = Field(default_factory=dict)
    observacao: Optional[str] = None


# ==========================================
# SCHEMAS - IMAGENS (deve vir antes de ProdutoResponse)
# ==========================================


class ImagemUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    produto_id: int
    url: str
    thumbnail_url: Optional[str] = None
    ordem: int
    e_principal: bool
    tamanho: Optional[int] = None
    largura: Optional[int] = None
    altura: Optional[int] = None
    created_at: datetime


# ==========================================
# SCHEMAS - LOTES
# ==========================================


class LoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    produto_id: int
    nome_lote: str
    data_fabricacao: Optional[datetime] = None
    data_validade: Optional[datetime] = None
    deposito: Optional[str] = None
    quantidade_inicial: float
    quantidade_disponivel: float
    quantidade_reservada: float
    status: str
    ordem_entrada: int
    custo_unitario: Optional[float] = None
    created_at: datetime


class LoteValidadeResumoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome_lote: str
    data_validade: Optional[datetime] = None
    quantidade_inicial: float = 0
    quantidade_disponivel: float = 0


class ProdutoResponse(ProdutoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estoque_atual: Optional[float] = 0
    controlar_estoque: Optional[bool] = True  # Sempre controla estoque por padrÃ£o
    markup_percentual: Optional[float] = None  # Campo calculado
    ativo: bool
    created_at: datetime
    updated_at: datetime
    categoria: Optional[CategoriaResponse] = None
    categoria_nome: Optional[str] = (
        None  # ðŸ†• Nome da categoria (para facilitar uso no frontend)
    )
    marca: Optional[MarcaResponse] = None
    imagens: List[ImagemUploadResponse] = Field(default_factory=list)
    lotes: List[LoteResponse] = Field(default_factory=list)
    imagem_principal: Optional[str] = None  # URL da imagem principal
    imagem_principal_thumbnail: Optional[str] = None
    total_variacoes: Optional[int] = 0  # NÃºmero de variaÃ§Ãµes (para produtos PAI)
    # Sprint 4: KIT - ComposiÃ§Ã£o e estoque virtual
    composicao_kit: List[KitComponenteResponse] = Field(
        default_factory=list
    )  # Componentes do KIT
    estoque_virtual: Optional[int] = None  # Estoque calculado (apenas para KIT virtual)
    estoque_reservado: Optional[float] = (
        0  # Unidades reservadas por pedidos Bling em aberto
    )
    estoque_disponivel: Optional[float] = 0  # Estoque livre apos reservas
    validade_proxima: Optional[datetime] = None
    validade_proxima_listagem: Optional[datetime] = None
    lote_validade_proxima: Optional[str] = None
    lotes_validade_resumo: List[LoteValidadeResumoResponse] = Field(
        default_factory=list
    )
    # Sistema Predecessor/Sucessor
    data_descontinuacao: Optional[datetime] = (
        None  # Data em que foi marcado como descontinuado
    )
    predecessor_nome: Optional[str] = (
        None  # Nome do produto predecessor (populado manualmente)
    )
    sucessor_nome: Optional[str] = None  # Nome do sucessor (se existir)
    # Campo de parceria (True = pertence ao tenant parceiro)
    de_parceiro: bool = False
    # Preco efetivo para PDV/loja fisica quando houver promocao ERP ativa
    preco_venda_original: Optional[float] = None
    preco_venda_pdv: Optional[float] = None
    preco_venda_efetivo: Optional[float] = None
    promocao_pdv_ativa: bool = False
    promocao_origem_pdv: Optional[str] = None
    desconto_promocional_pdv: Optional[float] = 0
    bling_produto_id: Optional[str] = None
    bling_sync_status: Optional[str] = None
    bling_sincronizar: bool = False
    bling_ultima_sincronizacao: Optional[datetime] = None
    bling_ultimo_erro: Optional[str] = None

    @field_validator("categoria_nome", mode="before")
    @classmethod
    def set_categoria_nome(cls, v, info) -> Optional[str]:
        # Se jÃ¡ tem valor, retornar
        if v:
            return v

        # Tentar pegar da categoria
        if hasattr(info, "data") and "categoria" in info.data:
            categoria = info.data["categoria"]
            if categoria and hasattr(categoria, "nome"):
                return categoria.nome
        return None

    @field_validator("imagem_principal", mode="before")
    @classmethod
    def set_imagem_principal(cls, v, info) -> Optional[str]:
        # Se já tem valor, retornar
        if v:
            return v

        # Tentar pegar das imagens (se disponível no contexto)
        imagens = info.data.get("imagens", []) or []
        if not imagens:
            return None

        # Primeiro: buscar a marcada como principal
        for img in imagens:
            e_principal = (
                getattr(img, "e_principal", None)
                if hasattr(img, "e_principal")
                else (img.get("e_principal") if isinstance(img, dict) else None)
            )
            if e_principal:
                url = (
                    getattr(img, "url", None)
                    if hasattr(img, "url")
                    else (img.get("url") if isinstance(img, dict) else None)
                )
                if url:
                    return url

        # Fallback: retornar a primeira imagem
        img = imagens[0]
        url = (
            getattr(img, "url", None)
            if hasattr(img, "url")
            else (img.get("url") if isinstance(img, dict) else None)
        )
        return url


# Schema de resposta paginada (Sprint 1)
class ProdutosPaginadosResponse(BaseModel):
    items: List[ProdutoResponse]
    total: int
    page: int
    page_size: int
    pages: int


class RelatorioValorizacaoEstoqueItem(BaseModel):
    id: int
    codigo: Optional[str] = None
    sku: Optional[str] = None
    nome: str
    categoria_nome: Optional[str] = None
    marca_nome: Optional[str] = None
    departamento_nome: Optional[str] = None
    fornecedor_nome: Optional[str] = None
    tipo_produto: Optional[str] = None
    tipo_kit: Optional[str] = None
    estoque_atual: float = 0
    estoque_reservado: float = 0
    estoque_disponivel: float = 0
    preco_custo: float = 0
    preco_venda: float = 0
    valor_custo_total: float = 0
    valor_venda_total: float = 0


class RelatorioValorizacaoEstoqueAreaResumo(BaseModel):
    area_nome: str
    total_produtos: int = 0
    total_itens_estoque: float = 0
    total_itens_disponiveis: float = 0
    valor_custo_total: float = 0
    valor_venda_total: float = 0


class RelatorioValorizacaoEstoqueTotais(BaseModel):
    total_produtos: int = 0
    total_itens_estoque: float = 0
    total_itens_reservados: float = 0
    total_itens_disponiveis: float = 0
    valor_custo_total: float = 0
    valor_venda_total: float = 0
    margem_potencial_total: float = 0
    total_areas: int = 0


class RelatorioValorizacaoEstoqueResponse(BaseModel):
    items: List[RelatorioValorizacaoEstoqueItem]
    areas: List[RelatorioValorizacaoEstoqueAreaResumo] = Field(default_factory=list)
    totais: RelatorioValorizacaoEstoqueTotais
    total: int
    page: int
    page_size: int
    pages: int


class RelatorioValidadeProximaItem(BaseModel):
    lote_id: int
    produto_id: int
    codigo: Optional[str] = None
    sku: Optional[str] = None
    nome: str
    categoria_nome: Optional[str] = None
    marca_nome: Optional[str] = None
    departamento_nome: Optional[str] = None
    fornecedor_nome: Optional[str] = None
    nome_lote: str
    data_validade: datetime
    dias_para_vencer: int
    quantidade_disponivel: float = 0
    custo_unitario: float = 0
    preco_venda: float = 0
    valor_custo_lote: float = 0
    valor_venda_lote: float = 0
    status_validade: str = "monitorar"
    faixa_campanha: Optional[str] = None
    promocao_ativa: bool = False
    campanha_validade_ativa: bool = False
    campanha_validade_excluida: bool = False
    campanha_validade_exclusao_id: Optional[int] = None
    campanha_validade_canais: List[str] = Field(default_factory=list)
    percentual_desconto_validade: Optional[float] = None
    quantidade_promocional: float = 0
    preco_promocional_validade: Optional[float] = None
    preco_promocional_validade_app: Optional[float] = None
    preco_promocional_validade_ecommerce: Optional[float] = None
    mensagem_promocional: Optional[str] = None


class RelatorioValidadeProximaTotais(BaseModel):
    total_lotes: int = 0
    total_produtos: int = 0
    total_quantidade: float = 0
    lotes_vencidos: int = 0
    lotes_ate_7_dias: int = 0
    lotes_ate_30_dias: int = 0
    lotes_ate_60_dias: int = 0
    valor_custo_em_risco: float = 0
    valor_venda_em_risco: float = 0
    lotes_em_campanha: int = 0
    lotes_excluidos_campanha: int = 0


class RelatorioValidadeProximaResponse(BaseModel):
    items: List[RelatorioValidadeProximaItem]
    totais: RelatorioValidadeProximaTotais
    total: int
    page: int
    page_size: int
    pages: int


# ==========================================
# SCHEMAS - LOTES
# ==========================================


class LoteBase(BaseModel):
    nome_lote: str
    quantidade_inicial: float
    data_fabricacao: Optional[datetime] = None
    data_validade: Optional[datetime] = None
    custo_unitario: Optional[float] = None


class LoteCreate(LoteBase):
    pass


class LoteResponse(LoteBase):
    id: int
    produto_id: int
    quantidade_disponivel: float
    quantidade_reservada: Optional[float] = 0
    status: Optional[str] = "ativo"
    ordem_entrada: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EntradaEstoqueRequest(BaseModel):
    nome_lote: str
    quantidade: float
    data_fabricacao: Optional[datetime] = None
    data_validade: Optional[datetime] = None
    preco_custo: Optional[float] = None
    observacoes: Optional[str] = None


class SaidaEstoqueRequest(BaseModel):
    quantidade: float
    motivo: str  # venda, ajuste, perda, etc
    numero_pedido: Optional[str] = None
    observacoes: Optional[str] = None


class AtualizacaoLoteRequest(BaseModel):
    produto_ids: List[int]
    ativo: Optional[bool] = None
    eh_racao: Optional[bool] = None
    classificacao_racao: Optional[str] = None
    marca_id: Optional[int] = None
    categoria_id: Optional[int] = None
    departamento_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    fornecedor_operacao: Optional[str] = None
    fornecedor_remover_outros: Optional[bool] = None
    linha_racao_id: Optional[int] = None
    porte_animal_id: Optional[int] = None
    fase_publico_id: Optional[int] = None
    tipo_tratamento_id: Optional[int] = None
    sabor_proteina_id: Optional[int] = None
    apresentacao_peso_id: Optional[int] = None
    categoria_racao: Optional[str] = None
    especies_indicadas: Optional[str] = None
    controle_lote: Optional[bool] = None
    estoque_minimo: Optional[float] = None
    estoque_maximo: Optional[float] = None
    anunciar_ecommerce: Optional[bool] = None
    anunciar_app: Optional[bool] = None


class ImagemUpdateRequest(BaseModel):
    ordem: Optional[int] = None
    principal: Optional[bool] = None


class FornecedorVinculoCreate(BaseModel):
    fornecedor_id: int
    codigo_fornecedor: Optional[str] = None
    preco_custo: Optional[float] = None
    prazo_entrega: Optional[int] = None
    estoque_fornecedor: Optional[float] = None
    e_principal: bool = False


class FornecedorVinculoUpdate(BaseModel):
    codigo_fornecedor: Optional[str] = None
    preco_custo: Optional[float] = None
    prazo_entrega: Optional[int] = None
    estoque_fornecedor: Optional[float] = None
    e_principal: Optional[bool] = None
    ativo: Optional[bool] = None


class FornecedorVinculoResponse(BaseModel):
    id: int
    produto_id: int
    fornecedor_id: int
    codigo_fornecedor: Optional[str]
    preco_custo: Optional[float]
    prazo_entrega: Optional[int]
    estoque_fornecedor: Optional[float]
    e_principal: bool
    ativo: bool
    created_at: datetime
    updated_at: datetime

    # Dados do fornecedor
    fornecedor_nome: Optional[str] = None
    fornecedor_cpf_cnpj: Optional[str] = None
    fornecedor_email: Optional[str] = None
    fornecedor_telefone: Optional[str] = None


class HistoricoPrecoResponse(BaseModel):
    id: int
    data: datetime
    preco_custo_anterior: Optional[float]
    preco_custo_novo: Optional[float]
    preco_venda_anterior: Optional[float]
    preco_venda_novo: Optional[float]
    margem_anterior: Optional[float]
    margem_nova: Optional[float]
    variacao_custo_percentual: Optional[float]
    variacao_venda_percentual: Optional[float]
    motivo: str
    nota_numero: Optional[str] = None
    nota_data_emissao: Optional[datetime] = None
    referencia: Optional[str]
    observacoes: Optional[str]
    usuario: Optional[str]

    model_config = {"from_attributes": True}
