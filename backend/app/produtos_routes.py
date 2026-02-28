# âš ï¸ ARQUIVO CRÃTICO DE PRODUÃ‡ÃƒO
# Este arquivo impacta diretamente operaÃ§Ãµes reais (PDV / Financeiro / Estoque).
# NÃƒO alterar sem:
# 1. Entender o fluxo completo
# 2. Testar cenÃ¡rio real
# 3. Validar impacto financeiro

"""
Rotas para o mÃ³dulo de Produtos
Inclui: Categorias, Marcas, Departamentos, Produtos, Lotes, FIFO, CÃ³digo de Barras
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text, or_, case
from typing import List, Optional
from datetime import datetime, timedelta
import random
import logging
import traceback

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .security.permissions_decorator import require_permission
from .models import User, Cliente
from .produtos_models import (
    Categoria, Marca, Departamento, Produto, ProdutoLote,
    ProdutoImagem, ProdutoFornecedor, ListaPreco, ProdutoListaPreco,
    EstoqueMovimentacao, ProdutoHistoricoPreco, NotaEntrada,
    ProdutoKitComponente  # Sprint 4: ComposiÃ§Ã£o de KIT
)
from pydantic import BaseModel, Field, ConfigDict, field_validator

# Service Layer
from .services.produto_service import ProdutoService
from .services.kit_estoque_service import KitEstoqueService  # Sprint 4: ComposiÃ§Ã£o de KIT

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/produtos", tags=["produtos"])


# ==========================================
# FUNÃ‡Ã•ES AUXILIARES - CONSOLIDAÃ‡ÃƒO DE LÃ“GICA REPETIDA
# ==========================================

def _validar_tenant_e_obter_usuario(user_and_tenant):
    """Desempacota e valida user_and_tenant (padrÃ£o repetido 30+ vezes)"""
    current_user, tenant_id = user_and_tenant
    return current_user, tenant_id


def _obter_produto_ou_404(db: Session, produto_id: int, tenant_id: int):
    """Busca produto com validaÃ§Ã£o de tenant e retorna 404 se nÃ£o encontrado"""
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    return produto


def _obter_categoria_ou_404(db: Session, categoria_id: int, tenant_id: int):
    """Busca categoria com validaÃ§Ã£o de tenant e retorna 404 se nÃ£o encontrada"""
    categoria = db.query(Categoria).filter(
        Categoria.id == categoria_id,
        Categoria.tenant_id == tenant_id
    ).first()
    
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")
    
    return categoria


def _obter_marca_ou_404(db: Session, marca_id: int, tenant_id: int):
    """Busca marca com validaÃ§Ã£o de tenant e retorna 404 se nÃ£o encontrada"""
    marca = db.query(Marca).filter(
        Marca.id == marca_id,
        Marca.tenant_id == tenant_id
    ).first()
    
    if not marca:
        raise HTTPException(status_code=404, detail="Marca nÃ£o encontrada")
    
    return marca


def _validar_sku_unico(db: Session, sku: str, tenant_id: int, produto_id: Optional[int] = None):
    """Valida se SKU Ã© Ãºnico no tenant (exceto para o prÃ³prio produto em ediÃ§Ã£o)"""
    query = db.query(Produto).filter(
        Produto.sku == sku,
        Produto.tenant_id == tenant_id
    )
    
    if produto_id:
        query = query.filter(Produto.id != produto_id)
    
    if query.first():
        raise HTTPException(
            status_code=400,
            detail=f"SKU '{sku}' jÃ¡ estÃ¡ em uso"
        )


def _validar_codigo_barras_unico(db: Session, codigo_barras: str, tenant_id: int, produto_id: Optional[int] = None):
    """Valida se cÃ³digo de barras Ã© Ãºnico no tenant (exceto para o prÃ³prio produto em ediÃ§Ã£o)"""
    query = db.query(Produto).filter(
        Produto.codigo_barras == codigo_barras,
        Produto.tenant_id == tenant_id
    )
    
    if produto_id:
        query = query.filter(Produto.id != produto_id)
    
    if query.first():
        raise HTTPException(
            status_code=400,
            detail=f"CÃ³digo de barras '{codigo_barras}' jÃ¡ estÃ¡ em uso"
        )


# ==========================================
# SCHEMAS - CATEGORIAS
# ==========================================

class CategoriaBase(BaseModel):
    nome: str
    categoria_pai_id: Optional[int] = None
    descricao: Optional[str] = None
    icone: Optional[str] = None
    cor: Optional[str] = None
    ordem: int = 0


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
    created_at: datetime
    updated_at: datetime
    
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
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None
    departamento_id: Optional[int] = None
    unidade: str = "UN"
    peso_bruto: Optional[float] = None
    peso_liquido: Optional[float] = None
    preco_custo: Optional[float] = 0
    preco_venda: Optional[float] = None  # Opcional porque produto PAI nÃ£o tem preÃ§o
    preco_promocional: Optional[float] = None
    promocao_inicio: Optional[datetime] = None
    promocao_fim: Optional[datetime] = None
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
    tipo_produto: Optional[str] = 'SIMPLES'  # SIMPLES, PAI, VARIACAO, KIT
    produto_pai_id: Optional[int] = None  # FK para produto PAI (se for VARIACAO)
    # Sprint 4: Produtos KIT
    tipo_kit: Optional[str] = 'VIRTUAL'  # VIRTUAL (estoque calculado) ou FISICO (estoque prÃ³prio)
    e_kit_fisico: Optional[bool] = False  # Alias para tipo_kit (usado pelo frontend)
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
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None
    departamento_id: Optional[int] = None
    unidade: Optional[str] = None
    peso_bruto: Optional[float] = None
    peso_liquido: Optional[float] = None
    preco_custo: Optional[float] = None
    preco_venda: Optional[float] = None
    preco_promocional: Optional[float] = None
    promocao_inicio: Optional[datetime] = None
    promocao_fim: Optional[datetime] = None
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


# ==========================================
# SCHEMAS - IMAGENS (deve vir antes de ProdutoResponse)
# ==========================================

class ImagemUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    produto_id: int
    url: str
    ordem: int
    e_principal: bool
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
    categoria_nome: Optional[str] = None  # ðŸ†• Nome da categoria (para facilitar uso no frontend)
    marca: Optional[MarcaResponse] = None
    imagens: List[ImagemUploadResponse] = Field(default_factory=list)
    lotes: List[LoteResponse] = Field(default_factory=list)
    imagem_principal: Optional[str] = None  # URL da imagem principal
    total_variacoes: Optional[int] = 0  # NÃºmero de variaÃ§Ãµes (para produtos PAI)
    # Sprint 4: KIT - ComposiÃ§Ã£o e estoque virtual
    composicao_kit: List[KitComponenteResponse] = Field(default_factory=list)  # Componentes do KIT
    estoque_virtual: Optional[int] = None  # Estoque calculado (apenas para KIT virtual)
    # Sistema Predecessor/Sucessor
    data_descontinuacao: Optional[datetime] = None  # Data em que foi marcado como descontinuado
    predecessor_nome: Optional[str] = None  # Nome do produto predecessor (populado manualmente)
    sucessor_nome: Optional[str] = None  # Nome do sucessor (se existir)
    
    @field_validator('categoria_nome', mode='before')
    @classmethod
    def set_categoria_nome(cls, v, info) -> Optional[str]:
        # Se jÃ¡ tem valor, retornar
        if v:
            return v
        
        # Tentar pegar da categoria
        if hasattr(info, 'data') and 'categoria' in info.data:
            categoria = info.data['categoria']
            if categoria and hasattr(categoria, 'nome'):
                return categoria.nome
        return None
    
    @field_validator('imagem_principal', mode='before')
    @classmethod
    def set_imagem_principal(cls, v, info) -> Optional[str]:
        # Se já tem valor, retornar
        if v:
            return v

        # Tentar pegar das imagens (se disponível no contexto)
        imagens = info.data.get('imagens', []) or []
        if not imagens:
            return None

        # Primeiro: buscar a marcada como principal
        for img in imagens:
            e_principal = getattr(img, 'e_principal', None) if hasattr(img, 'e_principal') else (img.get('e_principal') if isinstance(img, dict) else None)
            if e_principal:
                url = getattr(img, 'url', None) if hasattr(img, 'url') else (img.get('url') if isinstance(img, dict) else None)
                if url:
                    return url

        # Fallback: retornar a primeira imagem
        img = imagens[0]
        url = getattr(img, 'url', None) if hasattr(img, 'url') else (img.get('url') if isinstance(img, dict) else None)
        return url


# Schema de resposta paginada (Sprint 1)
class ProdutosPaginadosResponse(BaseModel):
    items: List[ProdutoResponse]
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


# ==========================================
# ENDPOINTS - CATEGORIAS
# ==========================================

@router.post("/categorias", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)
def criar_categoria(
    categoria: CategoriaCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria uma nova categoria"""
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Verificar se categoria pai existe (se fornecida)
    if categoria.categoria_pai_id:
        pai = db.query(Categoria).filter(
            Categoria.id == categoria.categoria_pai_id,
            Categoria.tenant_id == tenant_id,
            Categoria.ativo == True
        ).first()
        if not pai:
            raise HTTPException(
                status_code=404,
                detail="Categoria pai nÃ£o encontrada"
            )
        
        # Verificar nÃ­vel mÃ¡ximo (4 nÃ­veis)
        nivel_pai = calcular_nivel(db, categoria.categoria_pai_id)
        if nivel_pai >= 4:
            raise HTTPException(
                status_code=400,
                detail="Limite de 4 nÃ­veis de categorias atingido"
            )
    
    # Criar categoria
    nova_categoria = Categoria(
        **categoria.model_dump(),
        tenant_id=tenant_id,
        user_id=current_user.id
    )
    
    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)
    
    return nova_categoria


@router.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(
    categoria_pai_id: Optional[int] = None,
    incluir_subcategorias: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todas as categorias (o frontend constrÃ³i a hierarquia)
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Retornar TODAS as categorias ativas do usuÃ¡rio
    # O frontend vai construir a Ã¡rvore hierÃ¡rquica
    query = db.query(Categoria).filter(
        Categoria.tenant_id == tenant_id,
        Categoria.ativo == True
    )
    
    categorias = query.order_by(Categoria.ordem, Categoria.nome).all()
    
    # Calcular nÃ­vel e contadores para cada categoria
    resultado = []
    for cat in categorias:
        cat_dict = {
            "id": cat.id,
            "nome": cat.nome,
            "descricao": cat.descricao,
            "categoria_pai_id": cat.categoria_pai_id,
            "icone": cat.icone,
            "cor": cat.cor,
            "ordem": cat.ordem,
            "ativo": cat.ativo,
            "created_at": cat.created_at,
            "updated_at": cat.updated_at,
            "nivel": calcular_nivel(db, cat.id),
            "total_filhos": db.query(Categoria).filter(
                Categoria.categoria_pai_id == cat.id,
                Categoria.ativo == True
            ).count(),
            "total_produtos": db.query(Produto).filter(
                Produto.categoria_id == cat.id
            ).count()
        }
        resultado.append(CategoriaResponse(**cat_dict))
    
    return resultado


def calcular_nivel(db: Session, categoria_id: int, nivel: int = 1) -> int:
    """Calcula o nÃ­vel de uma categoria na hierarquia"""
    categoria = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not categoria or not categoria.categoria_pai_id:
        return nivel
    return calcular_nivel(db, categoria.categoria_pai_id, nivel + 1)


@router.get("/categorias/hierarquia", response_model=List[dict])
def listar_categorias_hierarquia(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista todas as categorias em formato de Ã¡rvore hierÃ¡rquica"""
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar todas as categorias ativas
    categorias = db.query(Categoria).filter(
        Categoria.tenant_id == tenant_id,
        Categoria.ativo == True
    ).order_by(Categoria.ordem, Categoria.nome).all()
    
    # Construir Ã¡rvore
    def construir_arvore(pai_id=None):
        resultado = []
        for cat in categorias:
            if cat.categoria_pai_id == pai_id:
                item = {
                    "id": cat.id,
                    "nome": cat.nome,
                    "descricao": cat.descricao,
                    "icone": cat.icone,
                    "cor": cat.cor,
                    "ordem": cat.ordem,
                    "subcategorias": construir_arvore(cat.id)
                }
                resultado.append(item)
        return resultado
    
    return construir_arvore()


@router.get("/categorias/{categoria_id}", response_model=CategoriaResponse)
def obter_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """ObtÃ©m detalhes de uma categoria"""
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    categoria = db.query(Categoria).filter(
        Categoria.id == categoria_id,
        Categoria.tenant_id == tenant_id,
        Categoria.ativo == True
    ).first()
    
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")
    
    return categoria


@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
def atualizar_categoria(
    categoria_id: int,
    categoria_update: CategoriaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza uma categoria"""
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    categoria = db.query(Categoria).filter(
        Categoria.id == categoria_id,
        Categoria.tenant_id == tenant_id,
        Categoria.ativo == True
    ).first()
    
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")
    
    # Verificar se categoria pai existe (se fornecida e diferente)
    if categoria_update.categoria_pai_id and categoria_update.categoria_pai_id != categoria.categoria_pai_id:
        # NÃ£o permitir que categoria seja filha de si mesma
        if categoria_update.categoria_pai_id == categoria_id:
            raise HTTPException(
                status_code=400,
                detail="Categoria nÃ£o pode ser pai de si mesma"
            )
        
        pai = db.query(Categoria).filter(
            Categoria.id == categoria_update.categoria_pai_id,
            Categoria.tenant_id == tenant_id,
            Categoria.ativo == True
        ).first()
        if not pai:
            raise HTTPException(
                status_code=404,
                detail="Categoria pai nÃ£o encontrada"
            )
    
    # Atualizar campos
    for key, value in categoria_update.model_dump(exclude_unset=True).items():
        setattr(categoria, key, value)
    
    categoria.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(categoria)
    
    return categoria


@router.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deleta (soft delete) uma categoria"""
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    categoria = db.query(Categoria).filter(
        Categoria.id == categoria_id,
        Categoria.tenant_id == tenant_id,
        Categoria.ativo == True
    ).first()
    
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")
    
    # Verificar se categoria tem subcategorias
    subcategorias = db.query(Categoria).filter(
        Categoria.categoria_pai_id == categoria_id,
        Categoria.ativo == True
    ).count()
    
    if subcategorias > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria possui {subcategorias} subcategorias. Remova-as primeiro."
        )
    
    # Verificar se categoria tem produtos
    produtos_count = db.query(Produto).filter(
        Produto.categoria_id == categoria_id,
        Produto.ativo == True
    ).count()
    
    if produtos_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria possui {produtos_count} produtos. Remova-os ou mova para outra categoria primeiro."
        )
    
    # Soft delete
    categoria.ativo = False
    categoria.updated_at = datetime.utcnow()
    
    db.commit()
    
    return None


# ==========================================
# ENDPOINTS - MARCAS
# ==========================================

@router.post("/marcas", response_model=MarcaResponse, status_code=status.HTTP_201_CREATED)
def criar_marca(
    marca: MarcaCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria uma nova marca"""
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    nova_marca = Marca(
        **marca.model_dump(),
        tenant_id=tenant_id
    )
    
    db.add(nova_marca)
    db.commit()
    db.refresh(nova_marca)
    
    return nova_marca


@router.get("/marcas", response_model=List[MarcaResponse])
def listar_marcas(
    busca: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista marcas"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    query = db.query(Marca).filter(
        Marca.tenant_id == tenant_id,
        Marca.ativo == True
    )
    
    if busca:
        query = query.filter(Marca.nome.ilike(f"%{busca}%"))
    
    marcas = query.order_by(Marca.nome).all()
    
    return marcas


@router.get("/marcas/{marca_id}", response_model=MarcaResponse)
def obter_marca(
    marca_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """ObtÃ©m detalhes de uma marca"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    marca = _obter_marca_ou_404(db, marca_id, tenant_id)
    return marca


@router.put("/marcas/{marca_id}", response_model=MarcaResponse)
def atualizar_marca(
    marca_id: int,
    marca_update: MarcaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza uma marca"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    marca = _obter_marca_ou_404(db, marca_id, tenant_id)
    
    if not marca:
        raise HTTPException(status_code=404, detail="Marca nÃ£o encontrada")
    
    for key, value in marca_update.model_dump(exclude_unset=True).items():
        setattr(marca, key, value)
    
    marca.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(marca)
    
    return marca


@router.delete("/marcas/{marca_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_marca(
    marca_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deleta (soft delete) uma marca"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    marca = db.query(Marca).filter(
        Marca.id == marca_id,
        Marca.tenant_id == tenant_id,
        Marca.ativo == True
    ).first()
    
    if not marca:
        raise HTTPException(status_code=404, detail="Marca nÃ£o encontrada")
    
    # Verificar se marca tem produtos
    produtos_count = db.query(Produto).filter(
        Produto.marca_id == marca_id,
        Produto.ativo == True
    ).count()
    
    if produtos_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Marca possui {produtos_count} produtos. Remova-os ou mova para outra marca primeiro."
        )
    
    # Soft delete
    marca.ativo = False
    marca.updated_at = datetime.utcnow()
    
    db.commit()
    
    return None


# ==========================================
# ENDPOINTS - DEPARTAMENTOS
# ==========================================

@router.post("/departamentos", response_model=DepartamentoResponse, status_code=status.HTTP_201_CREATED)
def criar_departamento(
    departamento: DepartamentoCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria um novo departamento"""
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    novo_departamento = Departamento(
        **departamento.model_dump(),
        tenant_id=tenant_id
    )
    
    db.add(novo_departamento)
    db.commit()
    db.refresh(novo_departamento)
    
    return novo_departamento


@router.get("/departamentos", response_model=List[DepartamentoResponse])
def listar_departamentos(
    busca: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """Lista departamentos (rota pÃºblica)"""
    
    query = db.query(Departamento).filter(
        Departamento.ativo == True
    )
    
    if busca:
        query = query.filter(Departamento.nome.ilike(f"%{busca}%"))
    
    departamentos = query.order_by(Departamento.nome).all()
    
    return departamentos


@router.get("/departamentos/{departamento_id}", response_model=DepartamentoResponse)
def obter_departamento(
    departamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """ObtÃ©m um departamento por ID"""
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    departamento = db.query(Departamento).filter(
        Departamento.id == departamento_id,
        Departamento.tenant_id == tenant_id,
        Departamento.ativo == True
    ).first()
    
    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento nÃ£o encontrado")
    
    return departamento


@router.put("/departamentos/{departamento_id}", response_model=DepartamentoResponse)
def atualizar_departamento(
    departamento_id: int,
    departamento_update: DepartamentoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza um departamento"""
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    departamento = db.query(Departamento).filter(
        Departamento.id == departamento_id,
        Departamento.tenant_id == tenant_id,
        Departamento.ativo == True
    ).first()
    
    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento nÃ£o encontrado")
    
    for key, value in departamento_update.model_dump(exclude_unset=True).items():
        setattr(departamento, key, value)
    
    departamento.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(departamento)
    
    return departamento


@router.delete("/departamentos/{departamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_departamento(
    departamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deleta (soft delete) um departamento"""
    
    departamento = db.query(Departamento).filter(
        Departamento.id == departamento_id,
        Departamento.tenant_id == tenant_id,
        Departamento.ativo == True
    ).first()
    
    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento nÃ£o encontrado")
    
    # Verificar se departamento tem produtos
    produtos_count = db.query(Produto).filter(
        Produto.departamento_id == departamento_id,
        Produto.ativo == True
    ).count()
    
    if produtos_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Departamento possui {produtos_count} produtos. Remova-os ou mova para outro departamento primeiro."
        )
    
    # Soft delete
    departamento.ativo = False
    departamento.updated_at = datetime.utcnow()
    
    db.commit()
    
    return None


# ==========================================
# ENDPOINTS - CÃ“DIGO DE BARRAS
# ==========================================

def calcular_digito_verificador_ean13(codigo_12_digitos: str) -> str:
    """
    Calcula o dÃ­gito verificador para cÃ³digo EAN-13
    Algoritmo: MÃ³dulo 10
    """
    if len(codigo_12_digitos) != 12:
        raise ValueError("CÃ³digo deve ter exatamente 12 dÃ­gitos")
    
    # Somar dÃ­gitos nas posiÃ§Ãµes Ã­mpares (1, 3, 5...) multiplicados por 1
    soma_impar = sum(int(codigo_12_digitos[i]) for i in range(0, 12, 2))
    
    # Somar dÃ­gitos nas posiÃ§Ãµes pares (2, 4, 6...) multiplicados por 3
    soma_par = sum(int(codigo_12_digitos[i]) * 3 for i in range(1, 12, 2))
    
    # Soma total
    soma_total = soma_impar + soma_par
    
    # DÃ­gito verificador = (10 - (soma_total % 10)) % 10
    digito = (10 - (soma_total % 10)) % 10
    
    return str(digito)


def gerar_codigo_barras_ean13(sku: str) -> str:
    """
    Gera cÃ³digo de barras EAN-13 com padrÃ£o:
    789 (Brasil) + 5 dÃ­gitos aleatÃ³rios + 4 Ãºltimos dÃ­gitos do SKU + checksum
    
    Exemplo: SKU = PROD-00123 â†’ EAN-13 = 7891234501234
    """
    # Extrair apenas nÃºmeros do SKU
    numeros_sku = ''.join(filter(str.isdigit, sku))
    
    if not numeros_sku:
        # Se nÃ£o houver nÃºmeros, usar aleatÃ³rio
        numeros_sku = str(random.randint(1000, 9999))
    
    # Pegar Ãºltimos 4 dÃ­gitos
    ultimos_4_sku = numeros_sku[-4:].zfill(4)
    
    # Prefixo Brasil
    prefixo = "789"
    
    # 5 dÃ­gitos aleatÃ³rios
    meio = str(random.randint(10000, 99999))
    
    # Montar cÃ³digo de 12 dÃ­gitos
    codigo_12 = prefixo + meio + ultimos_4_sku
    
    # Calcular dÃ­gito verificador
    digito_verificador = calcular_digito_verificador_ean13(codigo_12)
    
    # CÃ³digo completo EAN-13
    codigo_ean13 = codigo_12 + digito_verificador
    
    return codigo_ean13


@router.post("/gerar-codigo-barras", response_model=GerarCodigoBarrasResponse)
def gerar_codigo_barras(
    request: GerarCodigoBarrasRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Gera cÃ³digo de barras EAN-13 Ãºnico
    Formato: 789-XXXXX-SKUU-C
    - 789: Prefixo Brasil
    - XXXXX: 5 dÃ­gitos aleatÃ³rios
    - SKUU: 4 Ãºltimos dÃ­gitos do SKU
    - C: DÃ­gito verificador
    """
    current_user, tenant_id = user_and_tenant
    
    max_tentativas = 10
    tentativa = 0
    
    while tentativa < max_tentativas:
        # Gerar cÃ³digo
        codigo = gerar_codigo_barras_ean13(request.sku)
        
        # Verificar se jÃ¡ existe
        existe = db.query(Produto).filter(
            Produto.codigo_barras == codigo,
            Produto.tenant_id == tenant_id
        ).first()
        
        if not existe:
            return GerarCodigoBarrasResponse(
                codigo_barras=codigo,
                sku_usado=request.sku,
                formato="789-XXXXX-SKUU-C (EAN-13)",
                valido=True
            )
        
        tentativa += 1
    
    raise HTTPException(
        status_code=500,
        detail="NÃ£o foi possÃ­vel gerar cÃ³digo de barras Ãºnico apÃ³s mÃºltiplas tentativas"
    )


@router.get("/validar-codigo-barras/{codigo}")
def validar_codigo_barras(
    codigo: str,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Valida um cÃ³digo de barras EAN-13"""
    
    # Remover espaÃ§os e traÃ§os
    codigo_limpo = codigo.replace(" ", "").replace("-", "")
    
    # Verificar comprimento
    if len(codigo_limpo) != 13:
        return {
            "valido": False,
            "erro": f"CÃ³digo deve ter 13 dÃ­gitos. Fornecido: {len(codigo_limpo)} dÃ­gitos"
        }
    
    # Verificar se sÃ£o apenas nÃºmeros
    if not codigo_limpo.isdigit():
        return {
            "valido": False,
            "erro": "CÃ³digo deve conter apenas nÃºmeros"
        }
    
    # Validar dÃ­gito verificador
    codigo_12 = codigo_limpo[:12]
    digito_fornecido = codigo_limpo[12]
    digito_calculado = calcular_digito_verificador_ean13(codigo_12)
    
    if digito_fornecido != digito_calculado:
        return {
            "valido": False,
            "erro": f"DÃ­gito verificador invÃ¡lido. Esperado: {digito_calculado}, Fornecido: {digito_fornecido}"
        }
    
    # Verificar se jÃ¡ existe no banco
    existe = db.query(Produto).filter(
        Produto.codigo_barras == codigo_limpo,
        Produto.tenant_id == tenant_id
    ).first()
    
    if existe:
        return {
            "valido": True,
            "existe_no_banco": True,
            "produto_id": existe.id,
            "produto_nome": existe.nome,
            "aviso": "CÃ³digo de barras jÃ¡ cadastrado para outro produto"
        }
    
    return {
        "valido": True,
        "existe_no_banco": False,
        "mensagem": "CÃ³digo de barras vÃ¡lido e disponÃ­vel"
    }


# ==========================================
# ENDPOINTS - PRODUTOS
# ==========================================

@router.post("/", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
@require_permission("produtos.criar")
def criar_produto(
    produto: ProdutoCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria um novo produto"""
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # LOG: Dados recebidos
    logger.info(f"ðŸ” Criando produto - User: {current_user.email}")
    logger.info(f"ðŸ“¦ Dados recebidos: {produto.model_dump()}")
    
    # ========================================
    # ðŸ”„ AUTO-CONVERSÃƒO: classificacao_racao='sim' â†’ tipo='raÃ§Ã£o'
    # ========================================
    if produto.classificacao_racao == 'sim':
        produto.tipo = 'raÃ§Ã£o'
        logger.info("âœ… Produto marcado como raÃ§Ã£o (classificacao_racao='sim')")
    elif produto.classificacao_racao in ['nao', 'nÃ£o', None]:
        # Se nÃ£o Ã© raÃ§Ã£o, garantir que tipo seja 'produto'
        if not produto.tipo or produto.tipo == 'raÃ§Ã£o':
            produto.tipo = 'produto'
    
    # ========================================
    # VALIDAÃ‡Ã•ES DE INFRAESTRUTURA (mantidas na rota)
    # ========================================
    
    # Verificar se SKU jÃ¡ existe
    existe_sku = db.query(Produto).filter(
        Produto.codigo == produto.codigo,
        Produto.tenant_id == tenant_id
    ).first()
    
    if existe_sku:
        raise HTTPException(
            status_code=400,
            detail=f"SKU '{produto.codigo}' jÃ¡ cadastrado"
        )
    
    # Verificar se cÃ³digo de barras jÃ¡ existe
    if produto.codigo_barras:
        existe_barcode = db.query(Produto).filter(
            Produto.codigo_barras == produto.codigo_barras,
            Produto.tenant_id == tenant_id
        ).first()
        
        if existe_barcode:
            raise HTTPException(
                status_code=400,
                detail=f"CÃ³digo de barras '{produto.codigo_barras}' jÃ¡ cadastrado"
            )
    
    # Verificar se categoria existe
    if produto.categoria_id:
        categoria = db.query(Categoria).filter(
            Categoria.id == produto.categoria_id,
            Categoria.tenant_id == tenant_id,
            Categoria.ativo == True
        ).first()
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")
    
    # Verificar se marca existe
    if produto.marca_id:
        marca = db.query(Marca).filter(
            Marca.id == produto.marca_id,
            Marca.tenant_id == tenant_id,
            Marca.ativo == True
        ).first()
        if not marca:
            raise HTTPException(status_code=404, detail="Marca nÃ£o encontrada")
    
    # ========================================
    # ðŸ”’ TRAVA 3 â€” VALIDAÃ‡ÃƒO: PRODUTO PAI NÃƒO TEM PREÃ‡O
    # ========================================
    if produto.tipo_produto == 'PAI':
        if produto.preco_venda and produto.preco_venda > 0:
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter preÃ§o de venda. O preÃ§o deve ser definido nas variaÃ§Ãµes individuais."
            )
        # Verificar estoque_atual se existir no modelo (pode nÃ£o existir em ProdutoCreate)
        estoque = getattr(produto, 'estoque_atual', None)
        if estoque and estoque > 0:
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter estoque inicial. O estoque deve ser gerenciado nas variaÃ§Ãµes."
            )
    
    # ========================================
    # ðŸ”’ VALIDAÃ‡ÃƒO: VARIAÃ‡ÃƒO DUPLICADA
    # ========================================
    # Se estÃ¡ criando uma VARIAÃ‡ÃƒO, verificar duplicidade por signature
    variation_sig = getattr(produto, 'variation_signature', None)
    if produto.produto_pai_id and variation_sig:
        variacao_existente = db.query(Produto).filter(
            Produto.tenant_id == tenant_id,
            Produto.produto_pai_id == produto.produto_pai_id,
            Produto.variation_signature == variation_sig,
            Produto.ativo == True
        ).first()
        
        if variacao_existente:
            raise HTTPException(
                status_code=409,
                detail=f"âŒ JÃ¡ existe uma variaÃ§Ã£o com os mesmos atributos para este produto. VariaÃ§Ã£o existente: '{variacao_existente.nome}' (ID: {variacao_existente.id})"
            )
    
    # ========================================
    # ðŸ”’ PREDECESSOR/SUCESSOR: Marcar predecessor como descontinuado
    # ========================================
    if produto.produto_predecessor_id:
        predecessor = db.query(Produto).filter(
            Produto.id == produto.produto_predecessor_id,
            Produto.tenant_id == tenant_id
        ).first()
        
        if not predecessor:
            raise HTTPException(
                status_code=404,
                detail="Produto predecessor nÃ£o encontrado"
            )
        
        # Marcar predecessor como descontinuado
        predecessor.data_descontinuacao = datetime.utcnow()
        if produto.motivo_descontinuacao:
            predecessor.motivo_descontinuacao = produto.motivo_descontinuacao
        else:
            predecessor.motivo_descontinuacao = f"SubstituÃ­do por: {produto.nome}"
        
        logger.info(f"ðŸ“¦ Produto predecessor {predecessor.id} marcado como descontinuado")
    
    # ========================================
    # DELEGAR PARA SERVICE LAYER
    # ========================================
    
    try:
        # Preparar dados do produto
        produto_data = produto.model_dump()
        
        # Adicionar user_id aos dados (necessÃ¡rio para o modelo)
        produto_data['user_id'] = current_user.id
        
        # Chamar service com regras de negÃ³cio
        novo_produto = ProdutoService.create_produto(
            dados=produto_data,
            db=db,
            tenant_id=tenant_id
        )
        
        logger.info(f"âœ… Produto criado com sucesso! ID: {novo_produto.id}")
        return novo_produto
        
    except ValueError as e:
        # Erros de validaÃ§Ã£o de negÃ³cio
        logger.warning(f"âš ï¸ ValidaÃ§Ã£o de negÃ³cio falhou: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"âŒ Erro ao criar produto: {str(e)}")
        logger.error(f"âŒ Tipo do erro: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar produto: {str(e)}")


# ============================================================================
# LISTAGEM DE PRODUTOS
# ============================================================================

@router.get("/vendaveis", response_model=ProdutosPaginadosResponse)
def listar_produtos_vendaveis(
    page: int = 1,
    page_size: int = 1000,
    busca: Optional[str] = None,
    categoria_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    departamento_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    estoque_baixo: Optional[bool] = False,
    em_promocao: Optional[bool] = False,
    ativo: Optional[bool] = True,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista apenas produtos VENDÃVEIS (SIMPLES, VARIACAO e KIT)
    
    Usado pelo PDV e carrinho de vendas.
    Produtos PAI nÃ£o aparecem pois nÃ£o sÃ£o vendÃ¡veis diretamente.
    """
    user, tenant_id = user_and_tenant

    # QUERY BASE - Produtos vendÃ¡veis (incluindo KIT)
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.tipo_produto.in_(['SIMPLES', 'VARIACAO', 'KIT'])  # KIT Ã© vendÃ¡vel!
    )

    # FILTROS OPCIONAIS
    if busca:
        # Busca por múltiplas palavras: todas as palavras precisam aparecer (qualquer ordem)
        # Ex: "golden castrado" acha "Ração Golden Gato Castrado Salmão"
        palavras = [p.strip() for p in busca.split() if p.strip()]
        for palavra in palavras:
            p = f"%{palavra}%"
            query = query.filter(
                (Produto.nome.ilike(p)) |
                (Produto.codigo.ilike(p)) |
                (Produto.codigo_barras.ilike(p))
            )

    if categoria_id:
        query = query.filter(Produto.categoria_id == categoria_id)
    
    if marca_id:
        query = query.filter(Produto.marca_id == marca_id)
    
    if departamento_id:
        query = query.filter(Produto.departamento_id == departamento_id)
    
    if fornecedor_id:
        # JOIN com tabela produto_fornecedores (relacionamento muitos-para-muitos)
        query = query.join(
            ProdutoFornecedor,
            Produto.id == ProdutoFornecedor.produto_id
        ).filter(
            ProdutoFornecedor.fornecedor_id == fornecedor_id,
            ProdutoFornecedor.ativo == True
        )

    if estoque_baixo:
        query = query.filter(Produto.estoque_atual <= Produto.estoque_minimo)

    if em_promocao:
        query = query.filter(
            Produto.preco_promocional.isnot(None),
            Produto.promocao_inicio <= datetime.utcnow(),
            Produto.promocao_fim >= datetime.utcnow()
        )

    # TOTAL
    total = query.count()

    # PAGINAÃ‡ÃƒO
    offset = (page - 1) * page_size
    
    # OrdenaÃ§Ã£o inteligente: prioriza match exato no cÃ³digo
    if busca:
        order_clause = [
            case(
                (Produto.codigo == busca, 1),  # Match exato no cÃ³digo
                (Produto.codigo_barras == busca, 1),  # Match exato no cÃ³digo de barras
                (Produto.codigo.ilike(f"{busca}%"), 2),  # CÃ³digo comeÃ§a com busca
                (Produto.nome.ilike(f"{busca}%"), 3),  # Nome comeÃ§a com busca
                else_=4
            ),
            Produto.nome
        ]
    else:
        order_clause = [Produto.created_at.desc()]
    
    # QUERY FINAL
    produtos = (
        query
        .options(
            joinedload(Produto.categoria),
            joinedload(Produto.marca),
            joinedload(Produto.imagens),
            joinedload(Produto.lotes)
        )
        .order_by(*order_clause)
        .offset(offset)
        .limit(page_size)
        .all()
    )
    
    produtos = [p for p in produtos if p is not None]
    
    # Processar estoque virtual para KITs e adicionar categoria_nome
    from app.services.kit_estoque_service import KitEstoqueService
    import logging
    logger = logging.getLogger(__name__)
    
    for produto in produtos:
        # ðŸ†• Adicionar categoria_nome para facilitar frontend
        if produto.categoria:
            produto.categoria_nome = produto.categoria.nome
        
        if produto.tipo_produto == 'KIT':
            try:
                # Carregar composiÃ§Ã£o do KIT
                composicao = KitEstoqueService.obter_detalhes_composicao(db, produto.id)
                produto.composicao_kit = composicao
                
                # Calcular estoque virtual (apenas para KIT VIRTUAL)
                if produto.tipo_kit == 'VIRTUAL':
                    estoque_virtual = KitEstoqueService.calcular_estoque_virtual_kit(db, produto.id)
                    produto.estoque_virtual = estoque_virtual
                else:
                    # KIT FÃSICO usa estoque prÃ³prio
                    produto.estoque_virtual = int(produto.estoque_atual or 0)
            except Exception as e:
                logger.warning(f"Erro ao processar kit {produto.id}: {e}")
                produto.composicao_kit = []
                produto.estoque_virtual = 0
    
    pages = (total + page_size - 1) // page_size

    return {
        "items": produtos,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
    }


@router.get("/", response_model=ProdutosPaginadosResponse)
@require_permission("produtos.visualizar")
def listar_produtos(
    page: int = 1,
    page_size: int = 1000,  # forÃ§a trazer tudo
    busca: Optional[str] = None,
    categoria_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    departamento_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    estoque_baixo: Optional[bool] = False,
    em_promocao: Optional[bool] = False,
    ativo: Optional[bool] = True,
    tipo_produto: Optional[str] = None,  # Filtro por tipo de produto
    produto_predecessor_id: Optional[int] = None,  # Buscar sucessores de um produto
    include_variations: Optional[bool] = False,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista produtos com hierarquia PAI > FILHOS
    
    REGRA DE NEGÃ“CIO (Sprint 2 + KIT - Atualizada):
    - Produtos PAI aparecem na listagem com suas variaÃ§Ãµes agrupadas
    - Produtos SIMPLES aparecem normalmente
    - Produtos KIT aparecem normalmente
    - Produtos VARIACAO aparecem apenas dentro do grupo do PAI
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # QUERY BASE - Buscar apenas produtos principais (SIMPLES, PAI e KIT)
    # VARIACAO nÃ£o aparecem sozinhas, apenas agrupadas com o PAI
    # EXCEÃ‡ÃƒO: Se filtrar explicitamente por tipo_produto, respeita o filtro
    # EXCEÃ‡ÃƒO 2: Se filtrar por produto_predecessor_id, buscar apenas sucessores (qualquer tipo)
    if produto_predecessor_id:
        # Buscar produtos que sÃ£o sucessores do produto especificado
        query = db.query(Produto).filter(
            Produto.tenant_id == tenant_id,
            Produto.produto_predecessor_id == produto_predecessor_id
        )
    elif tipo_produto:
        query = db.query(Produto).filter(
            Produto.tenant_id == tenant_id,
            Produto.tipo_produto == tipo_produto  # Filtro especÃ­fico
        )
    else:
        query = db.query(Produto).filter(
            Produto.tenant_id == tenant_id,
            Produto.tipo_produto.in_(['SIMPLES', 'PAI', 'KIT'])  # Sprint 2 + KIT: Mostrar SIMPLES, PAI e KIT
        )
    
    # Aplicar filtro de ativo (se especificado)
    # Se ativo=None, mostra todos (ativos e inativos)
    # Se ativo=True, mostra apenas ativos
    # Se ativo=False, mostra apenas inativos
    if ativo is not None:
        if ativo:
            query = query.filter(or_(Produto.ativo.is_(True), Produto.ativo.is_(None)))
        else:
            query = query.filter(Produto.ativo.is_(False))

    # FILTROS OPCIONAIS
    if busca:
        busca_pattern = f"%{busca}%"
        query = query.filter(
            (Produto.nome.ilike(busca_pattern)) |
            (Produto.codigo.ilike(busca_pattern)) |
            (Produto.codigo_barras.ilike(busca_pattern))
        )
    
    if categoria_id:
        query = query.filter(Produto.categoria_id == categoria_id)
    
    if marca_id:
        query = query.filter(Produto.marca_id == marca_id)
    
    if departamento_id:
        query = query.filter(Produto.departamento_id == departamento_id)
    
    if fornecedor_id:
        # JOIN com tabela produto_fornecedores (relacionamento muitos-para-muitos)
        query = query.join(
            ProdutoFornecedor, 
            Produto.id == ProdutoFornecedor.produto_id
        ).filter(
            ProdutoFornecedor.fornecedor_id == fornecedor_id,
            ProdutoFornecedor.ativo == True
        )

    if estoque_baixo:
        query = query.filter(Produto.estoque_atual <= Produto.estoque_minimo)

    if em_promocao:
        query = query.filter(
            Produto.preco_promocional.isnot(None),
            Produto.promocao_inicio <= datetime.utcnow(),
            Produto.promocao_fim >= datetime.utcnow()
        )

    # TOTAL
    total = query.count()
    
    logger.info(f"ðŸ“¦ GET /produtos/ - Total encontrado: {total} | Tenant: {tenant_id}")

    # PAGINAÃ‡ÃƒO
    offset = (page - 1) * page_size
    
    # QUERY FINAL COM RELACIONAMENTOS
    produtos = (
        query
        .options(
            joinedload(Produto.categoria),
            joinedload(Produto.marca),
            joinedload(Produto.imagens),
            joinedload(Produto.lotes)
        )
        .order_by(Produto.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    
    # Filtro de seguranÃ§a: remover None
    produtos = [p for p in produtos if p is not None]
    
    # HIERARQUIA: Para produtos PAI, buscar suas variaÃ§Ãµes
    # Para produtos KIT, calcular estoque virtual e carregar composiÃ§Ã£o
    produtos_expandidos = []
    for produto in produtos:
        # Se for PAI, contar variaÃ§Ãµes antes de adicionar
        if produto.tipo_produto == 'PAI':
            total_variacoes = db.query(func.count(Produto.id)).filter(
                Produto.produto_pai_id == produto.id,
                Produto.tipo_produto == 'VARIACAO',
                Produto.ativo == True
            ).scalar()
            produto.total_variacoes = total_variacoes or 0
        
        # Se for KIT, processar composiÃ§Ã£o e estoque
        if produto.tipo_produto == 'KIT':
            try:
                # âš ï¸ TEMPORÃRIO: Desabilitado para evitar timeout
                # Carregar composiÃ§Ã£o do KIT
                # composicao = KitEstoqueService.obter_detalhes_composicao(db, produto.id)
                produto.composicao_kit = []
                
                # Calcular estoque virtual (apenas para KIT VIRTUAL)
                if produto.tipo_kit == 'VIRTUAL':
                    # estoque_virtual = KitEstoqueService.calcular_estoque_virtual_kit(db, produto.id)
                    # produto.estoque_virtual = estoque_virtual
                    produto.estoque_virtual = 0  # TemporÃ¡rio
                else:
                    # KIT FÃSICO usa estoque prÃ³prio
                    produto.estoque_virtual = int(produto.estoque_atual or 0)
            except Exception as e:
                logger.warning(f"Erro ao processar kit {produto.id}: {e}")
                produto.composicao_kit = []
                produto.estoque_virtual = 0
        
        produtos_expandidos.append(produto)
        
        # Se for PAI, buscar e incluir suas variaÃ§Ãµes logo apÃ³s
        if produto.tipo_produto == 'PAI':
            variacoes = db.query(Produto).filter(
                Produto.produto_pai_id == produto.id,
                Produto.tipo_produto == 'VARIACAO',
                Produto.ativo == True
            ).options(
                joinedload(Produto.imagens),
                joinedload(Produto.lotes)
            ).order_by(Produto.nome).all()
            
            # Adicionar variaÃ§Ãµes logo apÃ³s o PAI
            produtos_expandidos.extend(variacoes)
    
    pages = (total + page_size - 1) // page_size

    return {
        "items": produtos_expandidos,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
    }


@router.get("/{produto_id}/variacoes", response_model=List[ProdutoResponse])
def listar_variacoes_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todas as variaÃ§Ãµes de um produto PAI
    
    Sprint 2: Lazy load de variaÃ§Ãµes
    - Usado para expandir produto PAI na listagem
    - Retorna apenas produtos filhos (tipo_produto = 'VARIACAO')
    - Ordenado por nome
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Verificar se produto existe e Ã© PAI
    produto_pai = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto_pai:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    if produto_pai.tipo_produto != 'PAI':
        raise HTTPException(
            status_code=400,
            detail="Produto nÃ£o Ã© do tipo PAI (nÃ£o possui variaÃ§Ãµes)"
        )
    
    # Buscar variaÃ§Ãµes
    variacoes = db.query(Produto).filter(
        Produto.produto_pai_id == produto_id,
        Produto.tipo_produto == 'VARIACAO',
        Produto.ativo == True,  # Filtrar apenas variaÃ§Ãµes ativas
        Produto.tenant_id == tenant_id
    ).options(
        joinedload(Produto.imagens),
        joinedload(Produto.lotes)
    ).order_by(Produto.nome).all()
    
    logger.info(f"ðŸ“¦ Produto PAI #{produto_id} possui {len(variacoes)} variaÃ§Ãµes ativas")
    
    return variacoes


@router.get("/{produto_id}/variacoes/excluidas", response_model=List[ProdutoResponse])
def listar_variacoes_excluidas(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista variaÃ§Ãµes excluÃ­das (soft-deleted) de um produto PAI
    Permite visualizar, restaurar ou excluir definitivamente
    """
    
    # Verificar se produto existe e Ã© PAI
    produto_pai = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto_pai:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    if produto_pai.tipo_produto != 'PAI':
        raise HTTPException(
            status_code=400,
            detail="Produto nÃ£o Ã© do tipo PAI (nÃ£o possui variaÃ§Ãµes)"
        )
    
    # Buscar variaÃ§Ãµes excluÃ­das
    variacoes_excluidas = db.query(Produto).filter(
        Produto.produto_pai_id == produto_id,
        Produto.tipo_produto == 'VARIACAO',
        Produto.ativo == False,  # Apenas inativas (excluÃ­das)
        Produto.tenant_id == tenant_id
    ).options(
        joinedload(Produto.imagens),
        joinedload(Produto.lotes)
    ).order_by(Produto.updated_at.desc()).all()
    
    logger.info(f"ðŸ—‘ï¸ Produto PAI #{produto_id} possui {len(variacoes_excluidas)} variaÃ§Ãµes excluÃ­das")
    
    return variacoes_excluidas


@router.patch("/{produto_id}/restaurar", response_model=ProdutoResponse)
def restaurar_variacao(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Restaura uma variaÃ§Ã£o excluÃ­da (reativa)
    """
    
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id,
        Produto.tipo_produto == 'VARIACAO'
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="VariaÃ§Ã£o nÃ£o encontrada")
    
    if produto.ativo:
        raise HTTPException(status_code=400, detail="VariaÃ§Ã£o jÃ¡ estÃ¡ ativa")
    
    # Restaurar
    produto.ativo = True
    produto.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(produto)
    
    logger.info(f"â™»ï¸ VariaÃ§Ã£o #{produto_id} restaurada com sucesso")
    
    return produto


@router.delete("/{produto_id}/permanente", status_code=status.HTTP_204_NO_CONTENT)
def excluir_variacao_permanentemente(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Exclui DEFINITIVAMENTE uma variaÃ§Ã£o do banco de dados
    ATENÃ‡ÃƒO: Esta aÃ§Ã£o Ã© irreversÃ­vel!
    """
    
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id,
        Produto.tipo_produto == 'VARIACAO'
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="VariaÃ§Ã£o nÃ£o encontrada")
    
    if produto.ativo:
        raise HTTPException(
            status_code=400, 
            detail="NÃ£o Ã© possÃ­vel excluir permanentemente uma variaÃ§Ã£o ativa. Exclua-a primeiro (soft delete)."
        )
    
    # Excluir DEFINITIVAMENTE
    db.delete(produto)
    db.commit()
    
    logger.warning(f"âš ï¸ VariaÃ§Ã£o #{produto_id} EXCLUÃDA PERMANENTEMENTE do banco de dados")
    
    return None


@router.get("/{produto_id}", response_model=ProdutoResponse)
def obter_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    ObtÃ©m detalhes completos de um produto
    
    Para produtos do tipo KIT:
    - Retorna composicao_kit (lista de componentes)
    - Retorna estoque_virtual (calculado automaticamente se tipo_kit=VIRTUAL)
    """
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).options(
        joinedload(Produto.imagens),
        joinedload(Produto.categoria),
        joinedload(Produto.marca)
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    # Preparar resposta base
    response_data = {
        **produto.__dict__,
        'categoria': produto.categoria,
        'marca': produto.marca,
        'imagens': produto.imagens,
        'lotes': produto.lotes,
        'composicao_kit': [],
        'estoque_virtual': None
    }
    
    # ========================================
    # PROCESSAR PRODUTOS DO TIPO KIT
    # ========================================
    if produto.tipo_produto == 'KIT':
        from .services.kit_estoque_service import KitEstoqueService
        
        # Buscar composiÃ§Ã£o do KIT
        composicao = KitEstoqueService.obter_detalhes_composicao(db, produto_id)
        response_data['composicao_kit'] = composicao
        
        # Calcular estoque virtual (se for KIT VIRTUAL)
        if produto.tipo_kit == 'VIRTUAL':
            estoque_virtual = KitEstoqueService.calcular_estoque_virtual_kit(db, produto_id)
            response_data['estoque_virtual'] = estoque_virtual
            logger.info(f"ðŸ§© Kit #{produto_id}: estoque_virtual={estoque_virtual}")
        else:
            # KIT FÃSICO usa estoque prÃ³prio
            response_data['estoque_virtual'] = int(produto.estoque_atual or 0)
    
    # Mapear tipo_kit para e_kit_fisico (compatibilidade com frontend)
    response_data['e_kit_fisico'] = (produto.tipo_kit == 'FISICO')
    
    return response_data


@router.put("/{produto_id}", response_model=ProdutoResponse)
@require_permission("produtos.editar")
def atualizar_produto(
    produto_id: int,
    produto_update: ProdutoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualiza um produto
    
    Para produtos KIT:
    - Pode atualizar composicao_kit (diff inteligente)
    - Pode alterar tipo_kit (VIRTUAL <-> FISICO)
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    # Verificar se novo SKU jÃ¡ existe
    if produto_update.codigo and produto_update.codigo != produto.codigo:
        existe_sku = db.query(Produto).filter(
            Produto.codigo == produto_update.codigo,
            Produto.tenant_id == tenant_id,
            Produto.id != produto_id
        ).first()
        
        if existe_sku:
            raise HTTPException(
                status_code=400,
                detail=f"SKU '{produto_update.codigo}' jÃ¡ cadastrado"
            )
    
    # Verificar se novo cÃ³digo de barras jÃ¡ existe
    if produto_update.codigo_barras and produto_update.codigo_barras != produto.codigo_barras:
        existe_barcode = db.query(Produto).filter(
            Produto.codigo_barras == produto_update.codigo_barras,
            Produto.tenant_id == tenant_id,
            Produto.id != produto_id
        ).first()
        
        if existe_barcode:
            raise HTTPException(
                status_code=400,
                detail=f"CÃ³digo de barras '{produto_update.codigo_barras}' jÃ¡ cadastrado"
            )
    
    # Extrair dados
    dados_recebidos = produto_update.model_dump(exclude_unset=True)
    composicao_kit = dados_recebidos.pop('composicao_kit', None)
    
    # ========================================
    # ï¿½ AUTO-CONVERSÃƒO: classificacao_racao='sim' â†’ tipo='raÃ§Ã£o'
    # ========================================
    if 'classificacao_racao' in dados_recebidos:
        if dados_recebidos['classificacao_racao'] == 'sim':
            dados_recebidos['tipo'] = 'raÃ§Ã£o'
            logger.info(f"âœ… Produto {produto_id} marcado como raÃ§Ã£o (classificacao_racao='sim')")
        elif dados_recebidos['classificacao_racao'] in ['nao', 'nÃ£o', None]:
            # Se nÃ£o Ã© raÃ§Ã£o, garantir que tipo seja 'produto'
            dados_recebidos['tipo'] = 'produto'
            logger.info(f"âœ… Produto {produto_id} desmarcado como raÃ§Ã£o")
    
    # ========================================
    # ï¿½ðŸ”’ TRAVA 3 â€” VALIDAÃ‡ÃƒO: PRODUTO PAI NÃƒO TEM PREÃ‡O (ATUALIZAÃ‡ÃƒO)
    # ========================================
    is_parent_atual = produto.is_parent
    is_parent_novo = dados_recebidos.get('is_parent', is_parent_atual)
    
    if is_parent_novo:
        # Bloquear alteraÃ§Ã£o de preÃ§o em produto PAI
        if 'preco_venda' in dados_recebidos and dados_recebidos['preco_venda'] and dados_recebidos['preco_venda'] > 0:
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter preÃ§o de venda. O preÃ§o deve ser definido nas variaÃ§Ãµes individuais."
            )
        
        # Bloquear alteraÃ§Ã£o de estoque em produto PAI
        if 'estoque_atual' in dados_recebidos and dados_recebidos['estoque_atual'] and dados_recebidos['estoque_atual'] > 0:
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter estoque. O estoque deve ser gerenciado nas variaÃ§Ãµes."
            )
    
    # ========================================
    # ðŸ”’ VALIDAÃ‡ÃƒO: VARIAÃ‡ÃƒO DUPLICADA (ATUALIZAÃ‡ÃƒO)
    # ========================================
    # Se estÃ¡ atualizando signature de uma VARIAÃ‡ÃƒO, verificar duplicidade
    if 'variation_signature' in dados_recebidos and dados_recebidos['variation_signature']:
        variacao_existente = db.query(Produto).filter(
            Produto.tenant_id == tenant_id,
            Produto.produto_pai_id == produto.produto_pai_id,
            Produto.variation_signature == dados_recebidos['variation_signature'],
            Produto.id != produto_id,  # Excluir o prÃ³prio produto
            Produto.ativo == True
        ).first()
        
        if variacao_existente:
            raise HTTPException(
                status_code=409,
                detail=f"âŒ JÃ¡ existe uma variaÃ§Ã£o com os mesmos atributos para este produto. VariaÃ§Ã£o existente: '{variacao_existente.nome}' (ID: {variacao_existente.id})"
            )
    
    # ========================================
    # ATUALIZAR COMPOSIÃ‡ÃƒO DO KIT (se enviado)
    # ========================================
    if composicao_kit is not None and produto.tipo_produto == 'KIT':
        from .services.kit_estoque_service import KitEstoqueService
        
        # âš ï¸ VALIDAÃ‡ÃƒO OBRIGATÃ“RIA: KIT deve ter pelo menos 1 componente
        if len(composicao_kit) == 0:
            raise HTTPException(
                status_code=400, 
                detail="Produto do tipo KIT deve ter pelo menos 1 componente na composiÃ§Ã£o. Adicione os produtos que fazem parte do kit antes de salvar."
            )
        
        # Validar novos componentes
        valido, erro = KitEstoqueService.validar_componentes_kit(
            db=db,
            kit_id=produto_id,
            componentes=composicao_kit
        )
        
        if not valido:
            raise HTTPException(status_code=400, detail=f"ComposiÃ§Ã£o invÃ¡lida: {erro}")
        
        # Remover componentes antigos
        db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.kit_id == produto_id
        ).delete()
        
        # Adicionar novos componentes
        for comp in composicao_kit:
            novo_comp = ProdutoKitComponente(
                kit_id=produto_id,
                produto_componente_id=comp.get('produto_componente_id'),
                quantidade=comp.get('quantidade', 1.0),
                ordem=comp.get('ordem', 0),
                opcional=comp.get('opcional', False)
            )
            db.add(novo_comp)
        
        logger.info(f"ðŸ§© ComposiÃ§Ã£o do Kit #{produto_id} atualizada: {len(composicao_kit)} componentes")
    
    # ========================================
    # PROCESSAR e_kit_fisico -> tipo_kit
    # ========================================
    if 'e_kit_fisico' in dados_recebidos:
        e_kit_fisico = dados_recebidos.pop('e_kit_fisico')
        dados_recebidos['tipo_kit'] = 'FISICO' if e_kit_fisico else 'VIRTUAL'
    
    # ========================================
    # ATUALIZAR CAMPOS DO PRODUTO
    # ========================================
    for key, value in dados_recebidos.items():
        setattr(produto, key, value)
    
    produto.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(produto)
        logger.info(f"âœ… Produto #{produto_id} atualizado com sucesso")

        # Notificar clientes "Avise-me" se estoque voltou ao positivo
        if 'estoque_atual' in dados_recebidos and produto.estoque_atual and produto.estoque_atual > 0:
            try:
                from app.routes.ecommerce_notify_routes import notificar_clientes_estoque_disponivel
                notificar_clientes_estoque_disponivel(db, str(tenant_id), produto_id, produto.nome)
            except Exception as _notify_err:
                logger.warning(f"Aviso: erro ao enviar notificacoes avise-me: {_notify_err}")
        
        # Retornar com composiÃ§Ã£o e estoque virtual
        return obter_produto(produto_id, db, user_and_tenant)
        
    except Exception as e:
        db.rollback()
        logger.error(f"âŒ Erro ao atualizar produto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar produto: {str(e)}")


# ============================================================================
# ATUALIZAÃ‡ÃƒO EM LOTE
# ============================================================================

class AtualizacaoLoteRequest(BaseModel):
    produto_ids: List[int]
    marca_id: Optional[int] = None
    categoria_id: Optional[int] = None
    departamento_id: Optional[int] = None


@router.patch("/atualizar-lote")
def atualizar_produtos_lote(
    dados: AtualizacaoLoteRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza marca, categoria e/ou departamento de mÃºltiplos produtos"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    logger.info(f"ðŸ“¦ Atualizando {len(dados.produto_ids)} produtos em lote")
    
    # Buscar produtos
    produtos = db.query(Produto).filter(
        Produto.id.in_(dados.produto_ids),
        Produto.tenant_id == tenant_id
    ).all()
    
    if not produtos:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado")
    
    # Validar se todos os produtos pertencem ao usuÃ¡rio
    if len(produtos) != len(dados.produto_ids):
        raise HTTPException(
            status_code=400, 
            detail="Alguns produtos nÃ£o foram encontrados ou nÃ£o pertencem ao usuÃ¡rio"
        )
    
    # Atualizar campos fornecidos
    atualizado = 0
    for produto in produtos:
        if dados.marca_id is not None:
            produto.marca_id = dados.marca_id
            atualizado += 1
        if dados.categoria_id is not None:
            produto.categoria_id = dados.categoria_id
            atualizado += 1
        if dados.departamento_id is not None:
            produto.departamento_id = dados.departamento_id
            atualizado += 1
        
        produto.updated_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"âœ… {len(produtos)} produtos atualizados em lote")
    
    return {
        "produtos_atualizados": len(produtos),
        "campos_atualizados": atualizado,
        "marca_id": dados.marca_id,
        "categoria_id": dados.categoria_id,
        "departamento_id": dados.departamento_id
    }


@router.patch("/{produto_id}")
def atualizar_preco_produto(
    produto_id: int,
    preco_venda: Optional[float] = None,
    preco_custo: Optional[float] = None,
    preco_promocional: Optional[float] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza apenas o preÃ§o de um produto (ediÃ§Ã£o rÃ¡pida)"""
    
    current_user, tenant_id = user_and_tenant
    logger.info(f"ðŸ·ï¸ Atualizando preÃ§o do produto {produto_id}")
    
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    # Atualizar apenas os preÃ§os fornecidos
    if preco_venda is not None:
        produto.preco_venda = preco_venda
    if preco_custo is not None:
        produto.preco_custo = preco_custo
    if preco_promocional is not None:
        produto.preco_promocional = preco_promocional
    
    produto.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(produto)
    
    logger.info(f"âœ… PreÃ§o atualizado: PV={produto.preco_venda}")
    
    return {
        "id": produto.id,
        "preco_venda": produto.preco_venda,
        "preco_custo": produto.preco_custo,
        "preco_promocional": produto.preco_promocional
    }


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Deleta (soft delete) um produto"""
    
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    # ========================================
    # ðŸ”’ TRAVA 4 â€” VALIDAÃ‡ÃƒO: PRODUTO PAI COM VARIAÃ‡Ã•ES NÃƒO PODE SER EXCLUÃDO
    # ========================================
    if produto.is_parent:
        # Verificar se existem variaÃ§Ãµes ativas
        variacoes_ativas = db.query(Produto).filter(
            Produto.produto_pai_id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo == True
        ).count()
        
        if variacoes_ativas > 0:
            raise HTTPException(
                status_code=409,
                detail=f"âŒ Produto '{produto.nome}' possui {variacoes_ativas} variaÃ§Ã£o(Ãµes) ativa(s) e nÃ£o pode ser excluÃ­do. Exclua primeiro todas as variaÃ§Ãµes."
            )
    
    # Soft delete
    produto.ativo = False
    produto.updated_at = datetime.utcnow()
    
    db.commit()
    
    return None


@router.post("/gerar-sku")
def gerar_sku(
    prefixo: str = "PROD",
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Gera um SKU Ãºnico automaticamente
    Formato: {PREFIXO}-{NÃšMERO_SEQUENCIAL}
    Exemplo: PROD-00001
    """
    current_user, tenant_id = user_and_tenant
    
    # Buscar Ãºltimo SKU com o mesmo prefixo
    ultimo_produto = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.codigo.like(f"{prefixo}-%")
    ).order_by(Produto.id.desc()).first()
    
    if ultimo_produto:
        # Extrair nÃºmero do Ãºltimo SKU
        try:
            ultimo_numero = int(ultimo_produto.codigo.split("-")[-1])
            proximo_numero = ultimo_numero + 1
        except ValueError:
            # Se nÃ£o conseguir extrair, comeÃ§ar do 1
            proximo_numero = 1
    else:
        proximo_numero = 1
    
    # Gerar novo SKU
    novo_sku = f"{prefixo}-{proximo_numero:05d}"
    
    # Verificar se jÃ¡ existe (caso de race condition)
    existe = db.query(Produto).filter(
        Produto.codigo == novo_sku,
        Produto.tenant_id == tenant_id
    ).first()
    
    if existe:
        # Se existir, tentar prÃ³ximo nÃºmero
        novo_sku = f"{prefixo}-{proximo_numero + 1:05d}"
    
    return {
        "sku": novo_sku,
        "prefixo": prefixo,
        "numero": proximo_numero,
        "disponivel": True
    }


# ==========================================
# ENDPOINTS - LOTES E FIFO
# ==========================================

@router.post("/{produto_id}/lotes", response_model=LoteResponse, status_code=status.HTTP_201_CREATED)
def criar_lote(
    produto_id: int,
    lote: LoteCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Cria um novo lote para o produto"""
    
    # Verificar se produto existe
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id,
        Produto.ativo == True
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    # Verificar se nÃºmero de lote jÃ¡ existe para este produto
    lote_existente = db.query(ProdutoLote).filter(
        ProdutoLote.produto_id == produto_id,
        ProdutoLote.nome_lote == lote.nome_lote
    ).first()
    
    if lote_existente:
        raise HTTPException(
            status_code=400,
            detail=f"Lote '{lote.nome_lote}' jÃ¡ cadastrado para este produto"
        )
    
    # Criar lote com timestamp para FIFO
    import time
    novo_lote = ProdutoLote(
        **lote.model_dump(),
        produto_id=produto_id,
        quantidade_disponivel=lote.quantidade,
        ordem_entrada=int(time.time())  # Unix timestamp para FIFO
    )
    
    db.add(novo_lote)
    
    # Atualizar estoque do produto
    produto.estoque_atual += lote.quantidade
    produto.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(novo_lote)
    
    return novo_lote


@router.get("/{produto_id}/lotes", response_model=List[LoteResponse])
def listar_lotes(
    produto_id: int,
    apenas_disponiveis: bool = False,  # Mostrar todos por padrÃ£o
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Lista lotes de um produto"""
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    logger.info(f"ðŸ“¦ Listando lotes do produto {produto_id} - apenas_disponiveis={apenas_disponiveis}")
    
    # Verificar se produto existe
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    query = db.query(ProdutoLote).filter(
        ProdutoLote.produto_id == produto_id,
        ProdutoLote.status != 'excluido'  # Apenas lotes nÃ£o excluÃ­dos
    )
    
    if apenas_disponiveis:
        query = query.filter(ProdutoLote.quantidade_disponivel > 0)
    
    # Ordenar por FIFO (mais antigo primeiro)
    lotes = query.order_by(ProdutoLote.ordem_entrada).all()
    
    logger.info(f"âœ… Encontrados {len(lotes)} lotes")
    
    return lotes


@router.put("/{produto_id}/lotes/{lote_id}", response_model=LoteResponse)
def atualizar_lote(
    produto_id: int,
    lote_id: int,
    lote_data: LoteBase,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Atualiza informaÃ§Ãµes de um lote"""
    
    # Buscar lote
    lote = db.query(ProdutoLote).filter(
        ProdutoLote.id == lote_id,
        ProdutoLote.produto_id == produto_id
    ).first()
    
    if not lote:
        raise HTTPException(status_code=404, detail="Lote nÃ£o encontrado")
    
    # Verificar se o produto pertence ao usuÃ¡rio
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    # Calcular diferenÃ§a de quantidade para ajustar estoque
    diferenca_quantidade = lote_data.quantidade_inicial - lote.quantidade_inicial
    
    # Atualizar campos
    lote.nome_lote = lote_data.nome_lote
    lote.quantidade_inicial = lote_data.quantidade_inicial
    lote.quantidade_disponivel = lote.quantidade_disponivel + diferenca_quantidade
    lote.data_fabricacao = lote_data.data_fabricacao
    lote.data_validade = lote_data.data_validade
    lote.custo_unitario = lote_data.custo_unitario
    
    # Atualizar estoque do produto
    produto.estoque_atual = produto.estoque_atual + diferenca_quantidade
    
    db.commit()
    db.refresh(lote)
    
    return lote


@router.delete("/{produto_id}/lotes/{lote_id}")
def excluir_lote(
    produto_id: int,
    lote_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Exclui um lote (soft delete)"""
    
    # Buscar lote
    lote = db.query(ProdutoLote).filter(
        ProdutoLote.id == lote_id,
        ProdutoLote.produto_id == produto_id
    ).first()
    
    if not lote:
        raise HTTPException(status_code=404, detail="Lote nÃ£o encontrado")
    
    # Verificar se o produto pertence ao usuÃ¡rio
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    # Atualizar estoque do produto (remover a quantidade do lote)
    produto.estoque_atual = produto.estoque_atual - lote.quantidade_disponivel
    
    # Soft delete - marcar como excluÃ­do
    lote.status = 'excluido'
    lote.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Lote excluÃ­do com sucesso"}


@router.post("/{produto_id}/entrada")
def entrada_estoque(
    produto_id: int,
    entrada: EntradaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Registra entrada de estoque criando um lote"""
    
    # Verificar se produto existe
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id,
        Produto.ativo == True
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    # VALIDAÃ‡ÃƒO: Produto PAI nÃ£o pode ter movimentaÃ§Ã£o de estoque
    if produto.is_parent:
        raise HTTPException(
            status_code=400,
            detail="Produto pai nÃ£o pode ter entrada de estoque. Realize a entrada nas variaÃ§Ãµes do produto."
        )
    
    # Verificar se lote jÃ¡ existe
    lote_existente = db.query(ProdutoLote).filter(
        ProdutoLote.produto_id == produto_id,
        ProdutoLote.nome_lote == entrada.nome_lote
    ).first()
    
    if lote_existente:
        # Se lote existe, adicionar quantidade
        lote_existente.quantidade_inicial += entrada.quantidade
        lote_existente.quantidade_disponivel += entrada.quantidade
        lote = lote_existente
    else:
        # Criar novo lote
        import time
        lote = ProdutoLote(
            produto_id=produto_id,
            nome_lote=entrada.nome_lote,
            quantidade_inicial=entrada.quantidade,
            quantidade_disponivel=entrada.quantidade,
            data_fabricacao=entrada.data_fabricacao,
            data_validade=entrada.data_validade or datetime.utcnow() + timedelta(days=365),  # Validade padrÃ£o 1 ano
            custo_unitario=entrada.preco_custo,
            ordem_entrada=int(time.time())
        )
        db.add(lote)
    
    # Atualizar estoque do produto
    estoque_anterior = produto.estoque_atual
    produto.estoque_atual += entrada.quantidade
    produto.updated_at = datetime.utcnow()
    
    # Registrar movimentaÃ§Ã£o
    movimentacao = EstoqueMovimentacao(
        produto_id=produto_id,
        tipo="entrada",
        motivo="compra",
        quantidade=entrada.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=produto.estoque_atual,
        custo_unitario=entrada.preco_custo,
        lote_id=lote.id,
        observacao=entrada.observacoes,
        tenant_id=tenant_id
    )
    db.add(movimentacao)
    
    db.commit()
    db.refresh(lote)
    
    return {
        "sucesso": True,
        "mensagem": "Entrada registrada com sucesso",
        "lote_id": lote.id,
        "nome_lote": lote.nome_lote,
        "quantidade_entrada": entrada.quantidade,
        "estoque_atual": produto.estoque_atual
    }


@router.post("/{produto_id}/saida-fifo")
def saida_estoque_fifo(
    produto_id: int,
    saida: SaidaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Registra saÃ­da de estoque usando FIFO
    Consome lotes mais antigos primeiro
    """
    
    # Verificar se produto existe
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id,
        Produto.ativo == True
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    # VALIDAÃ‡ÃƒO: Produto PAI nÃ£o pode ter movimentaÃ§Ã£o de estoque
    if produto.is_parent:
        raise HTTPException(
            status_code=400,
            detail="Produto pai nÃ£o pode ter saÃ­da de estoque. Realize a saÃ­da nas variaÃ§Ãµes do produto."
        )
    
    # Verificar se hÃ¡ estoque suficiente
    if produto.estoque_atual < saida.quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque insuficiente. DisponÃ­vel: {produto.estoque_atual}, Solicitado: {saida.quantidade}"
        )
    
    # Buscar lotes disponÃ­veis ordenados por FIFO (mais antigo primeiro)
    lotes = db.query(ProdutoLote).filter(
        ProdutoLote.produto_id == produto_id,
        ProdutoLote.quantidade_disponivel > 0
    ).order_by(ProdutoLote.ordem_entrada).all()
    
    if not lotes:
        raise HTTPException(
            status_code=400,
            detail="Nenhum lote disponÃ­vel"
        )
    
    # Consumir lotes usando FIFO
    quantidade_restante = saida.quantidade
    lotes_consumidos = []
    
    for lote in lotes:
        if quantidade_restante <= 0:
            break
        
        if lote.quantidade_disponivel >= quantidade_restante:
            # Este lote tem quantidade suficiente
            lote.quantidade_disponivel -= quantidade_restante
            lotes_consumidos.append({
                "lote_id": lote.id,
                "nome_lote": lote.nome_lote,
                "quantidade_consumida": quantidade_restante,
                "data_validade": lote.data_validade.isoformat() if lote.data_validade else None
            })
            quantidade_restante = 0
        else:
            # Consumir todo este lote e continuar
            quantidade_consumida = lote.quantidade_disponivel
            lotes_consumidos.append({
                "lote_id": lote.id,
                "nome_lote": lote.nome_lote,
                "quantidade_consumida": quantidade_consumida,
                "data_validade": lote.data_validade.isoformat() if lote.data_validade else None
            })
            quantidade_restante -= quantidade_consumida
            lote.quantidade_disponivel = 0
    
    # Atualizar estoque do produto
    estoque_anterior = produto.estoque_atual
    produto.estoque_atual -= saida.quantidade
    produto.updated_at = datetime.utcnow()
    
    # Registrar movimentaÃ§Ã£o
    import json
    movimentacao = EstoqueMovimentacao(
        produto_id=produto_id,
        tipo_movimentacao=saida.motivo,
        quantidade=saida.quantidade,
        estoque_anterior=estoque_anterior,
        estoque_resultante=produto.estoque_atual,
        numero_pedido=saida.numero_pedido,
        observacoes=saida.observacoes,
        usuario=current_user.nome,
        lotes_consumidos=json.dumps(lotes_consumidos)
    )
    db.add(movimentacao)
    
    db.commit()
    
    return {
        "sucesso": True,
        "mensagem": "SaÃ­da registrada com sucesso usando FIFO",
        "quantidade_saida": saida.quantidade,
        "estoque_anterior": estoque_anterior,
        "estoque_atual": produto.estoque_atual,
        "lotes_consumidos": lotes_consumidos,
        "numero_pedido": saida.numero_pedido
    }


# ==========================================
# ENDPOINTS - RELATÃ“RIOS
# ==========================================

@router.get("/relatorio/movimentacoes")
def relatorio_movimentacoes(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    produto_id: Optional[str] = None,  # String para aceitar "" vazio
    tipo_movimentacao: Optional[str] = None,
    agrupar_por_mes: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    RelatÃ³rio de movimentaÃ§Ãµes de estoque
    Retorna histÃ³rico com filtros de perÃ­odo, produto e tipo
    Inclui nÃºmero de pedido clicÃ¡vel para navegaÃ§Ã£o ao PDV
    """
    
    from datetime import datetime as dt, timedelta
    from sqlalchemy import func, extract
    
    # Extrair tenant_id
    user, tenant_id = user_and_tenant
    
    # Query base
    query = db.query(EstoqueMovimentacao).join(Produto).filter(
        Produto.tenant_id == tenant_id
    )
    
    # Filtro de data
    if data_inicio:
        try:
            data_inicio_dt = dt.fromisoformat(data_inicio)
            query = query.filter(EstoqueMovimentacao.created_at >= data_inicio_dt)
        except:
            pass
    
    if data_fim:
        try:
            data_fim_dt = dt.fromisoformat(data_fim)
            # Adicionar 1 dia para incluir todo o dia final
            data_fim_dt = data_fim_dt + timedelta(days=1)
            query = query.filter(EstoqueMovimentacao.created_at < data_fim_dt)
        except:
            pass
    
    # Se nÃ£o informou datas, usar Ãºltimos 6 meses
    if not data_inicio and not data_fim:
        data_inicio_dt = dt.now() - timedelta(days=180)
        query = query.filter(EstoqueMovimentacao.created_at >= data_inicio_dt)
    
    # Filtro de produto (converter string para int se nÃ£o vazio)
    if produto_id and produto_id.strip():
        try:
            produto_id_int = int(produto_id)
            query = query.filter(EstoqueMovimentacao.produto_id == produto_id_int)
        except ValueError:
            pass  # Ignora se nÃ£o for nÃºmero vÃ¡lido
    
    # Filtro de tipo (campo 'tipo' e nÃ£o 'tipo_movimentacao')
    if tipo_movimentacao and tipo_movimentacao != "todos":
        query = query.filter(EstoqueMovimentacao.tipo == tipo_movimentacao)
    
    # Ordenar por data (mais recente primeiro)
    query = query.order_by(EstoqueMovimentacao.created_at.desc())
    
    movimentacoes = query.all()
    
    # Montar resultado
    resultado = []
    
    for mov in movimentacoes:
        # Buscar produto
        produto = db.query(Produto).filter(Produto.id == mov.produto_id).first()
        
        # Determinar entrada/saÃ­da (campo 'tipo' e nÃ£o 'tipo_movimentacao')
        entrada = mov.quantidade if mov.tipo == "entrada" else None
        saida = mov.quantidade if mov.tipo != "entrada" else None
        
        item = {
            "id": mov.id,
            "data": mov.created_at.strftime("%d/%m/%Y"),
            "data_completa": mov.created_at.isoformat(),
            "mes": mov.created_at.strftime("%B, %Y"),
            "mes_numero": mov.created_at.month,
            "ano": mov.created_at.year,
            "codigo": produto.codigo if produto else "N/A",
            "produto_nome": produto.nome if produto else "Produto deletado",
            "produto_id": mov.produto_id,
            "entrada": entrada,
            "saida": saida,
            "estoque": mov.quantidade_nova,
            "tipo": mov.tipo.title(),
            "valor_unitario": mov.custo_unitario,
            "valor_total": mov.valor_total,
            "usuario": mov.user.nome if mov.user else "Sistema",
            "numero_pedido": mov.documento,
            "lancamento": mov.created_at.strftime("%d/%m/%Y %H:%M:%S"),
            "observacoes": mov.observacao,
            "lotes_consumidos": mov.lotes_consumidos
        }
        
        resultado.append(item)
    
    # Se solicitado, agrupar por mÃªs
    if agrupar_por_mes:
        # Agrupar movimentaÃ§Ãµes por mÃªs
        agrupado = {}
        
        for item in resultado:
            chave_mes = f"{item['ano']}-{item['mes_numero']:02d}"
            
            if chave_mes not in agrupado:
                agrupado[chave_mes] = {
                    "mes": item["mes"],
                    "ano": item["ano"],
                    "total_vendas": 0,
                    "total_outras_saidas": 0,
                    "total_entradas": 0,
                    "movimentacoes": []
                }
            
            # Contabilizar totais
            if item["entrada"]:
                agrupado[chave_mes]["total_entradas"] += item["entrada"]
            elif item["tipo"].lower() == "venda":
                agrupado[chave_mes]["total_vendas"] += item["saida"] or 0
            else:
                agrupado[chave_mes]["total_outras_saidas"] += item["saida"] or 0
            
            agrupado[chave_mes]["movimentacoes"].append(item)
        
        # Converter para lista ordenada
        resultado_agrupado = []
        for chave in sorted(agrupado.keys(), reverse=True):
            resultado_agrupado.append(agrupado[chave])
        
        return {
            "total_registros": len(resultado),
            "agrupado_por_mes": True,
            "meses": resultado_agrupado
        }
    
    return {
        "total_registros": len(resultado),
        "agrupado_por_mes": False,
        "movimentacoes": resultado
    }


# ==========================================
# ENDPOINTS - IMAGENS
# ==========================================

from fastapi import UploadFile, File
from pathlib import Path
import shutil
import uuid

# DiretÃ³rio para salvar imagens
UPLOAD_DIR = Path("uploads/produtos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/{produto_id}/imagens", response_model=ImagemUploadResponse)
async def upload_imagem_produto(
    produto_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Upload de imagem para um produto
    
    - Aceita JPG, PNG, WebP
    - Tamanho mÃ¡ximo: 5MB
    - Salva em /uploads/produtos/{produto_id}/{uuid}.ext
    - Primeira imagem Ã© automaticamente marcada como principal
    """
    try:
        current_user, tenant_id = user_and_tenant
        logger.info(f"[UPLOAD] Iniciando upload para produto {produto_id}")
        
        # Verificar se produto existe e pertence ao usuÃ¡rio
        produto = db.query(Produto).filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.situacao == True
        ).first()
        
        if not produto:
            logger.error(f"[UPLOAD] Produto {produto_id} nÃ£o encontrado para usuÃ¡rio {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto nÃ£o encontrado"
            )
        
        logger.info(f"[UPLOAD] Produto encontrado: {produto.nome}")
        
        # Validar tipo de arquivo
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            logger.error(f"[UPLOAD] Tipo invÃ¡lido: {file.content_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato nÃ£o aceito. Use JPG, PNG ou WebP"
            )
        
        # Validar tamanho (5MB)
        file.file.seek(0, 2)  # Ir para o final do arquivo
        file_size = file.file.tell()  # Obter tamanho
        file.file.seek(0)  # Voltar ao inÃ­cio
        
        max_size = 5 * 1024 * 1024  # 5MB
        if file_size > max_size:
            logger.error(f"[UPLOAD] Arquivo muito grande: {file_size} bytes")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo muito grande. MÃ¡ximo: 5MB"
            )
        
        logger.info(f"[UPLOAD] Arquivo validado: {file_size} bytes")
        
        # Gerar nome Ãºnico para o arquivo
        ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        
        # Criar pasta do produto
        produto_dir = UPLOAD_DIR / str(produto_id)
        produto_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[UPLOAD] DiretÃ³rio criado: {produto_dir}")
        
        # Salvar arquivo
        file_path = produto_dir / filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"[UPLOAD] Arquivo salvo: {file_path}")
        
        # Verificar se jÃ¡ existe imagem principal
        tem_principal = db.query(ProdutoImagem).filter(
            ProdutoImagem.produto_id == produto_id,
            ProdutoImagem.e_principal == True
        ).first()
        
        # Primeira imagem Ã© principal automaticamente
        e_principal = not tem_principal
        logger.info(f"[UPLOAD] Ã‰ principal: {e_principal}")
        
        # Obter prÃ³xima ordem
        max_ordem = db.query(func.max(ProdutoImagem.ordem)).filter(
            ProdutoImagem.produto_id == produto_id
        ).scalar() or 0
        logger.info(f"[UPLOAD] PrÃ³xima ordem: {max_ordem + 1}")
        
        # Criar registro no banco
        nova_imagem = ProdutoImagem(
            tenant_id=tenant_id,
            produto_id=produto_id,
            url=f"/uploads/produtos/{produto_id}/{filename}",
            ordem=max_ordem + 1,
            e_principal=e_principal
        )
        
        db.add(nova_imagem)
        db.commit()
        db.refresh(nova_imagem)

        # Se é a imagem principal, atualizar também o campo imagem_principal do produto
        if e_principal:
            produto.imagem_principal = nova_imagem.url
            db.commit()

        logger.info(f"[UPLOAD] ✅ Imagem {nova_imagem.id} adicionada ao produto {produto_id} por {current_user.email}")
        
        return nova_imagem
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[UPLOAD] âŒ ERRO: {str(e)}")
        logger.error(f"[UPLOAD] Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer upload: {str(e)}"
        )


@router.get("/{produto_id}/imagens", response_model=List[ImagemUploadResponse])
def listar_imagens_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Listar todas as imagens de um produto
    Ordenadas por: principal DESC, ordem ASC
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Verificar se produto existe e pertence ao usuÃ¡rio
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto nÃ£o encontrado"
        )
    
    imagens = db.query(ProdutoImagem).filter(
        ProdutoImagem.produto_id == produto_id
    ).order_by(
        ProdutoImagem.e_principal.desc(),
        ProdutoImagem.ordem.asc()
    ).all()
    
    return imagens


class ImagemUpdateRequest(BaseModel):
    ordem: Optional[int] = None
    principal: Optional[bool] = None


@router.put("/imagens/{imagem_id}", response_model=ImagemUploadResponse)
def atualizar_imagem(
    imagem_id: int,
    dados: ImagemUpdateRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualizar dados da imagem (ordem, se Ã© principal)
    """
    # Buscar imagem e verificar permissÃ£o
    imagem = db.query(ProdutoImagem).join(Produto).filter(
        ProdutoImagem.id == imagem_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not imagem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagem nÃ£o encontrada"
        )
    
    # Se for marcar como principal, desmarcar outras
    if dados.principal and not imagem.e_principal:
        db.query(ProdutoImagem).filter(
            ProdutoImagem.produto_id == imagem.produto_id,
            ProdutoImagem.e_principal == True
        ).update({"e_principal": False})
    
    # Atualizar campos
    if dados.ordem is not None:
        imagem.ordem = dados.ordem
    if dados.principal is not None:
        imagem.e_principal = dados.principal
    
    imagem.updated_at = datetime.now()
    
    db.commit()
    db.refresh(imagem)
    
    logger.info(f"Imagem {imagem_id} atualizada por {current_user.email}")
    
    return imagem


@router.delete("/imagens/{imagem_id}")
def deletar_imagem(
    imagem_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Deletar imagem do produto
    Remove o arquivo fÃ­sico e o registro do banco
    """
    # Buscar imagem e verificar permissÃ£o
    imagem = db.query(ProdutoImagem).join(Produto).filter(
        ProdutoImagem.id == imagem_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not imagem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagem nÃ£o encontrada"
        )
    
    # Deletar arquivo fÃ­sico
    try:
        file_path = Path(f".{imagem.url}")  # Remove leading /
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Arquivo {file_path} deletado")
    except Exception as e:
        logger.warning(f"Erro ao deletar arquivo fÃ­sico: {e}")
    
    # Deletar registro
    db.delete(imagem)
    db.commit()
    
    logger.info(f"Imagem {imagem_id} deletada por {current_user.email}")
    
    return {"message": "Imagem deletada com sucesso"}

# ==========================================
# ENDPOINTS - FORNECEDORES
# ==========================================

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


@router.post("/{produto_id}/fornecedores", response_model=FornecedorVinculoResponse)
def vincular_fornecedor(
    produto_id: int,
    dados: FornecedorVinculoCreate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Vincular fornecedor a um produto
    
    - Pode ter mÃºltiplos fornecedores por produto
    - Apenas 1 pode ser principal
    - Fornecedor deve ser do tipo 'fornecedor' no cadastro de clientes
    """
    try:
        logger.info(f"[FORNECEDOR] Vinculando fornecedor {dados.fornecedor_id} ao produto {produto_id}")
        
        # Verificar se produto existe e pertence ao usuÃ¡rio
        produto = db.query(Produto).filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.situacao == True
        ).first()
        
        if not produto:
            logger.error(f"[FORNECEDOR] Produto {produto_id} nÃ£o encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto nÃ£o encontrado"
            )
        
        logger.info(f"[FORNECEDOR] Produto encontrado: {produto.nome}")
        
        # Verificar se fornecedor existe e pertence ao usuÃ¡rio
        fornecedor = db.query(Cliente).filter(
            Cliente.id == dados.fornecedor_id,
            Cliente.tenant_id == tenant_id,
            Cliente.tipo_cadastro == "fornecedor"
        ).first()
        
        if not fornecedor:
            logger.error(f"[FORNECEDOR] Fornecedor {dados.fornecedor_id} nÃ£o encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fornecedor nÃ£o encontrado ou nÃ£o Ã© do tipo fornecedor"
            )
        
        logger.info(f"[FORNECEDOR] Fornecedor encontrado: {fornecedor.nome}")
        
        # Verificar se jÃ¡ existe vÃ­nculo
        vinculo_existente = db.query(ProdutoFornecedor).filter(
            ProdutoFornecedor.produto_id == produto_id,
            ProdutoFornecedor.fornecedor_id == dados.fornecedor_id
        ).first()
        
        if vinculo_existente:
            logger.error(f"[FORNECEDOR] VÃ­nculo jÃ¡ existe")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fornecedor jÃ¡ vinculado a este produto"
            )
        
        # Se for marcar como principal, desmarcar outros
        if dados.e_principal:
            logger.info(f"[FORNECEDOR] Desmarcando outros fornecedores principais")
            db.query(ProdutoFornecedor).filter(
                ProdutoFornecedor.produto_id == produto_id,
                ProdutoFornecedor.e_principal == True
            ).update({"e_principal": False})
            
            # Atualizar fornecedor_id do produto
            produto.fornecedor_id = dados.fornecedor_id
        
        # Criar vÃ­nculo
        logger.info(f"[FORNECEDOR] Criando vÃ­nculo no banco")
        novo_vinculo = ProdutoFornecedor(
            produto_id=produto_id,
            fornecedor_id=dados.fornecedor_id,
            codigo_fornecedor=dados.codigo_fornecedor,
            preco_custo=dados.preco_custo,
            prazo_entrega=dados.prazo_entrega,
            estoque_fornecedor=dados.estoque_fornecedor,
            e_principal=dados.e_principal
        )
        
        db.add(novo_vinculo)
        db.commit()
        db.refresh(novo_vinculo)
        
        logger.info(f"[FORNECEDOR] VÃ­nculo criado com ID {novo_vinculo.id}")
        
        # Montar resposta com dados do fornecedor
        response = FornecedorVinculoResponse(
            id=novo_vinculo.id,
            produto_id=novo_vinculo.produto_id,
            fornecedor_id=novo_vinculo.fornecedor_id,
            codigo_fornecedor=novo_vinculo.codigo_fornecedor,
            preco_custo=novo_vinculo.preco_custo,
            prazo_entrega=novo_vinculo.prazo_entrega,
            estoque_fornecedor=novo_vinculo.estoque_fornecedor,
            e_principal=novo_vinculo.e_principal,
            ativo=novo_vinculo.ativo,
            created_at=novo_vinculo.created_at,
            updated_at=novo_vinculo.updated_at,
            fornecedor_nome=fornecedor.nome,
            fornecedor_cpf_cnpj=fornecedor.cnpj if fornecedor.tipo_pessoa == 'PJ' else fornecedor.cpf,
            fornecedor_email=fornecedor.email,
            fornecedor_telefone=fornecedor.telefone or fornecedor.celular
        )
        
        logger.info(f"[FORNECEDOR] âœ… VÃ­nculo completado com sucesso")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FORNECEDOR] âŒ ERRO: {str(e)}")
        logger.error(f"[FORNECEDOR] Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao vincular fornecedor: {str(e)}"
        )


@router.get("/{produto_id}/fornecedores", response_model=List[FornecedorVinculoResponse])
def listar_fornecedores_produto(
    produto_id: int,
    apenas_ativos: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Listar todos os fornecedores vinculados a um produto
    Ordenados por: principal DESC, created_at ASC
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Verificar se produto existe e pertence ao usuÃ¡rio
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto nÃ£o encontrado"
        )
    
    # Buscar fornecedores
    query = db.query(ProdutoFornecedor).filter(
        ProdutoFornecedor.produto_id == produto_id
    )
    
    if apenas_ativos:
        query = query.filter(ProdutoFornecedor.ativo == True)
    
    vinculos = query.order_by(
        ProdutoFornecedor.e_principal.desc(),
        ProdutoFornecedor.created_at.asc()
    ).all()
    
    # Montar resposta com dados dos fornecedores
    resultado = []
    for vinculo in vinculos:
        fornecedor = db.query(Cliente).filter(Cliente.id == vinculo.fornecedor_id).first()
        
        if fornecedor:
            cpf_cnpj = fornecedor.cnpj if fornecedor.tipo_pessoa == 'PJ' else fornecedor.cpf
            telefone = fornecedor.telefone or fornecedor.celular
        else:
            cpf_cnpj = None
            telefone = None
        
        resultado.append(FornecedorVinculoResponse(
            id=vinculo.id,
            produto_id=vinculo.produto_id,
            fornecedor_id=vinculo.fornecedor_id,
            codigo_fornecedor=vinculo.codigo_fornecedor,
            preco_custo=vinculo.preco_custo,
            prazo_entrega=vinculo.prazo_entrega,
            estoque_fornecedor=vinculo.estoque_fornecedor,
            e_principal=vinculo.e_principal,
            ativo=vinculo.ativo,
            created_at=vinculo.created_at,
            updated_at=vinculo.updated_at,
            fornecedor_nome=fornecedor.nome if fornecedor else None,
            fornecedor_cpf_cnpj=cpf_cnpj,
            fornecedor_email=fornecedor.email if fornecedor else None,
            fornecedor_telefone=telefone
        ))
    
    return resultado


@router.put("/fornecedores/{vinculo_id}", response_model=FornecedorVinculoResponse)
def atualizar_vinculo_fornecedor(
    vinculo_id: int,
    dados: FornecedorVinculoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Atualizar dados do vÃ­nculo fornecedor-produto
    """
    # Buscar vÃ­nculo e verificar permissÃ£o
    vinculo = db.query(ProdutoFornecedor).join(Produto).filter(
        ProdutoFornecedor.id == vinculo_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VÃ­nculo nÃ£o encontrado"
        )
    
    # Se for marcar como principal, desmarcar outros
    if dados.e_principal and not vinculo.e_principal:
        db.query(ProdutoFornecedor).filter(
            ProdutoFornecedor.produto_id == vinculo.produto_id,
            ProdutoFornecedor.e_principal == True
        ).update({"e_principal": False})
        
        # Atualizar fornecedor_id do produto
        produto = db.query(Produto).filter(Produto.id == vinculo.produto_id).first()
        if produto:
            produto.fornecedor_id = vinculo.fornecedor_id
    
    # Atualizar campos
    if dados.codigo_fornecedor is not None:
        vinculo.codigo_fornecedor = dados.codigo_fornecedor
    if dados.preco_custo is not None:
        vinculo.preco_custo = dados.preco_custo
    if dados.prazo_entrega is not None:
        vinculo.prazo_entrega = dados.prazo_entrega
    if dados.estoque_fornecedor is not None:
        vinculo.estoque_fornecedor = dados.estoque_fornecedor
    if dados.e_principal is not None:
        vinculo.e_principal = dados.e_principal
    if dados.ativo is not None:
        vinculo.ativo = dados.ativo
    
    vinculo.updated_at = datetime.now()
    
    db.commit()
    db.refresh(vinculo)
    
    logger.info(f"VÃ­nculo fornecedor {vinculo_id} atualizado por {current_user.email}")
    
    # Buscar dados do fornecedor para resposta
    fornecedor = db.query(Cliente).filter(Cliente.id == vinculo.fornecedor_id).first()
    
    response = FornecedorVinculoResponse(
        id=vinculo.id,
        produto_id=vinculo.produto_id,
        fornecedor_id=vinculo.fornecedor_id,
        codigo_fornecedor=vinculo.codigo_fornecedor,
        preco_custo=vinculo.preco_custo,
        prazo_entrega=vinculo.prazo_entrega,
        estoque_fornecedor=vinculo.estoque_fornecedor,
        e_principal=vinculo.e_principal,
        ativo=vinculo.ativo,
        created_at=vinculo.created_at,
        updated_at=vinculo.updated_at,
        fornecedor_nome=fornecedor.nome if fornecedor else None,
        fornecedor_cpf_cnpj=fornecedor.cnpj if (fornecedor and fornecedor.tipo_pessoa == 'PJ') else (fornecedor.cpf if fornecedor else None),
        fornecedor_email=fornecedor.email if fornecedor else None,
        fornecedor_telefone=(fornecedor.telefone or fornecedor.celular) if fornecedor else None
    )
    
    return response


@router.delete("/fornecedores/{vinculo_id}")
def desvincular_fornecedor(
    vinculo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Desvincular fornecedor de um produto
    Remove o vÃ­nculo do banco de dados
    """
    # Buscar vÃ­nculo e verificar permissÃ£o
    vinculo = db.query(ProdutoFornecedor).join(Produto).filter(
        ProdutoFornecedor.id == vinculo_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VÃ­nculo nÃ£o encontrado"
        )
    
    produto_id = vinculo.produto_id
    era_principal = vinculo.e_principal
    
    # Deletar vÃ­nculo
    db.delete(vinculo)
    
    # Se era principal, tentar promover outro
    if era_principal:
        outro_vinculo = db.query(ProdutoFornecedor).filter(
            ProdutoFornecedor.produto_id == produto_id,
            ProdutoFornecedor.ativo == True
        ).first()
        
        if outro_vinculo:
            outro_vinculo.e_principal = True
            produto = db.query(Produto).filter(Produto.id == produto_id).first()
            if produto:
                produto.fornecedor_id = outro_vinculo.fornecedor_id
        else:
            # Nenhum fornecedor restante, remover do produto
            produto = db.query(Produto).filter(Produto.id == produto_id).first()
            if produto:
                produto.fornecedor_id = None
    
    db.commit()
    
    logger.info(f"Fornecedor desvinculado (id {vinculo_id}) por {current_user.email}")
    
    return {"message": "Fornecedor desvinculado com sucesso"}


# ==========================================
# HISTÃ“RICO DE PREÃ‡OS
# ==========================================

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
    referencia: Optional[str]
    observacoes: Optional[str]
    usuario: Optional[str]
    
    model_config = {"from_attributes": True}


@router.get("/{produto_id}/historico-precos", response_model=List[HistoricoPrecoResponse])
@require_permission("produtos.visualizar")
def listar_historico_precos(
    produto_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista histÃ³rico de alteraÃ§Ãµes de preÃ§os de um produto
    """
    current_user, tenant_id = user_and_tenant
    
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")
    
    historicos = db.query(ProdutoHistoricoPreco).options(
        joinedload(ProdutoHistoricoPreco.user),
        joinedload(ProdutoHistoricoPreco.nota_entrada)
    ).filter(
        ProdutoHistoricoPreco.produto_id == produto_id
    ).order_by(
        ProdutoHistoricoPreco.created_at.desc()
    ).limit(limit).offset(offset).all()
    
    resultado = []
    for hist in historicos:
        resultado.append({
            "id": hist.id,
            "data": hist.created_at,
            "preco_custo_anterior": hist.preco_custo_anterior,
            "preco_custo_novo": hist.preco_custo_novo,
            "preco_venda_anterior": hist.preco_venda_anterior,
            "preco_venda_novo": hist.preco_venda_novo,
            "margem_anterior": hist.margem_anterior,
            "margem_nova": hist.margem_nova,
            "variacao_custo_percentual": hist.variacao_custo_percentual,
            "variacao_venda_percentual": hist.variacao_venda_percentual,
            "motivo": hist.motivo,
            "nota_numero": hist.nota_entrada.numero_nota if hist.nota_entrada else None,
            "referencia": hist.referencia,
            "observacoes": hist.observacoes,
            "usuario": hist.user.email if hist.user else None
        })
    
    return resultado


# ==================== CLASSIFICAï¿½ï¿½O INTELIGENTE DE RAï¿½ï¿½ES ====================

@router.post("/{produto_id}/classificar-ia")
async def classificar_produto_ia(
    produto_id: int,
    forcar: bool = False,  # Forï¿½a reclassificaï¿½ï¿½o mesmo se auto_classificar_nome = False
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Aplica classificaï¿½ï¿½o inteligente via IA em um produto
    Extrai automaticamente: porte, fase, tratamento, sabor e peso do nome
    """
    from .classificador_racao import classificar_produto
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Buscar produto
    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto nï¿½o encontrado"
        )
    
    # Verificar se deve classificar
    if not forcar and not produto.auto_classificar_nome:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auto-classificaï¿½ï¿½o desativada para este produto. Use forcar=true para forï¿½ar."
        )
    
    # Executar classificaï¿½ï¿½o
    resultado, confianca, metadata = classificar_produto(produto.nome, produto.peso_embalagem)
    
    # Importar models de lookup
    from .opcoes_racao_models import PorteAnimal, FasePublico, TipoTratamento, SaborProteina, LinhaRacao
    
    # Atualizar produto apenas com campos que foram identificados
    campos_atualizados = []
    
    # Salvar metadados da classificaï¿½ï¿½o
    produto.classificacao_ia_versao = metadata["versao"]
    
    if resultado["especie_indicada"]:
        # Mapear para formato do banco (dog, cat, both, bird, etc)
        mapa_especies = {
            "CÃ£es": "dog",
            "Gatos": "cat",
            "PÃ¡ssaros": "bird",
            "Roedores": "rodent",
            "Peixes": "fish"
        }
        especie_db = mapa_especies.get(resultado["especie_indicada"], resultado["especie_indicada"].lower())
        produto.especies_indicadas = especie_db
        campos_atualizados.append("especies_indicadas")
    
    # Buscar ID do porte baseado no nome retornado pela IA
    # Classificador retorna array, pegar primeiro elemento
    if resultado["porte_animal"] and len(resultado["porte_animal"]) > 0:
        nome_porte = resultado["porte_animal"][0]  # Pega primeiro porte do array
        porte = db.query(PorteAnimal).filter(
            PorteAnimal.tenant_id == tenant_id,
            PorteAnimal.nome == nome_porte,
            PorteAnimal.ativo == True
        ).first()
        if porte:
            produto.porte_animal_id = porte.id
            campos_atualizados.append("porte_animal_id")
    
    # Buscar ID da fase baseado no nome retornado pela IA
    # Classificador retorna array, pegar primeiro elemento
    if resultado["fase_publico"] and len(resultado["fase_publico"]) > 0:
        nome_fase = resultado["fase_publico"][0]  # Pega primeira fase do array
        fase = db.query(FasePublico).filter(
            FasePublico.tenant_id == tenant_id,
            FasePublico.nome == nome_fase,
            FasePublico.ativo == True
        ).first()
        if fase:
            produto.fase_publico_id = fase.id
            campos_atualizados.append("fase_publico_id")
    
    # Buscar ID do tipo de tratamento baseado no nome retornado pela IA
    # Classificador retorna array, pegar primeiro elemento
    if resultado["tipo_tratamento"] and len(resultado["tipo_tratamento"]) > 0:
        nome_tratamento = resultado["tipo_tratamento"][0]  # Pega primeiro tratamento do array
        tratamento = db.query(TipoTratamento).filter(
            TipoTratamento.tenant_id == tenant_id,
            TipoTratamento.nome == nome_tratamento,
            TipoTratamento.ativo == True
        ).first()
        if tratamento:
            produto.tipo_tratamento_id = tratamento.id
            campos_atualizados.append("tipo_tratamento_id")
    
    # Buscar ID do sabor/proteÃ­na baseado no nome retornado pela IA
    if resultado["sabor_proteina"]:
        sabor = db.query(SaborProteina).filter(
            SaborProteina.tenant_id == tenant_id,
            SaborProteina.nome == resultado["sabor_proteina"],
            SaborProteina.ativo == True
        ).first()
        if sabor:
            produto.sabor_proteina_id = sabor.id
            campos_atualizados.append("sabor_proteina_id")
    
    # Buscar ID da linha de raÃ§Ã£o baseado no nome retornado pela IA
    if resultado.get("linha_racao"):
        linha = db.query(LinhaRacao).filter(
            LinhaRacao.tenant_id == tenant_id,
            LinhaRacao.nome == resultado["linha_racao"],
            LinhaRacao.ativo == True
        ).first()
        if linha:
            produto.linha_racao_id = linha.id
            campos_atualizados.append("linha_racao_id")
    
    # Atualizar peso se retornado pela IA e ainda nÃ£o definido
    if resultado["peso_embalagem"] and not produto.peso_embalagem:
        produto.peso_embalagem = resultado["peso_embalagem"]
        campos_atualizados.append("peso_embalagem")
    
    # Salvar
    if campos_atualizados:
        db.commit()
        db.refresh(produto)
    
    return {
        "success": True,
        "produto_id": produto.id,
        "nome": produto.nome,
        "classificacao": resultado,
        "confianca": confianca,
        "campos_atualizados": campos_atualizados,
        "mensagem": f"Classificaï¿½ï¿½o aplicada com sucesso. Score: {confianca['score']}%"
    }


@router.post("/classificar-lote")
async def classificar_lote_produtos(
    produto_ids: List[int] = None,  # Se None, classifica todos ativos com auto_classificar_nome=True
    apenas_sem_classificacao: bool = True,  # Sï¿½ classifica produtos sem classificaï¿½ï¿½o existente
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Classifica mï¿½ltiplos produtos em lote
    ï¿½til para classificar produtos histï¿½ricos
    """
    from .classificador_racao import classificar_produto
    
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    
    # Montar query
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo == True,
        Produto.auto_classificar_nome == True
    )
    
    # Filtrar por IDs especÃ­ficos se fornecido
    if produto_ids:
        query = query.filter(Produto.id.in_(produto_ids))
    
    # Filtrar apenas produtos sem classificaÃ§Ã£o completa
    if apenas_sem_classificacao:
        query = query.filter(
            (Produto.porte_animal == None) |
            (Produto.fase_publico == None) |
            (Produto.sabor_proteina == None)
        )
    
    produtos = query.limit(100).all()  # Limite de seguranÃ§a
    
    sucesso = []
    erros = []
    
    for produto in produtos:
        try:
            resultado, confianca = classificar_produto(produto.nome, produto.peso_embalagem)
            
            campos_atualizados = []
            
            if resultado["especie_indicada"] and not produto.especies_indicadas:
                # Mapear para formato do banco
                mapa_especies = {
                    "CÃ£es": "dog",
                    "Gatos": "cat",
                    "PÃ¡ssaros": "bird",
                    "Roedores": "rodent",
                    "Peixes": "fish"
                }
                especie_db = mapa_especies.get(resultado["especie_indicada"], resultado["especie_indicada"].lower())
                produto.especies_indicadas = especie_db
                campos_atualizados.append("especies_indicadas")
            
            if resultado["porte_animal"] and not produto.porte_animal:
                produto.porte_animal = resultado["porte_animal"]
                campos_atualizados.append("porte_animal")
            
            if resultado["fase_publico"] and not produto.fase_publico:
                produto.fase_publico = resultado["fase_publico"]
                campos_atualizados.append("fase_publico")
            
            if resultado["tipo_tratamento"] and not produto.tipo_tratamento:
                produto.tipo_tratamento = resultado["tipo_tratamento"]
                campos_atualizados.append("tipo_tratamento")
            
            if resultado["sabor_proteina"] and not produto.sabor_proteina:
                produto.sabor_proteina = resultado["sabor_proteina"]
                campos_atualizados.append("sabor_proteina")
            
            if resultado["peso_embalagem"] and not produto.peso_embalagem:
                produto.peso_embalagem = resultado["peso_embalagem"]
                campos_atualizados.append("peso_embalagem")
            
            if campos_atualizados:
                db.commit()
                db.refresh(produto)
            
            sucesso.append({
                "produto_id": produto.id,
                "nome": produto.nome,
                "campos_atualizados": campos_atualizados,
                "score": confianca["score"]
            })
            
        except Exception as e:
            erros.append({
                "produto_id": produto.id,
                "nome": produto.nome,
                "erro": str(e)
            })
    
    return {
        "success": True,
        "total_processados": len(produtos),
        "sucessos": len(sucesso),
        "erros": len(erros),
        "detalhes_sucesso": sucesso,
        "detalhes_erros": erros
    }


@router.get("/racao/alertas")
async def listar_racoes_sem_classificacao(
    limite: int = 50,
    offset: int = 0,
    especie: Optional[str] = None,  # Filtro por espÃ©cie: dog, cat, bird, rodent, fish
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista raï¿½ï¿½es sem classificaï¿½ï¿½o completa para alertas
    Filtra produtos classificados como raï¿½ï¿½o mas sem informaï¿½ï¿½es importantes
    
    ParÃ¢metros:
    - especie: Filtro opcional por espÃ©cie (dog, cat, bird, rodent, fish)
    """
    try:
        current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
        
        logger.info(f"[racao/alertas] Iniciando busca para tenant {tenant_id}, especie={especie}")
        
        # Buscar raÃ§Ãµes sem classificaÃ§Ã£o completa
        # Considera "raÃ§Ã£o" se:
        # 1. classificacao_racao != null AND != 'NÃ£o Ã© raÃ§Ã£o'
        # 2. OU categoria.nome LIKE '%raÃ§Ã£o%'
        
        # Usar joinedload para evitar N+1 queries
        query = db.query(Produto).options(
            joinedload(Produto.categoria),
            joinedload(Produto.marca)
        ).filter(
            Produto.tenant_id == tenant_id,
            Produto.ativo == True
        )
        
        # Filtro: Ã© raÃ§Ã£o E estÃ¡ incompleta
        query = query.filter(
            Produto.classificacao_racao == 'sim'
        )
        
        # Montar filtros dinamicamente baseado em campos que existem
        filtros_incompletos = []
        filtros_incompletos.append(Produto.especies_indicadas == None)
        
        # Adicionar filtros apenas para campos que existem no modelo
        if hasattr(Produto, 'porte_animal_id'):
            filtros_incompletos.append(Produto.porte_animal_id == None)
            logger.info(f"[racao/alertas] Campo 'porte_animal_id' encontrado no modelo")
        else:
            logger.warning(f"[racao/alertas] Campo 'porte_animal_id' NÃƒO existe no modelo")
        
        if hasattr(Produto, 'fase_publico_id'):
            filtros_incompletos.append(Produto.fase_publico_id == None)
            logger.info(f"[racao/alertas] Campo 'fase_publico_id' encontrado no modelo")
        else:
            logger.warning(f"[racao/alertas] Campo 'fase_publico_id' NÃƒO existe no modelo")
        
        filtros_incompletos.append(Produto.sabor_proteina == None)
        filtros_incompletos.append(Produto.peso_embalagem == None)
        
        # Aplicar filtro OR (pelo menos um campo faltando)
        query = query.filter(or_(*filtros_incompletos))
        
        # Filtrar por espÃ©cie se especificado
        if especie:
            query = query.filter(Produto.especies_indicadas == especie)
        
        total = query.count()
        logger.info(f"[racao/alertas] Total de produtos encontrados: {total}")
        
        produtos = query.limit(limite).offset(offset).all()
        logger.info(f"[racao/alertas] Produtos retornados nesta pÃ¡gina: {len(produtos)}")
        
        resultado = []
        for produto in produtos:
            try:
                campos_faltantes = []
                
                if not produto.especies_indicadas:
                    campos_faltantes.append("especies_indicadas")
                
                # Verificar campos FK apenas se existirem no modelo
                if hasattr(produto, 'porte_animal_id'):
                    if not produto.porte_animal_id:
                        campos_faltantes.append("porte_animal")
                
                if hasattr(produto, 'fase_publico_id'):
                    if not produto.fase_publico_id:
                        campos_faltantes.append("fase_publico")
                
                if not produto.sabor_proteina:
                    campos_faltantes.append("sabor_proteina")
                
                if not produto.peso_embalagem:
                    campos_faltantes.append("peso_embalagem")
                
                # Acesso seguro a relationships
                categoria_nome = None
                if produto.categoria:
                    categoria_nome = produto.categoria.nome
                
                marca_nome = None
                if produto.marca:
                    marca_nome = produto.marca.nome
                
                # Acesso seguro ao campo auto_classificar_nome
                auto_classificar = False
                if hasattr(produto, 'auto_classificar_nome'):
                    auto_classificar = produto.auto_classificar_nome or False
                
                resultado.append({
                    "id": produto.id,
                    "codigo": produto.codigo,
                    "nome": produto.nome,
                    "classificacao_racao": produto.classificacao_racao,
                    "especies_indicadas": produto.especies_indicadas,
                    "categoria": categoria_nome,
                    "marca": marca_nome,
                    "campos_faltantes": campos_faltantes,
                    "completude": round((5 - len(campos_faltantes)) / 5 * 100, 1),
                    "auto_classificar_ativo": auto_classificar
                })
            except Exception as e:
                logger.error(f"[racao/alertas] Erro ao processar produto {produto.id}: {str(e)}")
                logger.error(f"[racao/alertas] Stack trace: {traceback.format_exc()}")
                continue
        
        logger.info(f"[racao/alertas] Busca concluÃ­da com sucesso. Total de itens no resultado: {len(resultado)}")
        
        return {
            "total": total,
            "limite": limite,
            "offset": offset,
            "especie_filtro": especie,
            "items": resultado
        }
    
    except Exception as error:
        logger.error(f"[racao/alertas] ERRO CRÃTICO: {str(error)}")
        logger.error(f"[racao/alertas] Stack trace:\n{traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Erro ao listar raÃ§Ãµes sem classificaÃ§Ã£o",
                "error": str(error),
                "stack": traceback.format_exc(),
                "endpoint": "/api/produtos/racao/alertas"
            }
        )

