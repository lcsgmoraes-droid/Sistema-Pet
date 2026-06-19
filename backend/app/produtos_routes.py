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
from sqlalchemy import func, or_, and_
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import traceback

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .security.permissions_decorator import require_permission
from .models import Cliente
from app.partner_utils import get_all_accessible_tenant_ids
from .vendas_models import Venda, VendaItem
from .produtos_models import (
    Categoria,
    Marca,
    Departamento,
    Produto,
    ProdutoLote,
    ProdutoFornecedor,
    EstoqueMovimentacao,
    ProdutoHistoricoPreco,
    ProdutoKitComponente,  # Sprint 4: ComposiÃ§Ã£o de KIT
)
from .produtos.schemas import (
    CategoriaCreate,
    CategoriaUpdate,
    CategoriaResponse,
    MarcaCreate,
    MarcaUpdate,
    MarcaResponse,
    DepartamentoCreate,
    DepartamentoUpdate,
    DepartamentoResponse,
    GerarCodigoBarrasRequest,
    GerarCodigoBarrasResponse,
    ProdutoCreate,
    ProdutoUpdate,
    ProdutoAtivoUpdate,
    ProdutoFusaoPreviewRequest,
    ProdutoFusaoExecutarRequest,
    LoteResponse,
    ProdutoResponse,
    ProdutosPaginadosResponse,
    LoteBase,
    LoteCreate,
    EntradaEstoqueRequest,
    SaidaEstoqueRequest,
    AtualizacaoLoteRequest,
    FornecedorVinculoCreate,
    FornecedorVinculoUpdate,
    FornecedorVinculoResponse,
    HistoricoPrecoResponse,
)

from .services.produto_service import ProdutoService
from .services.produto_merge_service import (
    executar_fusao_produtos,
    montar_preview_fusao_produtos,
)
from .produtos.search import (
    _build_produto_search_order_clause,
    _produto_search_conditions,
    _produto_search_conditions_fast,
)
from .produtos.codigo_barras import (
    gerar_codigo_barras_ean13,
    validar_codigo_barras_ean13,
)
from .produtos.categorias import (
    _calcular_niveis_categorias,
    _construir_arvore_categorias,
)
from .produtos.core import (
    _aplicar_status_ativo_produto,
    _nome_indica_granel,
    _normalizar_filtro_ativo_produtos,
    _normalizar_payload_granel,
    _normalizar_promocao_erp_payload,
    _normalizar_sku_produto,
    _produto_sku_value,
)
from .produtos.listagem import (
    _aplicar_filtro_fornecedor_produto,
    _aplicar_filtros_basicos_produtos,
    _enriquecer_produto_listagem,
    _load_options_listagem_produtos,
    _mapa_reservas_ativas_multitenant,
    _normalizar_paginacao_produtos,
    _palavras_busca_produto,
    _resolver_fornecedor_ids_filtro_produto,
    _resolver_promocao_erp_produto,
    _tipos_base_listagem,
)
from .produtos.lotes import _consumir_lotes_fifo_produto
from .produtos.racao import (
    _normalizar_classificacao_racao,
    _normalizar_payload_racao,
    _produto_eh_racao_expr,
)
from .produtos.imagens_routes import router as imagens_router
from .produtos.relatorios_routes import router as relatorios_router
from .produtos.validade import (
    _mapa_validade_proxima_produtos,
)
from .produtos.validators import (
    _obter_marca_ou_404,
    _obter_produto_ou_404,
    _validar_pode_inativar_produto,
    _validar_sku_unico,
    _validar_tenant_e_obter_usuario,
)
from .produtos.fornecedores import (
    OPERACOES_FORNECEDOR_LOTE,
    _aplicar_fornecedor_produto_lote,
    _garantir_fornecedor_principal_quando_unico,
    _validar_fornecedor_produto_lote,
)

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/produtos", tags=["produtos"])
router.include_router(imagens_router)
router.include_router(relatorios_router)

PRODUTO_SKU_COLUMN = getattr(Produto, "sku", None)


# ==========================================
# ENDPOINTS - CATEGORIAS
# ==========================================


@router.post(
    "/categorias", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED
)
@require_permission("produtos.criar")
def criar_categoria(
    categoria: CategoriaCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria uma nova categoria"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se categoria pai existe (se fornecida)
    if categoria.categoria_pai_id:
        pai = (
            db.query(Categoria)
            .filter(
                Categoria.id == categoria.categoria_pai_id,
                Categoria.tenant_id == tenant_id,
                Categoria.ativo.is_(True),
            )
            .first()
        )
        if not pai:
            raise HTTPException(status_code=404, detail="Categoria pai nÃ£o encontrada")

        # Verificar nÃ­vel mÃ¡ximo (4 nÃ­veis)
        nivel_pai = calcular_nivel(db, categoria.categoria_pai_id)
        if nivel_pai >= 4:
            raise HTTPException(
                status_code=400, detail="Limite de 4 nÃ­veis de categorias atingido"
            )

    # Criar categoria
    nova_categoria = Categoria(
        **categoria.model_dump(), tenant_id=tenant_id, user_id=current_user.id
    )

    db.add(nova_categoria)
    db.commit()
    db.refresh(nova_categoria)

    return nova_categoria


@router.get("/categorias", response_model=List[CategoriaResponse])
@require_permission("produtos.visualizar")
def listar_categorias(
    categoria_pai_id: Optional[int] = None,
    incluir_subcategorias: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista todas as categorias (o frontend constrÃ³i a hierarquia)
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Retornar TODAS as categorias ativas do usuÃ¡rio
    # O frontend vai construir a Ã¡rvore hierÃ¡rquica
    query = db.query(Categoria).filter(
        Categoria.tenant_id == tenant_id, Categoria.ativo.is_(True)
    )

    categorias = (
        query.options(joinedload(Categoria.departamento))
        .order_by(Categoria.ordem, Categoria.nome)
        .all()
    )

    categoria_por_id = {cat.id: cat for cat in categorias}
    categoria_ids = list(categoria_por_id.keys())

    total_filhos_por_categoria = {
        categoria_pai_id: total_filhos
        for categoria_pai_id, total_filhos in (
            db.query(Categoria.categoria_pai_id, func.count(Categoria.id))
            .filter(
                Categoria.tenant_id == tenant_id,
                Categoria.ativo.is_(True),
                Categoria.categoria_pai_id.isnot(None),
            )
            .group_by(Categoria.categoria_pai_id)
            .all()
        )
    }

    total_produtos_por_categoria = {}
    if categoria_ids:
        total_produtos_por_categoria = {
            categoria_id: total_produtos
            for categoria_id, total_produtos in (
                db.query(Produto.categoria_id, func.count(Produto.id))
                .filter(
                    Produto.tenant_id == tenant_id,
                    Produto.categoria_id.in_(categoria_ids),
                )
                .group_by(Produto.categoria_id)
                .all()
            )
        }

    niveis_por_categoria = _calcular_niveis_categorias(categoria_por_id)

    # Calcular nÃ­vel e contadores para cada categoria sem N+1
    resultado = []
    for cat in categorias:
        cat_dict = {
            "id": cat.id,
            "nome": cat.nome,
            "descricao": cat.descricao,
            "categoria_pai_id": cat.categoria_pai_id,
            "departamento_id": cat.departamento_id,
            "departamento_nome": cat.departamento.nome if cat.departamento else None,
            "icone": cat.icone,
            "cor": cat.cor,
            "ordem": cat.ordem,
            "ativo": cat.ativo,
            "created_at": cat.created_at,
            "updated_at": cat.updated_at,
            "nivel": niveis_por_categoria.get(cat.id, 1),
            "total_filhos": int(total_filhos_por_categoria.get(cat.id, 0) or 0),
            "total_produtos": int(total_produtos_por_categoria.get(cat.id, 0) or 0),
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
@require_permission("produtos.visualizar")
def listar_categorias_hierarquia(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista todas as categorias em formato de Ã¡rvore hierÃ¡rquica"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar todas as categorias ativas
    categorias = (
        db.query(Categoria)
        .filter(Categoria.tenant_id == tenant_id, Categoria.ativo.is_(True))
        .order_by(Categoria.ordem, Categoria.nome)
        .all()
    )

    return _construir_arvore_categorias(categorias)


@router.get("/categorias/{categoria_id}", response_model=CategoriaResponse)
@require_permission("produtos.visualizar")
def obter_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """ObtÃ©m detalhes de uma categoria"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    categoria = (
        db.query(Categoria)
        .filter(
            Categoria.id == categoria_id,
            Categoria.tenant_id == tenant_id,
            Categoria.ativo.is_(True),
        )
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")

    return categoria


@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
@require_permission("produtos.editar")
def atualizar_categoria(
    categoria_id: int,
    categoria_update: CategoriaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza uma categoria"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    categoria = (
        db.query(Categoria)
        .filter(
            Categoria.id == categoria_id,
            Categoria.tenant_id == tenant_id,
            Categoria.ativo.is_(True),
        )
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")

    # Verificar se categoria pai existe (se fornecida e diferente)
    if (
        categoria_update.categoria_pai_id
        and categoria_update.categoria_pai_id != categoria.categoria_pai_id
    ):
        # NÃ£o permitir que categoria seja filha de si mesma
        if categoria_update.categoria_pai_id == categoria_id:
            raise HTTPException(
                status_code=400, detail="Categoria nÃ£o pode ser pai de si mesma"
            )

        pai = (
            db.query(Categoria)
            .filter(
                Categoria.id == categoria_update.categoria_pai_id,
                Categoria.tenant_id == tenant_id,
                Categoria.ativo.is_(True),
            )
            .first()
        )
        if not pai:
            raise HTTPException(status_code=404, detail="Categoria pai nÃ£o encontrada")

    # Atualizar campos
    for key, value in categoria_update.model_dump(exclude_unset=True).items():
        setattr(categoria, key, value)

    categoria.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(categoria)

    return categoria


@router.delete("/categorias/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("produtos.editar")
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Deleta (soft delete) uma categoria"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    categoria = (
        db.query(Categoria)
        .filter(
            Categoria.id == categoria_id,
            Categoria.tenant_id == tenant_id,
            Categoria.ativo.is_(True),
        )
        .first()
    )

    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")

    # Verificar se categoria tem subcategorias
    subcategorias = (
        db.query(Categoria)
        .filter(
            Categoria.categoria_pai_id == categoria_id,
            Categoria.tenant_id == tenant_id,
            Categoria.ativo.is_(True),
        )
        .count()
    )

    if subcategorias > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria possui {subcategorias} subcategorias. Remova-as primeiro.",
        )

    # Verificar se categoria tem produtos
    produtos_count = (
        db.query(Produto)
        .filter(
            Produto.categoria_id == categoria_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .count()
    )

    if produtos_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria possui {produtos_count} produtos. Remova-os ou mova para outra categoria primeiro.",
        )

    # Soft delete
    categoria.ativo = False
    categoria.updated_at = datetime.utcnow()

    db.commit()

    return None


# ==========================================
# ENDPOINTS - MARCAS
# ==========================================


@router.post(
    "/marcas", response_model=MarcaResponse, status_code=status.HTTP_201_CREATED
)
@require_permission("produtos.criar")
def criar_marca(
    marca: MarcaCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria uma nova marca"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    nova_marca = Marca(
        **marca.model_dump(),
        tenant_id=tenant_id,
        user_id=current_user.id,
    )

    db.add(nova_marca)
    db.commit()
    db.refresh(nova_marca)

    return nova_marca


@router.get("/marcas", response_model=List[MarcaResponse])
@require_permission("produtos.visualizar")
def listar_marcas(
    busca: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista marcas"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    query = db.query(Marca).filter(Marca.tenant_id == tenant_id, Marca.ativo.is_(True))

    if busca:
        query = query.filter(Marca.nome.ilike(f"%{busca}%"))

    marcas = query.order_by(Marca.nome).all()

    return marcas


@router.get("/marcas/{marca_id}", response_model=MarcaResponse)
@require_permission("produtos.visualizar")
def obter_marca(
    marca_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """ObtÃ©m detalhes de uma marca"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    marca = _obter_marca_ou_404(db, marca_id, tenant_id)
    return marca


@router.put("/marcas/{marca_id}", response_model=MarcaResponse)
@require_permission("produtos.editar")
def atualizar_marca(
    marca_id: int,
    marca_update: MarcaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
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
@require_permission("produtos.editar")
def deletar_marca(
    marca_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Deleta (soft delete) uma marca"""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    marca = (
        db.query(Marca)
        .filter(
            Marca.id == marca_id, Marca.tenant_id == tenant_id, Marca.ativo.is_(True)
        )
        .first()
    )

    if not marca:
        raise HTTPException(status_code=404, detail="Marca nÃ£o encontrada")

    # Verificar se marca tem produtos
    produtos_count = (
        db.query(Produto)
        .filter(
            Produto.marca_id == marca_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .count()
    )

    if produtos_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Marca possui {produtos_count} produtos. Remova-os ou mova para outra marca primeiro.",
        )

    # Soft delete
    marca.ativo = False
    marca.updated_at = datetime.utcnow()

    db.commit()

    return None


# ==========================================
# ENDPOINTS - DEPARTAMENTOS
# ==========================================


@router.post(
    "/departamentos",
    response_model=DepartamentoResponse,
    status_code=status.HTTP_201_CREATED,
)
@require_permission("produtos.criar")
def criar_departamento(
    departamento: DepartamentoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria um novo departamento"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    novo_departamento = Departamento(
        **departamento.model_dump(),
        tenant_id=tenant_id,
        user_id=current_user.id,
    )

    db.add(novo_departamento)
    db.commit()
    db.refresh(novo_departamento)

    return novo_departamento


@router.get("/departamentos", response_model=List[DepartamentoResponse])
@require_permission("produtos.visualizar")
def listar_departamentos(
    busca: Optional[str] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista departamentos do tenant atual"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    query = db.query(Departamento).filter(
        Departamento.tenant_id == tenant_id, Departamento.ativo.is_(True)
    )

    if busca:
        query = query.filter(Departamento.nome.ilike(f"%{busca}%"))

    departamentos = query.order_by(Departamento.nome).all()

    return departamentos


@router.get("/departamentos/{departamento_id}", response_model=DepartamentoResponse)
@require_permission("produtos.visualizar")
def obter_departamento(
    departamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """ObtÃ©m um departamento por ID"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    departamento = (
        db.query(Departamento)
        .filter(
            Departamento.id == departamento_id,
            Departamento.tenant_id == tenant_id,
            Departamento.ativo.is_(True),
        )
        .first()
    )

    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento nÃ£o encontrado")

    return departamento


@router.put("/departamentos/{departamento_id}", response_model=DepartamentoResponse)
@require_permission("produtos.editar")
def atualizar_departamento(
    departamento_id: int,
    departamento_update: DepartamentoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza um departamento"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    departamento = (
        db.query(Departamento)
        .filter(
            Departamento.id == departamento_id,
            Departamento.tenant_id == tenant_id,
            Departamento.ativo.is_(True),
        )
        .first()
    )

    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento nÃ£o encontrado")

    for key, value in departamento_update.model_dump(exclude_unset=True).items():
        setattr(departamento, key, value)

    departamento.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(departamento)

    return departamento


@router.delete(
    "/departamentos/{departamento_id}", status_code=status.HTTP_204_NO_CONTENT
)
@require_permission("produtos.editar")
def deletar_departamento(
    departamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Deleta (soft delete) um departamento"""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    departamento = (
        db.query(Departamento)
        .filter(
            Departamento.id == departamento_id,
            Departamento.tenant_id == tenant_id,
            Departamento.ativo.is_(True),
        )
        .first()
    )

    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento nÃ£o encontrado")

    # Verificar se departamento tem produtos
    produtos_count = (
        db.query(Produto)
        .filter(
            Produto.departamento_id == departamento_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .count()
    )

    if produtos_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Departamento possui {produtos_count} produtos. Remova-os ou mova para outro departamento primeiro.",
        )

    # Soft delete
    departamento.ativo = False
    departamento.updated_at = datetime.utcnow()

    db.commit()

    return None


# ==========================================
# ENDPOINTS - CÃ“DIGO DE BARRAS
# ==========================================


@router.post("/gerar-codigo-barras", response_model=GerarCodigoBarrasResponse)
def gerar_codigo_barras(
    request: GerarCodigoBarrasRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
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

        # Verificar se já existe globalmente (constraint é global, não por tenant)
        existe = db.query(Produto).filter(Produto.codigo_barras == codigo).first()

        if not existe:
            return GerarCodigoBarrasResponse(
                codigo_barras=codigo,
                sku_usado=request.sku,
                formato="789-XXXXX-SKUU-C (EAN-13)",
                valido=True,
            )

        tentativa += 1

    raise HTTPException(
        status_code=500,
        detail="NÃ£o foi possÃ­vel gerar cÃ³digo de barras Ãºnico apÃ³s mÃºltiplas tentativas",
    )


@router.get("/validar-codigo-barras/{codigo}")
def validar_codigo_barras(
    codigo: str,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Valida um cÃ³digo de barras EAN-13"""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    resultado_validacao = validar_codigo_barras_ean13(codigo)
    if not resultado_validacao["valido"]:
        return {
            "valido": False,
            "erro": resultado_validacao["erro"],
        }

    codigo_limpo = resultado_validacao["codigo_limpo"]

    # Verificar se jÃ¡ existe no banco
    existe = (
        db.query(Produto)
        .filter(Produto.codigo_barras == codigo_limpo, Produto.tenant_id == tenant_id)
        .first()
    )

    if existe:
        return {
            "valido": True,
            "existe_no_banco": True,
            "produto_id": existe.id,
            "produto_nome": existe.nome,
            "aviso": "CÃ³digo de barras jÃ¡ cadastrado para outro produto",
        }

    return {
        "valido": True,
        "existe_no_banco": False,
        "mensagem": "CÃ³digo de barras vÃ¡lido e disponÃ­vel",
    }


# ==========================================
# ENDPOINTS - PRODUTOS
# ==========================================


@router.post("/", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
@require_permission("produtos.criar")
def criar_produto(
    produto: ProdutoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria um novo produto"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # LOG: Dados recebidos
    logger.info("Criando produto")
    logger.info("Dados de produto recebidos para criacao")
    produto.codigo = _normalizar_sku_produto(produto.codigo)

    # ========================================
    # VALIDAÃ‡Ã•ES DE INFRAESTRUTURA (mantidas na rota)
    # ========================================

    _validar_sku_unico(db, produto.codigo, tenant_id)

    # Verificar se cÃ³digo de barras jÃ¡ existe
    if produto.codigo_barras:
        existe_barcode = (
            db.query(Produto)
            .filter(
                Produto.codigo_barras == produto.codigo_barras,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )

        if existe_barcode:
            raise HTTPException(
                status_code=400,
                detail=f"CÃ³digo de barras '{produto.codigo_barras}' jÃ¡ cadastrado",
            )

    # Verificar se categoria existe
    if produto.categoria_id:
        categoria = (
            db.query(Categoria)
            .filter(
                Categoria.id == produto.categoria_id,
                Categoria.tenant_id == tenant_id,
                Categoria.ativo.is_(True),
            )
            .first()
        )
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoria nÃ£o encontrada")

    # Verificar se marca existe
    if produto.marca_id:
        marca = (
            db.query(Marca)
            .filter(
                Marca.id == produto.marca_id,
                Marca.tenant_id == tenant_id,
                Marca.ativo.is_(True),
            )
            .first()
        )
        if not marca:
            raise HTTPException(status_code=404, detail="Marca nÃ£o encontrada")

    # ========================================
    # ðŸ”’ TRAVA 3 â€” VALIDAÃ‡ÃƒO: PRODUTO PAI NÃƒO TEM PREÃ‡O
    # ========================================
    if produto.tipo_produto == "PAI":
        if produto.preco_venda and produto.preco_venda > 0:
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter preÃ§o de venda. O preÃ§o deve ser definido nas variaÃ§Ãµes individuais.",
            )
        # Verificar estoque_atual se existir no modelo (pode nÃ£o existir em ProdutoCreate)
        estoque = getattr(produto, "estoque_atual", None)
        if estoque and estoque > 0:
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter estoque inicial. O estoque deve ser gerenciado nas variaÃ§Ãµes.",
            )

    # ========================================
    # ðŸ”’ VALIDAÃ‡ÃƒO: VARIAÃ‡ÃƒO DUPLICADA
    # ========================================
    # Se estÃ¡ criando uma VARIAÃ‡ÃƒO, verificar duplicidade por signature
    variation_sig = getattr(produto, "variation_signature", None)
    if produto.produto_pai_id and variation_sig:
        variacao_existente = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                Produto.produto_pai_id == produto.produto_pai_id,
                Produto.variation_signature == variation_sig,
                Produto.ativo.is_(True),
            )
            .first()
        )

        if variacao_existente:
            raise HTTPException(
                status_code=409,
                detail=f"âŒ JÃ¡ existe uma variaÃ§Ã£o com os mesmos atributos para este produto. VariaÃ§Ã£o existente: '{variacao_existente.nome}' (ID: {variacao_existente.id})",
            )

    # ========================================
    # ðŸ”’ PREDECESSOR/SUCESSOR: Marcar predecessor como descontinuado
    # ========================================
    if produto.produto_predecessor_id:
        predecessor = (
            db.query(Produto)
            .filter(
                Produto.id == produto.produto_predecessor_id,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )

        if not predecessor:
            raise HTTPException(
                status_code=404, detail="Produto predecessor nÃ£o encontrado"
            )

        # Marcar predecessor como descontinuado
        predecessor.data_descontinuacao = datetime.utcnow()
        if produto.motivo_descontinuacao:
            predecessor.motivo_descontinuacao = produto.motivo_descontinuacao
        else:
            predecessor.motivo_descontinuacao = f"SubstituÃ­do por: {produto.nome}"

        logger.info(
            f"ðŸ“¦ Produto predecessor {predecessor.id} marcado como descontinuado"
        )

    # ========================================
    # DELEGAR PARA SERVICE LAYER
    # ========================================

    try:
        # Preparar dados do produto
        produto_data = _normalizar_promocao_erp_payload(
            _normalizar_payload_granel(_normalizar_payload_racao(produto.model_dump()))
        )

        # Adicionar user_id aos dados (necessÃ¡rio para o modelo)
        produto_data["user_id"] = current_user.id

        # Chamar service com regras de negÃ³cio
        novo_produto = ProdutoService.create_produto(
            dados=produto_data, db=db, tenant_id=tenant_id
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
    page_size: int = 50,
    busca: Optional[str] = None,
    categoria_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    departamento_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    fornecedor_grupo_id: Optional[int] = None,
    estoque_baixo: Optional[bool] = False,
    em_promocao: Optional[bool] = False,
    ativo: Optional[bool] = True,
    contar_total: bool = True,
    incluir_imagens: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista apenas produtos VENDÃVEIS (SIMPLES, VARIACAO e KIT)

    Usado pelo PDV e carrinho de vendas.
    Produtos PAI nÃ£o aparecem pois nÃ£o sÃ£o vendÃ¡veis diretamente.
    """
    user, tenant_id = user_and_tenant
    page, page_size, offset = _normalizar_paginacao_produtos(
        page,
        page_size,
        max_page_size=100,
    )

    # QUERY BASE - Produtos vendÃ¡veis (incluindo KIT)
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo.is_(True),
        Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),  # KIT Ã© vendÃ¡vel!
    )

    # FILTROS OPCIONAIS
    termo_busca = (busca or "").strip()

    if termo_busca:
        # Busca por múltiplas palavras: todas as palavras precisam aparecer (qualquer ordem)
        # Ex: "golden castrado" acha "Ração Golden Gato Castrado Salmão"
        search_conditions = (
            _produto_search_conditions
            if contar_total
            else _produto_search_conditions_fast
        )
        for palavra in _palavras_busca_produto(termo_busca):
            query = query.filter(search_conditions(palavra))

    query = _aplicar_filtros_basicos_produtos(
        query,
        categoria_id=categoria_id,
        marca_id=marca_id,
        departamento_id=departamento_id,
        estoque_baixo=estoque_baixo,
        em_promocao=em_promocao,
    )

    fornecedor_ids_filtro, filtro_fornecedor_por_grupo = (
        _resolver_fornecedor_ids_filtro_produto(
            db,
            tenant_id=tenant_id,
            fornecedor_id=fornecedor_id,
            fornecedor_grupo_id=fornecedor_grupo_id,
            tenant_ids_fornecedores=[tenant_id],
        )
    )
    query = _aplicar_filtro_fornecedor_produto(
        query,
        fornecedor_ids=fornecedor_ids_filtro,
        filtro_por_grupo=filtro_fornecedor_por_grupo,
    )

    total = query.count() if contar_total else None

    # OrdenaÃ§Ã£o inteligente: prioriza match exato no cÃ³digo
    order_clause = _build_produto_search_order_clause(termo_busca)
    load_options = _load_options_listagem_produtos(
        incluir_imagens=incluir_imagens,
        incluir_lotes=False,
    )

    # QUERY FINAL
    produtos = (
        query.options(*load_options)
        .order_by(*order_clause)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    produtos = [p for p in produtos if p is not None]

    # PDV usa esta rota como busca rápida enquanto o operador digita/bipa.
    # Evitar cálculo detalhado de composição/custo aqui impede N+1 pesado por tecla.
    for produto in produtos:
        _enriquecer_produto_listagem(
            db,
            produto,
            tenant_id,
            {},
            incluir_detalhes_composto=False,
        )

    if total is None:
        total = offset + len(produtos)
    pages = (total + page_size - 1) // page_size

    return {
        "items": produtos,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
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
    fornecedor_grupo_id: Optional[int] = None,
    estoque_baixo: Optional[bool] = False,
    em_promocao: Optional[bool] = False,
    ativo: Optional[bool] = True,
    tipo_produto: Optional[str] = None,  # Filtro por tipo de produto
    produto_predecessor_id: Optional[int] = None,  # Buscar sucessores de um produto
    include_variations: Optional[bool] = False,
    busca_completa: bool = False,
    incluir_imagens: bool = False,
    incluir_lotes: bool = False,
    incluir_detalhes_composto: bool = False,
    incluir_inativos: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
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
    termo_busca = (busca or "").strip()
    ativo = _normalizar_filtro_ativo_produtos(ativo, incluir_inativos)

    # Incluir produtos de tenants parceiros (ex.: pet shop parceiro da clínica)
    access_ids = get_all_accessible_tenant_ids(db, tenant_id)

    # QUERY BASE
    # - include_variations=True: inclui PAI para permitir visualização da hierarquia
    # - include_variations=False: lista apenas produtos normais (SIMPLES e KIT)
    if produto_predecessor_id:
        query = db.query(Produto).filter(
            Produto.tenant_id.in_(access_ids),
            Produto.produto_predecessor_id == produto_predecessor_id,
        )
    elif tipo_produto:
        query = db.query(Produto).filter(
            Produto.tenant_id.in_(access_ids), Produto.tipo_produto == tipo_produto
        )
    else:
        query = db.query(Produto).filter(
            Produto.tenant_id.in_(access_ids),
            Produto.tipo_produto.in_(
                _tipos_base_listagem(include_variations, termo_busca)
            ),
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

    if termo_busca:
        # Busca por múltiplas palavras: todas as palavras precisam aparecer (qualquer ordem)
        # Ex: "special dog senior" encontra "Racao Special Dog Ultralife Senior"
        search_conditions = (
            _produto_search_conditions
            if busca_completa
            else _produto_search_conditions_fast
        )
        for palavra in _palavras_busca_produto(termo_busca):
            query = query.filter(search_conditions(palavra))

    query = _aplicar_filtros_basicos_produtos(
        query,
        categoria_id=categoria_id,
        marca_id=marca_id,
        departamento_id=departamento_id,
        estoque_baixo=estoque_baixo,
        em_promocao=em_promocao,
    )

    fornecedor_ids_filtro, filtro_fornecedor_por_grupo = (
        _resolver_fornecedor_ids_filtro_produto(
            db,
            tenant_id=tenant_id,
            fornecedor_id=fornecedor_id,
            fornecedor_grupo_id=fornecedor_grupo_id,
            tenant_ids_fornecedores=access_ids,
        )
    )
    query = _aplicar_filtro_fornecedor_produto(
        query,
        fornecedor_ids=fornecedor_ids_filtro,
        filtro_por_grupo=filtro_fornecedor_por_grupo,
    )

    # TOTAL
    total = query.count()

    logger.info("GET /produtos/ - total encontrado: %s", total)

    # PAGINAÃ‡ÃƒO
    offset = (page - 1) * page_size

    order_clause = _build_produto_search_order_clause(termo_busca)

    load_options = _load_options_listagem_produtos(
        incluir_imagens=incluir_imagens,
        incluir_lotes=incluir_lotes,
    )

    # QUERY FINAL COM RELACIONAMENTOS
    produtos = (
        query.options(*load_options)
        .order_by(*order_clause)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # Filtro de seguranÃ§a: remover None
    produtos = [p for p in produtos if p is not None]

    reservas_por_produto = _mapa_reservas_ativas_multitenant(db, access_ids)
    validade_por_produto = _mapa_validade_proxima_produtos(db, produtos, access_ids)

    # HIERARQUIA: Para produtos PAI, buscar suas variaÃ§Ãµes
    # Para produtos KIT, calcular estoque virtual e carregar composiÃ§Ã£o
    produtos_expandidos = []
    for produto in produtos:
        # Se for PAI, contar variaÃ§Ãµes antes de adicionar
        if produto.tipo_produto == "PAI":
            total_variacoes = (
                db.query(func.count(Produto.id))
                .filter(
                    Produto.produto_pai_id == produto.id,
                    Produto.tipo_produto == "VARIACAO",
                    Produto.ativo.is_(True),
                )
                .scalar()
            )
            produto.total_variacoes = total_variacoes or 0

        _enriquecer_produto_listagem(
            db,
            produto,
            tenant_id,
            reservas_por_produto,
            incluir_detalhes_composto=incluir_detalhes_composto,
            validade_por_produto=validade_por_produto,
        )
        produtos_expandidos.append(produto)

        # Se for PAI, buscar e incluir suas variaÃ§Ãµes logo apÃ³s
        # apenas quando a tela pedir explicitamente include_variations.
        if include_variations and not termo_busca and produto.tipo_produto == "PAI":
            variacoes = (
                db.query(Produto)
                .filter(
                    Produto.produto_pai_id == produto.id,
                    Produto.tipo_produto == "VARIACAO",
                    Produto.ativo.is_(True),
                )
                .options(*load_options)
                .order_by(Produto.nome)
                .all()
            )
            validade_por_variacao = _mapa_validade_proxima_produtos(
                db,
                variacoes,
                access_ids,
            )

            for variacao in variacoes:
                _enriquecer_produto_listagem(
                    db,
                    variacao,
                    tenant_id,
                    reservas_por_produto,
                    incluir_detalhes_composto=incluir_detalhes_composto,
                    validade_por_produto=validade_por_variacao,
                )
                produtos_expandidos.append(variacao)

    pages = (total + page_size - 1) // page_size

    return {
        "items": produtos_expandidos,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/{produto_id}/variacoes", response_model=List[ProdutoResponse])
def listar_variacoes_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
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
    produto_pai = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto_pai:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    if produto_pai.tipo_produto != "PAI":
        raise HTTPException(
            status_code=400,
            detail="Produto nÃ£o Ã© do tipo PAI (nÃ£o possui variaÃ§Ãµes)",
        )

    # Buscar variaÃ§Ãµes
    variacoes = (
        db.query(Produto)
        .filter(
            Produto.produto_pai_id == produto_id,
            Produto.tipo_produto == "VARIACAO",
            Produto.ativo.is_(True),  # Filtrar apenas variaÃ§Ãµes ativas
            Produto.tenant_id == tenant_id,
        )
        .options(joinedload(Produto.imagens), joinedload(Produto.lotes))
        .order_by(Produto.nome)
        .all()
    )

    logger.info(
        f"ðŸ“¦ Produto PAI #{produto_id} possui {len(variacoes)} variaÃ§Ãµes ativas"
    )

    return variacoes


@router.get("/{produto_id}/variacoes/excluidas", response_model=List[ProdutoResponse])
def listar_variacoes_excluidas(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista variaÃ§Ãµes excluÃ­das (soft-deleted) de um produto PAI
    Permite visualizar, restaurar ou excluir definitivamente
    """

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe e Ã© PAI
    produto_pai = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto_pai:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    if produto_pai.tipo_produto != "PAI":
        raise HTTPException(
            status_code=400,
            detail="Produto nÃ£o Ã© do tipo PAI (nÃ£o possui variaÃ§Ãµes)",
        )

    # Buscar variaÃ§Ãµes excluÃ­das
    variacoes_excluidas = (
        db.query(Produto)
        .filter(
            Produto.produto_pai_id == produto_id,
            Produto.tipo_produto == "VARIACAO",
            Produto.ativo.is_(False),  # Apenas inativas (excluÃ­das)
            Produto.tenant_id == tenant_id,
        )
        .options(joinedload(Produto.imagens), joinedload(Produto.lotes))
        .order_by(Produto.updated_at.desc())
        .all()
    )

    logger.info(
        f"ðŸ—‘ï¸ Produto PAI #{produto_id} possui {len(variacoes_excluidas)} variaÃ§Ãµes excluÃ­das"
    )

    return variacoes_excluidas


@router.patch("/{produto_id}/restaurar", response_model=ProdutoResponse)
def restaurar_variacao(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Restaura uma variaÃ§Ã£o excluÃ­da (reativa)
    """

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.tipo_produto == "VARIACAO",
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="VariaÃ§Ã£o nÃ£o encontrada")

    if produto.ativo:
        raise HTTPException(status_code=400, detail="VariaÃ§Ã£o jÃ¡ estÃ¡ ativa")

    # Restaurar
    _aplicar_status_ativo_produto(produto, True)

    db.commit()
    db.refresh(produto)

    logger.info(f"â™»ï¸ VariaÃ§Ã£o #{produto_id} restaurada com sucesso")

    return produto


@router.post("/fusao/preview")
@require_permission("produtos.editar")
def preview_fusao_produtos(
    payload: ProdutoFusaoPreviewRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Mostra conflitos de cadastro e impacto antes de fundir dois produtos."""
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    try:
        return montar_preview_fusao_produtos(
            db,
            tenant_id=tenant_id,
            principal_id=payload.produto_principal_id,
            duplicado_id=payload.produto_duplicado_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/fusao/executar")
@require_permission("produtos.editar")
def executar_fusao_produtos_endpoint(
    payload: ProdutoFusaoExecutarRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Funde dois produtos transferindo historico e inativando o duplicado."""
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    try:
        return executar_fusao_produtos(
            db,
            tenant_id=tenant_id,
            principal_id=payload.produto_principal_id,
            duplicado_id=payload.produto_duplicado_id,
            decisoes_campos=payload.decisoes_campos,
            user_id=current_user.id,
            observacao=payload.observacao,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.error("Erro ao fundir produtos: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao fundir produtos: {exc}")


@router.delete("/{produto_id}/permanente", status_code=status.HTTP_204_NO_CONTENT)
def excluir_variacao_permanentemente(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Exclui DEFINITIVAMENTE uma variaÃ§Ã£o do banco de dados
    ATENÃ‡ÃƒO: Esta aÃ§Ã£o Ã© irreversÃ­vel!
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.tipo_produto == "VARIACAO",
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="VariaÃ§Ã£o nÃ£o encontrada")

    if produto.ativo:
        raise HTTPException(
            status_code=400,
            detail="NÃ£o Ã© possÃ­vel excluir permanentemente uma variaÃ§Ã£o ativa. Exclua-a primeiro (soft delete).",
        )

    # Excluir DEFINITIVAMENTE
    db.delete(produto)
    db.commit()

    logger.warning(
        f"âš ï¸ VariaÃ§Ã£o #{produto_id} EXCLUÃDA PERMANENTEMENTE do banco de dados"
    )

    return None


@router.get("/{produto_id}", response_model=ProdutoResponse)
def obter_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    ObtÃ©m detalhes completos de um produto

    Para produtos do tipo KIT:
    - Retorna composicao_kit (lista de componentes)
    - Retorna estoque_virtual (calculado automaticamente se tipo_kit=VIRTUAL)
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .options(
            joinedload(Produto.imagens),
            joinedload(Produto.categoria),
            joinedload(Produto.marca),
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    # Preparar resposta base
    response_data = {
        **produto.__dict__,
        "categoria": produto.categoria,
        "marca": produto.marca,
        "imagens": produto.imagens,
        "lotes": produto.lotes,
        "composicao_kit": [],
        "estoque_virtual": None,
        "estoque_disponivel": None,
    }

    # ========================================
    # PROCESSAR PRODUTOS DO TIPO KIT ou VARIACAO-KIT
    # ========================================
    if produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit:
        from .services.kit_estoque_service import KitEstoqueService
        from .services.kit_custo_service import KitCustoService

        # Buscar composiÃ§Ã£o do KIT
        composicao = KitEstoqueService.obter_detalhes_composicao(
            db,
            produto_id,
            tenant_id=getattr(produto, "tenant_id", tenant_id),
        )
        response_data["composicao_kit"] = composicao
        response_data["preco_custo"] = float(
            KitCustoService.calcular_custo_kit(produto_id, db)
        )

        # Calcular estoque virtual (se for KIT VIRTUAL)
        if produto.tipo_kit == "VIRTUAL":
            estoque_virtual = KitEstoqueService.calcular_estoque_virtual_kit(
                db,
                produto_id,
                tenant_id=getattr(produto, "tenant_id", tenant_id),
            )
            response_data["estoque_virtual"] = estoque_virtual
            logger.info(f"ðŸ§© Kit #{produto_id}: estoque_virtual={estoque_virtual}")
        else:
            # KIT FÃSICO usa estoque prÃ³prio
            response_data["estoque_virtual"] = int(produto.estoque_atual or 0)

    # Mapear tipo_kit para e_kit_fisico (compatibilidade com frontend)
    response_data["e_kit_fisico"] = produto.tipo_kit == "FISICO"

    # Calcular estoque reservado (pedidos Bling em aberto)
    try:
        from app.estoque_reserva_service import EstoqueReservaService

        response_data["estoque_reservado"] = float(
            EstoqueReservaService.quantidade_reservada_produto(db, tenant_id, produto)
            or 0.0
        )
    except Exception:
        response_data["estoque_reservado"] = 0.0

    if produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit == "VIRTUAL":
        response_data["estoque_disponivel"] = float(
            response_data.get("estoque_virtual") or 0
        )
    else:
        response_data["estoque_disponivel"] = max(
            float(produto.estoque_atual or 0)
            - float(response_data.get("estoque_reservado") or 0),
            0.0,
        )

    promocao_pdv = _resolver_promocao_erp_produto(produto)
    response_data["preco_venda_original"] = promocao_pdv["preco_regular"]
    response_data["preco_venda_pdv"] = promocao_pdv["preco_pdv"]
    response_data["preco_venda_efetivo"] = promocao_pdv["preco_pdv"]
    response_data["promocao_pdv_ativa"] = promocao_pdv["promocao_ativa"]
    response_data["promocao_origem_pdv"] = (
        "Promocao ERP" if promocao_pdv["promocao_ativa"] else None
    )
    response_data["desconto_promocional_pdv"] = promocao_pdv["desconto"]

    return response_data


@router.put("/{produto_id}", response_model=ProdutoResponse)
@require_permission("produtos.editar")
def atualizar_produto(
    produto_id: int,
    produto_update: ProdutoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza um produto

    Para produtos KIT:
    - Pode atualizar composicao_kit (diff inteligente)
    - Pode alterar tipo_kit (VIRTUAL <-> FISICO)
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    # Verificar se novo SKU jÃ¡ existe
    if produto_update.codigo is not None:
        produto_update.codigo = _normalizar_sku_produto(produto_update.codigo)
        if produto_update.codigo.lower() != str(produto.codigo or "").strip().lower():
            _validar_sku_unico(
                db, produto_update.codigo, tenant_id, produto_id=produto_id
            )

    # Verificar se novo cÃ³digo de barras jÃ¡ existe
    if (
        produto_update.codigo_barras
        and produto_update.codigo_barras != produto.codigo_barras
    ):
        existe_barcode = (
            db.query(Produto)
            .filter(
                Produto.codigo_barras == produto_update.codigo_barras,
                Produto.tenant_id == tenant_id,
                Produto.id != produto_id,
            )
            .first()
        )

        if existe_barcode:
            raise HTTPException(
                status_code=400,
                detail=f"CÃ³digo de barras '{produto_update.codigo_barras}' jÃ¡ cadastrado",
            )

    # Extrair dados
    dados_recebidos = produto_update.model_dump(exclude_unset=True)
    composicao_kit = dados_recebidos.pop("composicao_kit", None)

    dados_recebidos = _normalizar_payload_granel(
        _normalizar_payload_racao(dados_recebidos)
    )
    dados_recebidos = _normalizar_promocao_erp_payload(dados_recebidos, produto)

    # ========================================
    # ï¿½ðŸ”’ TRAVA 3 â€” VALIDAÃ‡ÃƒO: PRODUTO PAI NÃƒO TEM PREÃ‡O (ATUALIZAÃ‡ÃƒO)
    # ========================================
    is_parent_atual = produto.is_parent
    is_parent_novo = dados_recebidos.get("is_parent", is_parent_atual)

    if is_parent_novo:
        # Bloquear alteraÃ§Ã£o de preÃ§o em produto PAI
        if (
            "preco_venda" in dados_recebidos
            and dados_recebidos["preco_venda"]
            and dados_recebidos["preco_venda"] > 0
        ):
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter preÃ§o de venda. O preÃ§o deve ser definido nas variaÃ§Ãµes individuais.",
            )

        # Bloquear alteraÃ§Ã£o de estoque em produto PAI
        if (
            "estoque_atual" in dados_recebidos
            and dados_recebidos["estoque_atual"]
            and dados_recebidos["estoque_atual"] > 0
        ):
            raise HTTPException(
                status_code=400,
                detail="âŒ Produto pai nÃ£o pode ter estoque. O estoque deve ser gerenciado nas variaÃ§Ãµes.",
            )

    # ========================================
    # ðŸ”’ VALIDAÃ‡ÃƒO: VARIAÃ‡ÃƒO DUPLICADA (ATUALIZAÃ‡ÃƒO)
    # ========================================
    # Se estÃ¡ atualizando signature de uma VARIAÃ‡ÃƒO, verificar duplicidade
    if (
        "variation_signature" in dados_recebidos
        and dados_recebidos["variation_signature"]
    ):
        variacao_existente = (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                Produto.produto_pai_id == produto.produto_pai_id,
                Produto.variation_signature == dados_recebidos["variation_signature"],
                Produto.id != produto_id,  # Excluir o prÃ³prio produto
                Produto.ativo.is_(True),
            )
            .first()
        )

        if variacao_existente:
            raise HTTPException(
                status_code=409,
                detail=f"âŒ JÃ¡ existe uma variaÃ§Ã£o com os mesmos atributos para este produto. VariaÃ§Ã£o existente: '{variacao_existente.nome}' (ID: {variacao_existente.id})",
            )

    tipo_produto_final = dados_recebidos.get("tipo_produto", produto.tipo_produto)
    tipo_kit_informado = "tipo_kit" in dados_recebidos
    remover_tipo_kit = tipo_kit_informado and not dados_recebidos.get("tipo_kit")

    # ========================================
    # PROCESSAR e_kit_fisico -> tipo_kit
    # ========================================
    if "e_kit_fisico" in dados_recebidos:
        e_kit_fisico = dados_recebidos.pop("e_kit_fisico")
        if (
            tipo_produto_final in ("KIT", "VARIACAO")
            and not remover_tipo_kit
            and (
                tipo_kit_informado
                or bool(dados_recebidos.get("tipo_kit", produto.tipo_kit))
            )
        ):
            dados_recebidos["tipo_kit"] = "FISICO" if e_kit_fisico else "VIRTUAL"

    tipo_kit_final = dados_recebidos.get("tipo_kit", produto.tipo_kit)
    produto_sera_composto = tipo_produto_final in ("KIT", "VARIACAO") and bool(
        tipo_kit_final
    )
    produto_sera_granel = bool(
        dados_recebidos.get("e_granel", produto.e_granel)
    ) or _nome_indica_granel(dados_recebidos.get("nome", produto.nome))

    if produto_sera_granel:
        dados_recebidos["e_granel"] = True
        dados_recebidos["tipo_produto"] = "SIMPLES"
        dados_recebidos["tipo_kit"] = None
        dados_recebidos["unidade"] = "KG"
        dados_recebidos["participa_sugestao_compra"] = False
        tipo_produto_final = "SIMPLES"
        tipo_kit_final = None
        produto_sera_composto = False

    # ========================================
    # ATUALIZAR COMPOSIÃ‡ÃƒO DO KIT (se enviado)
    # ========================================
    if composicao_kit is not None and produto_sera_composto:
        from .services.kit_estoque_service import KitEstoqueService

        # âš ï¸ VALIDAÃ‡ÃƒO OBRIGATÃ“RIA: KIT deve ter pelo menos 1 componente
        if len(composicao_kit) == 0:
            raise HTTPException(
                status_code=400,
                detail="Produto do tipo KIT deve ter pelo menos 1 componente na composiÃ§Ã£o. Adicione os produtos que fazem parte do kit antes de salvar.",
            )

        # Validar novos componentes
        valido, erro = KitEstoqueService.validar_componentes_kit(
            db=db, kit_id=produto_id, componentes=composicao_kit
        )

        if not valido:
            raise HTTPException(
                status_code=400, detail=f"ComposiÃ§Ã£o invÃ¡lida: {erro}"
            )

        # Remover componentes antigos
        db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.kit_id == produto_id
        ).delete()

        # Adicionar novos componentes
        for comp in composicao_kit:
            novo_comp = ProdutoKitComponente(
                kit_id=produto_id,
                produto_componente_id=comp.get("produto_componente_id"),
                quantidade=comp.get("quantidade", 1.0),
                ordem=comp.get("ordem", 0),
                opcional=comp.get("opcional", False),
                tenant_id=produto.tenant_id,
            )
            db.add(novo_comp)

        logger.info(
            f"ðŸ§© ComposiÃ§Ã£o do Kit #{produto_id} atualizada: {len(composicao_kit)} componentes"
        )
    elif composicao_kit is not None and not produto_sera_composto:
        db.query(ProdutoKitComponente).filter(
            ProdutoKitComponente.kit_id == produto_id
        ).delete()
        logger.info(
            f"🧹 Composição removida do produto #{produto_id} ao desmarcar o kit"
        )

    # ========================================
    # ATUALIZAR CAMPOS DO PRODUTO
    # ========================================
    custo_componente_alterado = "preco_custo" in dados_recebidos

    for key, value in dados_recebidos.items():
        setattr(produto, key, value)

    if not bool(produto.ativo) or produto.situacao is False:
        produto.anunciar_ecommerce = False
        produto.anunciar_app = False

    produto.updated_at = datetime.utcnow()

    try:
        from .services.kit_custo_service import KitCustoService

        db.flush()

        if KitCustoService.produto_usa_custo_por_componentes(produto):
            KitCustoService.sincronizar_custo_kit(db, produto.id)

        if custo_componente_alterado:
            KitCustoService.recalcular_kits_que_usam_produto(db, produto.id)

        if (
            produto.tipo_produto in ("KIT", "VARIACAO")
            and produto.tipo_kit == "VIRTUAL"
        ):
            from .services.kit_estoque_service import KitEstoqueService

            produto.estoque_atual = float(
                KitEstoqueService.calcular_estoque_virtual_kit(
                    db,
                    produto.id,
                    tenant_id=getattr(produto, "tenant_id", tenant_id),
                )
            )
            db.add(produto)

        db.commit()
        db.refresh(produto)
        logger.info(f"âœ… Produto #{produto_id} atualizado com sucesso")

        # Notificar clientes "Avise-me" se estoque voltou ao positivo
        if (
            "estoque_atual" in dados_recebidos
            and produto.estoque_atual
            and produto.estoque_atual > 0
        ):
            try:
                from app.routes.ecommerce_notify_routes import (
                    notificar_clientes_estoque_disponivel,
                )

                notificar_clientes_estoque_disponivel(
                    db, str(tenant_id), produto_id, produto.nome
                )
            except Exception as _notify_err:
                logger.warning(
                    f"Aviso: erro ao enviar notificacoes avise-me: {_notify_err}"
                )

        # Retornar com composiÃ§Ã£o e estoque virtual
        return obter_produto(produto_id, db, user_and_tenant)

    except Exception as e:
        db.rollback()
        logger.error(f"âŒ Erro ao atualizar produto: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao atualizar produto: {str(e)}"
        )


# ============================================================================
# ATUALIZAÃ‡ÃƒO EM LOTE
# ============================================================================


@router.patch("/atualizar-lote")
def atualizar_produtos_lote(
    dados: AtualizacaoLoteRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza dados comerciais e operacionais de mÃºltiplos produtos."""
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    logger.info(f"ðŸ“¦ Atualizando {len(dados.produto_ids)} produtos em lote")

    # Buscar produtos
    produtos = (
        db.query(Produto)
        .filter(Produto.id.in_(dados.produto_ids), Produto.tenant_id == tenant_id)
        .all()
    )

    if not produtos:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado")

    # Validar se todos os produtos pertencem ao usuÃ¡rio
    if len(produtos) != len(dados.produto_ids):
        raise HTTPException(
            status_code=400,
            detail="Alguns produtos nÃ£o foram encontrados ou nÃ£o pertencem ao usuÃ¡rio",
        )

    if dados.fornecedor_operacao:
        if dados.fornecedor_operacao not in OPERACOES_FORNECEDOR_LOTE:
            raise HTTPException(
                status_code=400,
                detail="Operacao de fornecedor invalida",
            )
        if (
            dados.fornecedor_operacao in {"adicionar", "definir_principal"}
            and dados.fornecedor_id is None
        ):
            raise HTTPException(
                status_code=400,
                detail="Informe o fornecedor para aplicar a operacao em lote",
            )
        if dados.fornecedor_id is not None:
            _validar_fornecedor_produto_lote(db, dados.fornecedor_id, tenant_id)
    elif dados.fornecedor_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Informe a operacao do fornecedor para atualizar em lote",
        )

    linha_racao_selecionada = None
    if dados.linha_racao_id is not None:
        from .opcoes_racao_models import LinhaRacao

        linha_racao_selecionada = (
            db.query(LinhaRacao)
            .filter(
                LinhaRacao.id == dados.linha_racao_id,
                LinhaRacao.tenant_id == tenant_id,
            )
            .first()
        )

    # Atualizar campos fornecidos
    atualizado = 0
    for produto in produtos:
        if dados.ativo is not None:
            if not dados.ativo:
                _validar_pode_inativar_produto(db, produto, tenant_id)
            if (
                bool(produto.ativo) != dados.ativo
                or bool(produto.situacao) != dados.ativo
            ):
                atualizado += 1
            _aplicar_status_ativo_produto(produto, dados.ativo)
        if dados.marca_id is not None:
            produto.marca_id = dados.marca_id
            atualizado += 1
        if dados.eh_racao is not None:
            produto.tipo = "ração" if dados.eh_racao else "produto"
            atualizado += 1
            if not dados.eh_racao:
                produto.classificacao_racao = None
                produto.peso_embalagem = None
                produto.categoria_racao = None
                produto.especies_indicadas = None
                produto.linha_racao_id = None
                produto.porte_animal_id = None
                produto.fase_publico_id = None
                produto.tipo_tratamento_id = None
                produto.sabor_proteina_id = None
                produto.apresentacao_peso_id = None
        if dados.classificacao_racao is not None and dados.eh_racao is not False:
            produto.classificacao_racao = _normalizar_classificacao_racao(
                dados.classificacao_racao
            )
            if produto.classificacao_racao:
                produto.tipo = "ração"
            atualizado += 1
        if dados.categoria_id is not None:
            produto.categoria_id = dados.categoria_id
            atualizado += 1
        if dados.departamento_id is not None:
            produto.departamento_id = dados.departamento_id
            atualizado += 1
        if dados.fornecedor_operacao:
            if _aplicar_fornecedor_produto_lote(
                db,
                produto,
                dados.fornecedor_id,
                dados.fornecedor_operacao,
                tenant_id,
                remover_outros=bool(dados.fornecedor_remover_outros),
            ):
                atualizado += 1
        if dados.linha_racao_id is not None:
            produto.linha_racao_id = dados.linha_racao_id
            if dados.eh_racao is not False and linha_racao_selecionada:
                produto.classificacao_racao = _normalizar_classificacao_racao(
                    linha_racao_selecionada.nome
                )
                produto.tipo = "ração"
            atualizado += 1
        if dados.porte_animal_id is not None:
            produto.porte_animal_id = dados.porte_animal_id
            atualizado += 1
        if dados.fase_publico_id is not None:
            produto.fase_publico_id = dados.fase_publico_id
            atualizado += 1
        if dados.tipo_tratamento_id is not None:
            produto.tipo_tratamento_id = dados.tipo_tratamento_id
            atualizado += 1
        if dados.sabor_proteina_id is not None:
            produto.sabor_proteina_id = dados.sabor_proteina_id
            atualizado += 1
        if dados.apresentacao_peso_id is not None:
            produto.apresentacao_peso_id = dados.apresentacao_peso_id
            atualizado += 1
        if dados.categoria_racao is not None:
            produto.categoria_racao = dados.categoria_racao
            atualizado += 1
        if dados.especies_indicadas is not None:
            produto.especies_indicadas = dados.especies_indicadas
            atualizado += 1
        if dados.controle_lote is not None:
            produto.controle_lote = dados.controle_lote
            atualizado += 1
        if dados.estoque_minimo is not None:
            produto.estoque_minimo = dados.estoque_minimo
            atualizado += 1
        if dados.estoque_maximo is not None:
            produto.estoque_maximo = dados.estoque_maximo
            atualizado += 1

        produto_ativo_loja = bool(getattr(produto, "ativo", True)) and bool(
            getattr(produto, "situacao", True)
        )
        if not produto_ativo_loja:
            if bool(getattr(produto, "anunciar_ecommerce", False)):
                atualizado += 1
            if bool(getattr(produto, "anunciar_app", False)):
                atualizado += 1
            produto.anunciar_ecommerce = False
            produto.anunciar_app = False
        else:
            if dados.anunciar_ecommerce is not None:
                if produto.anunciar_ecommerce != dados.anunciar_ecommerce:
                    atualizado += 1
                produto.anunciar_ecommerce = dados.anunciar_ecommerce
            if dados.anunciar_app is not None:
                if produto.anunciar_app != dados.anunciar_app:
                    atualizado += 1
                produto.anunciar_app = dados.anunciar_app

        produto.updated_at = datetime.utcnow()

    db.commit()

    logger.info(f"âœ… {len(produtos)} produtos atualizados em lote")

    return {
        "produtos_atualizados": len(produtos),
        "campos_atualizados": atualizado,
        "ativo": dados.ativo,
        "eh_racao": dados.eh_racao,
        "classificacao_racao": dados.classificacao_racao,
        "marca_id": dados.marca_id,
        "categoria_id": dados.categoria_id,
        "departamento_id": dados.departamento_id,
        "fornecedor_id": dados.fornecedor_id,
        "fornecedor_operacao": dados.fornecedor_operacao,
        "fornecedor_remover_outros": dados.fornecedor_remover_outros,
        "linha_racao_id": dados.linha_racao_id,
        "porte_animal_id": dados.porte_animal_id,
        "fase_publico_id": dados.fase_publico_id,
        "tipo_tratamento_id": dados.tipo_tratamento_id,
        "sabor_proteina_id": dados.sabor_proteina_id,
        "apresentacao_peso_id": dados.apresentacao_peso_id,
        "categoria_racao": dados.categoria_racao,
        "especies_indicadas": dados.especies_indicadas,
        "controle_lote": dados.controle_lote,
        "estoque_minimo": dados.estoque_minimo,
        "estoque_maximo": dados.estoque_maximo,
        "anunciar_ecommerce": dados.anunciar_ecommerce,
        "anunciar_app": dados.anunciar_app,
    }


@router.patch("/{produto_id}")
def atualizar_preco_produto(
    produto_id: int,
    preco_venda: Optional[float] = None,
    preco_custo: Optional[float] = None,
    preco_promocional: Optional[float] = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza apenas o preÃ§o de um produto (ediÃ§Ã£o rÃ¡pida)"""

    current_user, tenant_id = user_and_tenant
    logger.info(f"ðŸ·ï¸ Atualizando preÃ§o do produto {produto_id}")

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

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
        "preco_promocional": produto.preco_promocional,
    }


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Deleta (soft delete) um produto"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    _validar_pode_inativar_produto(db, produto, tenant_id)

    # Soft delete
    _aplicar_status_ativo_produto(produto, False)

    db.commit()

    return None


@router.patch("/{produto_id}/ativo", response_model=ProdutoResponse)
@require_permission("produtos.editar")
def atualizar_status_ativo_produto(
    produto_id: int,
    payload: ProdutoAtivoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Ativa ou desativa produto sem removÃª-lo do sistema."""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    produto = _obter_produto_ou_404(db, produto_id, tenant_id)

    if payload.ativo == bool(produto.ativo):
        return produto

    if not payload.ativo:
        _validar_pode_inativar_produto(db, produto, tenant_id)

    _aplicar_status_ativo_produto(produto, payload.ativo)

    db.commit()
    db.refresh(produto)

    logger.info(
        "ðŸ” Produto %s #%s com status alterado para %s",
        produto.nome,
        produto.id,
        "ativo" if payload.ativo else "inativo",
    )

    return produto


@router.post("/gerar-sku")
def gerar_sku(
    prefixo: str = "PROD",
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Gera um SKU Ãºnico automaticamente
    Formato: {PREFIXO}-{NÃšMERO_SEQUENCIAL}
    Exemplo: PROD-00001
    """
    _, tenant_id = user_and_tenant
    prefixo = _normalizar_sku_produto(prefixo).upper()

    # Buscar maior numero ja usado com esse prefixo dentro do tenant atual.
    ultimo_produto = (
        db.query(Produto)
        .filter(Produto.tenant_id == tenant_id, Produto.codigo.ilike(f"{prefixo}-%"))
        .order_by(Produto.id.desc())
        .first()
    )

    if ultimo_produto:
        # Extrair número do último SKU
        try:
            ultimo_numero = int(ultimo_produto.codigo.split("-")[-1])
            proximo_numero = ultimo_numero + 1
        except ValueError:
            proximo_numero = 1
    else:
        proximo_numero = 1

    # Gerar novo SKU
    novo_sku = f"{prefixo}-{proximo_numero:05d}"

    existe = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            func.lower(Produto.codigo) == novo_sku.lower(),
        )
        .first()
    )

    if existe:
        novo_sku = f"{prefixo}-{proximo_numero + 1:05d}"

    return {
        "sku": novo_sku,
        "prefixo": prefixo,
        "numero": proximo_numero,
        "disponivel": True,
    }


# ==========================================
# ENDPOINTS - LOTES E FIFO
# ==========================================


@router.post(
    "/{produto_id}/lotes",
    response_model=LoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_lote(
    produto_id: int,
    lote: LoteCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria um novo lote para o produto"""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    # Verificar se nÃºmero de lote jÃ¡ existe para este produto
    lote_existente = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto_id,
            ProdutoLote.nome_lote == lote.nome_lote,
        )
        .first()
    )

    if lote_existente:
        raise HTTPException(
            status_code=400,
            detail=f"Lote '{lote.nome_lote}' jÃ¡ cadastrado para este produto",
        )

    # Criar lote com timestamp para FIFO
    import time

    novo_lote = ProdutoLote(
        **lote.model_dump(),
        produto_id=produto_id,
        quantidade_disponivel=lote.quantidade,
        ordem_entrada=int(time.time()),  # Unix timestamp para FIFO
    )

    db.add(novo_lote)

    # Atualizar estoque do produto
    produto.estoque_atual += lote.quantidade
    produto.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(novo_lote)

    # Sincronizar estoque com Bling em background
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto.id, float(produto.estoque_atual), "criacao_lote"
        )
    except Exception:
        pass

    return novo_lote


@router.get("/{produto_id}/lotes", response_model=List[LoteResponse])
def listar_lotes(
    produto_id: int,
    apenas_disponiveis: bool = False,  # Mostrar todos por padrÃ£o
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista lotes de um produto"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    logger.info(
        f"ðŸ“¦ Listando lotes do produto {produto_id} - apenas_disponiveis={apenas_disponiveis}"
    )

    # Verificar se produto existe
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    query = db.query(ProdutoLote).filter(
        ProdutoLote.produto_id == produto_id,
        ProdutoLote.status != "excluido",  # Apenas lotes nÃ£o excluÃ­dos
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
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza informaÃ§Ãµes de um lote"""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar lote
    lote = (
        db.query(ProdutoLote)
        .filter(ProdutoLote.id == lote_id, ProdutoLote.produto_id == produto_id)
        .first()
    )

    if not lote:
        raise HTTPException(status_code=404, detail="Lote nÃ£o encontrado")

    # Verificar se o produto pertence ao usuÃ¡rio
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

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

    # Sincronizar estoque com Bling em background
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto.id, float(produto.estoque_atual), "edicao_lote"
        )
    except Exception:
        pass

    return lote


@router.delete("/{produto_id}/lotes/{lote_id}")
def excluir_lote(
    produto_id: int,
    lote_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exclui um lote (soft delete)"""

    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar lote
    lote = (
        db.query(ProdutoLote)
        .filter(ProdutoLote.id == lote_id, ProdutoLote.produto_id == produto_id)
        .first()
    )

    if not lote:
        raise HTTPException(status_code=404, detail="Lote nÃ£o encontrado")

    # Verificar se o produto pertence ao usuÃ¡rio
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    # Atualizar estoque do produto (remover a quantidade do lote)
    produto.estoque_atual = produto.estoque_atual - lote.quantidade_disponivel

    # Soft delete - marcar como excluÃ­do
    lote.status = "excluido"
    lote.updated_at = datetime.utcnow()

    db.commit()

    # Sincronizar estoque com Bling em background
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto.id, float(produto.estoque_atual), "exclusao_lote"
        )
    except Exception:
        pass

    return {"message": "Lote excluÃ­do com sucesso"}


@router.post("/{produto_id}/entrada")
def entrada_estoque(
    produto_id: int,
    entrada: EntradaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Registra entrada de estoque criando um lote"""

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    # VALIDAÃ‡ÃƒO: Produto PAI nÃ£o pode ter movimentaÃ§Ã£o de estoque
    if produto.is_parent:
        raise HTTPException(
            status_code=400,
            detail="Produto pai nÃ£o pode ter entrada de estoque. Realize a entrada nas variaÃ§Ãµes do produto.",
        )

    # Verificar se lote jÃ¡ existe
    lote_existente = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto_id,
            ProdutoLote.nome_lote == entrada.nome_lote,
        )
        .first()
    )

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
            data_validade=entrada.data_validade
            or datetime.utcnow() + timedelta(days=365),  # Validade padrÃ£o 1 ano
            custo_unitario=entrada.preco_custo,
            ordem_entrada=int(time.time()),
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
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(movimentacao)

    db.commit()
    db.refresh(lote)

    # Sincronizar estoque com Bling em background (fire-and-forget)
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto.id, float(produto.estoque_atual), "entrada_estoque"
        )
    except Exception:
        pass

    return {
        "sucesso": True,
        "mensagem": "Entrada registrada com sucesso",
        "lote_id": lote.id,
        "nome_lote": lote.nome_lote,
        "quantidade_entrada": entrada.quantidade,
        "estoque_atual": produto.estoque_atual,
    }


@router.post("/{produto_id}/saida-fifo")
def saida_estoque_fifo(
    produto_id: int,
    saida: SaidaEstoqueRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Registra saÃ­da de estoque usando FIFO
    Consome lotes mais antigos primeiro
    """

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
            Produto.ativo.is_(True),
        )
        .first()
    )

    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    # VALIDAÃ‡ÃƒO: Produto PAI nÃ£o pode ter movimentaÃ§Ã£o de estoque
    if produto.is_parent:
        raise HTTPException(
            status_code=400,
            detail="Produto pai nÃ£o pode ter saÃ­da de estoque. Realize a saÃ­da nas variaÃ§Ãµes do produto.",
        )

    # Verificar se hÃ¡ estoque suficiente
    if produto.estoque_atual < saida.quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque insuficiente. DisponÃ­vel: {produto.estoque_atual}, Solicitado: {saida.quantidade}",
        )

    # Buscar lotes disponÃ­veis ordenados por FIFO (mais antigo primeiro)
    lotes = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto_id, ProdutoLote.quantidade_disponivel > 0
        )
        .order_by(ProdutoLote.ordem_entrada)
        .all()
    )

    if not lotes:
        raise HTTPException(status_code=400, detail="Nenhum lote disponÃ­vel")

    # Consumir lotes usando FIFO
    lotes_consumidos = _consumir_lotes_fifo_produto(lotes, saida.quantidade)

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
        lotes_consumidos=json.dumps(lotes_consumidos),
    )
    db.add(movimentacao)

    db.commit()

    # Sincronizar estoque com Bling em background (fire-and-forget)
    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto.id, float(produto.estoque_atual), "saida_fifo"
        )
    except Exception:
        pass

    return {
        "sucesso": True,
        "mensagem": "SaÃ­da registrada com sucesso usando FIFO",
        "quantidade_saida": saida.quantidade,
        "estoque_anterior": estoque_anterior,
        "estoque_atual": produto.estoque_atual,
        "lotes_consumidos": lotes_consumidos,
        "numero_pedido": saida.numero_pedido,
    }


# ==========================================
# ENDPOINTS - FORNECEDORES
# ==========================================


@router.post("/{produto_id}/fornecedores", response_model=FornecedorVinculoResponse)
def vincular_fornecedor(
    produto_id: int,
    dados: FornecedorVinculoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Vincular fornecedor a um produto

    - Pode ter mÃºltiplos fornecedores por produto
    - Apenas 1 pode ser principal
    - Fornecedor deve ser do tipo 'fornecedor' no cadastro de clientes
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    try:
        logger.info(
            f"[FORNECEDOR] Vinculando fornecedor {dados.fornecedor_id} ao produto {produto_id}"
        )

        # Verificar se produto existe e pertence ao usuÃ¡rio
        produto = (
            db.query(Produto)
            .filter(
                Produto.id == produto_id,
                Produto.tenant_id == tenant_id,
                Produto.situacao.is_(True),
            )
            .first()
        )

        if not produto:
            logger.error(f"[FORNECEDOR] Produto {produto_id} nÃ£o encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Produto nÃ£o encontrado"
            )

        logger.info(f"[FORNECEDOR] Produto encontrado: {produto.nome}")

        # Verificar se fornecedor existe e pertence ao usuÃ¡rio
        fornecedor = (
            db.query(Cliente)
            .filter(
                Cliente.id == dados.fornecedor_id,
                Cliente.tenant_id == tenant_id,
                Cliente.tipo_cadastro == "fornecedor",
            )
            .first()
        )

        if not fornecedor:
            logger.error(
                f"[FORNECEDOR] Fornecedor {dados.fornecedor_id} nÃ£o encontrado"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fornecedor nÃ£o encontrado ou nÃ£o Ã© do tipo fornecedor",
            )

        logger.info(f"[FORNECEDOR] Fornecedor encontrado: {fornecedor.nome}")

        # Verificar se jÃ¡ existe vÃ­nculo
        vinculo_existente = (
            db.query(ProdutoFornecedor)
            .filter(
                ProdutoFornecedor.produto_id == produto_id,
                ProdutoFornecedor.fornecedor_id == dados.fornecedor_id,
            )
            .first()
        )

        if vinculo_existente:
            logger.error("[FORNECEDOR] VÃ­nculo jÃ¡ existe")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fornecedor jÃ¡ vinculado a este produto",
            )

        vinculos_ativos_existentes = (
            db.query(ProdutoFornecedor)
            .filter(
                ProdutoFornecedor.produto_id == produto_id,
                ProdutoFornecedor.tenant_id == tenant_id,
                ProdutoFornecedor.ativo.is_(True),
            )
            .count()
        )
        sera_principal = bool(dados.e_principal) or vinculos_ativos_existentes == 0

        # Se for marcar como principal, desmarcar outros
        if sera_principal:
            logger.info("[FORNECEDOR] Desmarcando outros fornecedores principais")
            db.query(ProdutoFornecedor).filter(
                ProdutoFornecedor.produto_id == produto_id,
                ProdutoFornecedor.tenant_id == tenant_id,
                ProdutoFornecedor.e_principal.is_(True),
            ).update({"e_principal": False})

            # Atualizar fornecedor_id do produto
            produto.fornecedor_id = dados.fornecedor_id

        # Criar vÃ­nculo
        logger.info("[FORNECEDOR] Criando vÃ­nculo no banco")
        novo_vinculo = ProdutoFornecedor(
            produto_id=produto_id,
            fornecedor_id=dados.fornecedor_id,
            codigo_fornecedor=dados.codigo_fornecedor,
            preco_custo=dados.preco_custo,
            prazo_entrega=dados.prazo_entrega,
            estoque_fornecedor=dados.estoque_fornecedor,
            e_principal=sera_principal,
            tenant_id=tenant_id,
        )

        db.add(novo_vinculo)
        db.flush()
        _garantir_fornecedor_principal_quando_unico(db, produto, tenant_id)
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
            fornecedor_cpf_cnpj=fornecedor.cnpj
            if fornecedor.tipo_pessoa == "PJ"
            else fornecedor.cpf,
            fornecedor_email=fornecedor.email,
            fornecedor_telefone=fornecedor.telefone or fornecedor.celular,
        )

        logger.info("[FORNECEDOR] âœ… VÃ­nculo completado com sucesso")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FORNECEDOR] âŒ ERRO: {str(e)}")
        logger.error(f"[FORNECEDOR] Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao vincular fornecedor: {str(e)}",
        )


@router.get(
    "/{produto_id}/fornecedores", response_model=List[FornecedorVinculoResponse]
)
def listar_fornecedores_produto(
    produto_id: int,
    apenas_ativos: bool = True,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Listar todos os fornecedores vinculados a um produto
    Ordenados por: principal DESC, created_at ASC
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Verificar se produto existe e pertence ao usuÃ¡rio
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produto nÃ£o encontrado"
        )

    # Buscar fornecedores
    query = db.query(ProdutoFornecedor).filter(
        ProdutoFornecedor.produto_id == produto_id
    )

    if apenas_ativos:
        query = query.filter(ProdutoFornecedor.ativo.is_(True))

    vinculos = query.order_by(
        ProdutoFornecedor.e_principal.desc(), ProdutoFornecedor.created_at.asc()
    ).all()

    # Montar resposta com dados dos fornecedores
    resultado = []
    for vinculo in vinculos:
        fornecedor = (
            db.query(Cliente).filter(Cliente.id == vinculo.fornecedor_id).first()
        )

        if fornecedor:
            cpf_cnpj = (
                fornecedor.cnpj if fornecedor.tipo_pessoa == "PJ" else fornecedor.cpf
            )
            telefone = fornecedor.telefone or fornecedor.celular
        else:
            cpf_cnpj = None
            telefone = None

        resultado.append(
            FornecedorVinculoResponse(
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
                fornecedor_telefone=telefone,
            )
        )

    return resultado


@router.put("/fornecedores/{vinculo_id}", response_model=FornecedorVinculoResponse)
def atualizar_vinculo_fornecedor(
    vinculo_id: int,
    dados: FornecedorVinculoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualizar dados do vÃ­nculo fornecedor-produto
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar vÃ­nculo e verificar permissÃ£o
    vinculo = (
        db.query(ProdutoFornecedor)
        .join(Produto)
        .filter(ProdutoFornecedor.id == vinculo_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="VÃ­nculo nÃ£o encontrado"
        )

    produto = (
        db.query(Produto)
        .filter(
            Produto.id == vinculo.produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )

    # Se for marcar como principal, desmarcar outros
    if dados.e_principal and not vinculo.e_principal:
        db.query(ProdutoFornecedor).filter(
            ProdutoFornecedor.produto_id == vinculo.produto_id,
            ProdutoFornecedor.tenant_id == tenant_id,
            ProdutoFornecedor.e_principal.is_(True),
        ).update({"e_principal": False})

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

    if produto:
        _garantir_fornecedor_principal_quando_unico(db, produto, tenant_id)

    vinculo.updated_at = datetime.now()

    db.commit()
    db.refresh(vinculo)

    logger.info("Vinculo de fornecedor atualizado")

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
        fornecedor_cpf_cnpj=fornecedor.cnpj
        if (fornecedor and fornecedor.tipo_pessoa == "PJ")
        else (fornecedor.cpf if fornecedor else None),
        fornecedor_email=fornecedor.email if fornecedor else None,
        fornecedor_telefone=(fornecedor.telefone or fornecedor.celular)
        if fornecedor
        else None,
    )

    return response


@router.delete("/fornecedores/{vinculo_id}")
def desvincular_fornecedor(
    vinculo_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Desvincular fornecedor de um produto
    Remove o vÃ­nculo do banco de dados
    """
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar vÃ­nculo e verificar permissÃ£o
    vinculo = (
        db.query(ProdutoFornecedor)
        .join(Produto)
        .filter(ProdutoFornecedor.id == vinculo_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not vinculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="VÃ­nculo nÃ£o encontrado"
        )

    produto_id = vinculo.produto_id
    era_principal = vinculo.e_principal
    produto = (
        db.query(Produto)
        .filter(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )

    # Deletar vÃ­nculo
    db.delete(vinculo)

    # Se era principal, tentar promover outro
    if era_principal:
        outro_vinculo = (
            db.query(ProdutoFornecedor)
            .filter(
                ProdutoFornecedor.produto_id == produto_id,
                ProdutoFornecedor.tenant_id == tenant_id,
                ProdutoFornecedor.id != vinculo_id,
                ProdutoFornecedor.ativo.is_(True),
            )
            .first()
        )

        if outro_vinculo:
            outro_vinculo.e_principal = True
            if produto:
                produto.fornecedor_id = outro_vinculo.fornecedor_id
        else:
            # Nenhum fornecedor restante, remover do produto
            if produto:
                produto.fornecedor_id = None

    if produto:
        _garantir_fornecedor_principal_quando_unico(db, produto, tenant_id)

    db.commit()

    logger.info("Fornecedor desvinculado do produto")

    return {"message": "Fornecedor desvinculado com sucesso"}


# ==========================================
# HISTÃ“RICO DE PREÃ‡OS
# ==========================================


@router.get(
    "/{produto_id}/historico-precos", response_model=List[HistoricoPrecoResponse]
)
@require_permission("produtos.visualizar")
def listar_historico_precos(
    produto_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista histÃ³rico de alteraÃ§Ãµes de preÃ§os de um produto
    """
    current_user, tenant_id = user_and_tenant

    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nÃ£o encontrado")

    historicos = (
        db.query(ProdutoHistoricoPreco)
        .options(
            joinedload(ProdutoHistoricoPreco.user),
            joinedload(ProdutoHistoricoPreco.nota_entrada),
        )
        .filter(ProdutoHistoricoPreco.produto_id == produto_id)
        .order_by(ProdutoHistoricoPreco.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    resultado = []
    for hist in historicos:
        resultado.append(
            {
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
                "nota_numero": hist.nota_entrada.numero_nota
                if hist.nota_entrada
                else None,
                "nota_data_emissao": hist.nota_entrada.data_emissao
                if hist.nota_entrada
                else None,
                "referencia": hist.referencia,
                "observacoes": hist.observacoes,
                "usuario": hist.user.email if hist.user else None,
            }
        )

    return resultado


# ==================== CLASSIFICAï¿½ï¿½O INTELIGENTE DE RAï¿½ï¿½ES ====================


@router.post("/{produto_id}/classificar-ia")
async def classificar_produto_ia(
    produto_id: int,
    forcar: bool = False,  # Forï¿½a reclassificaï¿½ï¿½o mesmo se auto_classificar_nome = False
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Aplica classificaï¿½ï¿½o inteligente via IA em um produto
    Extrai automaticamente: porte, fase, tratamento, sabor e peso do nome
    """
    from .classificador_racao import classificar_produto

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    # Buscar produto
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Produto nï¿½o encontrado"
        )

    # Verificar se deve classificar
    if not forcar and not produto.auto_classificar_nome:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auto-classificaï¿½ï¿½o desativada para este produto. Use forcar=true para forï¿½ar.",
        )

    # Executar classificaï¿½ï¿½o
    resultado, confianca, metadata = classificar_produto(
        produto.nome, produto.peso_embalagem
    )

    # Importar models de lookup
    from .opcoes_racao_models import (
        PorteAnimal,
        FasePublico,
        TipoTratamento,
        SaborProteina,
        LinhaRacao,
    )

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
            "Peixes": "fish",
        }
        especie_db = mapa_especies.get(
            resultado["especie_indicada"], resultado["especie_indicada"].lower()
        )
        produto.especies_indicadas = especie_db
        campos_atualizados.append("especies_indicadas")

    # Buscar ID do porte baseado no nome retornado pela IA
    # Classificador retorna array, pegar primeiro elemento
    if resultado["porte_animal"] and len(resultado["porte_animal"]) > 0:
        nome_porte = resultado["porte_animal"][0]  # Pega primeiro porte do array
        porte = (
            db.query(PorteAnimal)
            .filter(
                PorteAnimal.tenant_id == tenant_id,
                PorteAnimal.nome == nome_porte,
                PorteAnimal.ativo.is_(True),
            )
            .first()
        )
        if porte:
            produto.porte_animal_id = porte.id
            campos_atualizados.append("porte_animal_id")

    # Buscar ID da fase baseado no nome retornado pela IA
    # Classificador retorna array, pegar primeiro elemento
    if resultado["fase_publico"] and len(resultado["fase_publico"]) > 0:
        nome_fase = resultado["fase_publico"][0]  # Pega primeira fase do array
        fase = (
            db.query(FasePublico)
            .filter(
                FasePublico.tenant_id == tenant_id,
                FasePublico.nome == nome_fase,
                FasePublico.ativo.is_(True),
            )
            .first()
        )
        if fase:
            produto.fase_publico_id = fase.id
            campos_atualizados.append("fase_publico_id")

    # Buscar ID do tipo de tratamento baseado no nome retornado pela IA
    # Classificador retorna array, pegar primeiro elemento
    if resultado["tipo_tratamento"] and len(resultado["tipo_tratamento"]) > 0:
        nome_tratamento = resultado["tipo_tratamento"][
            0
        ]  # Pega primeiro tratamento do array
        tratamento = (
            db.query(TipoTratamento)
            .filter(
                TipoTratamento.tenant_id == tenant_id,
                TipoTratamento.nome == nome_tratamento,
                TipoTratamento.ativo.is_(True),
            )
            .first()
        )
        if tratamento:
            produto.tipo_tratamento_id = tratamento.id
            campos_atualizados.append("tipo_tratamento_id")

    # Buscar ID do sabor/proteÃ­na baseado no nome retornado pela IA
    if resultado["sabor_proteina"]:
        sabor = (
            db.query(SaborProteina)
            .filter(
                SaborProteina.tenant_id == tenant_id,
                SaborProteina.nome == resultado["sabor_proteina"],
                SaborProteina.ativo.is_(True),
            )
            .first()
        )
        if sabor:
            produto.sabor_proteina_id = sabor.id
            campos_atualizados.append("sabor_proteina_id")

    # Buscar ID da linha de raÃ§Ã£o baseado no nome retornado pela IA
    if resultado.get("linha_racao"):
        linha = (
            db.query(LinhaRacao)
            .filter(
                LinhaRacao.tenant_id == tenant_id,
                LinhaRacao.nome == resultado["linha_racao"],
                LinhaRacao.ativo.is_(True),
            )
            .first()
        )
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
        "mensagem": f"Classificaï¿½ï¿½o aplicada com sucesso. Score: {confianca['score']}%",
    }


@router.post("/classificar-lote")
async def classificar_lote_produtos(
    produto_ids: List[
        int
    ] = None,  # Se None, classifica todos ativos com auto_classificar_nome=True
    apenas_sem_classificacao: bool = True,  # Sï¿½ classifica produtos sem classificaï¿½ï¿½o existente
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
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
        Produto.ativo.is_(True),
        Produto.auto_classificar_nome.is_(True),
    )

    # Filtrar por IDs especÃ­ficos se fornecido
    if produto_ids:
        query = query.filter(Produto.id.in_(produto_ids))

    # Filtrar apenas produtos sem classificaÃ§Ã£o completa
    if apenas_sem_classificacao:
        query = query.filter(
            (Produto.porte_animal.is_(None))
            | (Produto.fase_publico.is_(None))
            | (Produto.sabor_proteina.is_(None))
        )

    produtos = query.limit(100).all()  # Limite de seguranÃ§a

    sucesso = []
    erros = []

    for produto in produtos:
        try:
            resultado, confianca = classificar_produto(
                produto.nome, produto.peso_embalagem
            )

            campos_atualizados = []

            if resultado["especie_indicada"] and not produto.especies_indicadas:
                # Mapear para formato do banco
                mapa_especies = {
                    "CÃ£es": "dog",
                    "Gatos": "cat",
                    "PÃ¡ssaros": "bird",
                    "Roedores": "rodent",
                    "Peixes": "fish",
                }
                especie_db = mapa_especies.get(
                    resultado["especie_indicada"], resultado["especie_indicada"].lower()
                )
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

            sucesso.append(
                {
                    "produto_id": produto.id,
                    "nome": produto.nome,
                    "campos_atualizados": campos_atualizados,
                    "score": confianca["score"],
                }
            )

        except Exception as e:
            erros.append(
                {"produto_id": produto.id, "nome": produto.nome, "erro": str(e)}
            )

    return {
        "success": True,
        "total_processados": len(produtos),
        "sucessos": len(sucesso),
        "erros": len(erros),
        "detalhes_sucesso": sucesso,
        "detalhes_erros": erros,
    }


@router.get("/racao/alertas")
async def listar_racoes_sem_classificacao(
    limite: int = 50,
    offset: int = 0,
    especie: Optional[str] = None,  # Filtro por espÃ©cie: dog, cat, bird, rodent, fish
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista raï¿½ï¿½es sem classificaï¿½ï¿½o completa para alertas
    Filtra produtos classificados como raï¿½ï¿½o mas sem informaï¿½ï¿½es importantes

    ParÃ¢metros:
    - especie: Filtro opcional por espÃ©cie (dog, cat, bird, rodent, fish)
    """
    try:
        current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

        logger.info("[racao/alertas] Iniciando busca")

        # Buscar raÃ§Ãµes sem classificaÃ§Ã£o completa
        # Considera "raÃ§Ã£o" se:
        # 1. classificacao_racao != null AND != 'NÃ£o Ã© raÃ§Ã£o'
        # 2. OU categoria.nome LIKE '%raÃ§Ã£o%'

        # Usar joinedload para evitar N+1 queries
        query = (
            db.query(Produto)
            .options(joinedload(Produto.categoria), joinedload(Produto.marca))
            .filter(Produto.tenant_id == tenant_id, Produto.ativo.is_(True))
        )

        # Filtro: Ã© raÃ§Ã£o E estÃ¡ incompleta
        query = query.filter(_produto_eh_racao_expr())

        # Montar filtros dinamicamente baseado em campos que existem
        filtros_incompletos = []
        filtros_incompletos.append(Produto.especies_indicadas.is_(None))

        # Adicionar filtros apenas para campos que existem no modelo
        if hasattr(Produto, "porte_animal_id"):
            filtros_incompletos.append(Produto.porte_animal_id.is_(None))
            logger.info("[racao/alertas] Campo 'porte_animal_id' encontrado no modelo")
        else:
            logger.warning(
                "[racao/alertas] Campo 'porte_animal_id' NÃƒO existe no modelo"
            )

        if hasattr(Produto, "fase_publico_id"):
            filtros_incompletos.append(Produto.fase_publico_id.is_(None))
            logger.info("[racao/alertas] Campo 'fase_publico_id' encontrado no modelo")
        else:
            logger.warning(
                "[racao/alertas] Campo 'fase_publico_id' NÃƒO existe no modelo"
            )

        filtros_incompletos.append(Produto.sabor_proteina.is_(None))
        filtros_incompletos.append(Produto.peso_embalagem.is_(None))

        # Aplicar filtro OR (pelo menos um campo faltando)
        query = query.filter(or_(*filtros_incompletos))

        # Filtrar por espÃ©cie se especificado
        if especie:
            query = query.filter(Produto.especies_indicadas == especie)

        total = query.count()
        logger.info(f"[racao/alertas] Total de produtos encontrados: {total}")

        produtos = query.limit(limite).offset(offset).all()
        logger.info(
            f"[racao/alertas] Produtos retornados nesta pÃ¡gina: {len(produtos)}"
        )

        resultado = []
        for produto in produtos:
            try:
                campos_faltantes = []

                if not produto.especies_indicadas:
                    campos_faltantes.append("especies_indicadas")

                # Verificar campos FK apenas se existirem no modelo
                if hasattr(produto, "porte_animal_id"):
                    if not produto.porte_animal_id:
                        campos_faltantes.append("porte_animal")

                if hasattr(produto, "fase_publico_id"):
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
                if hasattr(produto, "auto_classificar_nome"):
                    auto_classificar = produto.auto_classificar_nome or False

                resultado.append(
                    {
                        "id": produto.id,
                        "codigo": produto.codigo,
                        "nome": produto.nome,
                        "classificacao_racao": produto.classificacao_racao,
                        "especies_indicadas": produto.especies_indicadas,
                        "categoria": categoria_nome,
                        "marca": marca_nome,
                        "campos_faltantes": campos_faltantes,
                        "completude": round((5 - len(campos_faltantes)) / 5 * 100, 1),
                        "auto_classificar_ativo": auto_classificar,
                    }
                )
            except Exception as e:
                logger.error(
                    f"[racao/alertas] Erro ao processar produto {produto.id}: {str(e)}"
                )
                logger.error(f"[racao/alertas] Stack trace: {traceback.format_exc()}")
                continue

        logger.info(
            f"[racao/alertas] Busca concluÃ­da com sucesso. Total de itens no resultado: {len(resultado)}"
        )

        return {
            "total": total,
            "limite": limite,
            "offset": offset,
            "especie_filtro": especie,
            "items": resultado,
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
                "endpoint": "/api/produtos/racao/alertas",
            },
        )
