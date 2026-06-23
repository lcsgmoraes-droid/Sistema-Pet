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
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .security.permissions_decorator import require_permission
from app.partner_utils import get_all_accessible_tenant_ids
from .produtos_models import (
    Categoria,
    Marca,
    Produto,
    ProdutoLote,
    EstoqueMovimentacao,
    ProdutoKitComponente,  # Sprint 4: ComposiÃ§Ã£o de KIT
)
from .produtos.schemas import (
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
)

from .services.produto_service import ProdutoService
from .services.produto_merge_service import (
    executar_fusao_produtos,
    montar_preview_fusao_produtos,
)
from .produtos.search import (
    _build_produto_search_order_clause,
)
from .produtos.codigo_barras import (
    gerar_codigo_barras_ean13,
    validar_codigo_barras_ean13,
)
from .produtos.core import (
    _aplicar_status_ativo_produto,
    _nome_indica_granel,
    _normalizar_filtro_ativo_produtos,
    _normalizar_payload_granel,
    _normalizar_promocao_erp_payload,
    _normalizar_sku_produto,
)
from .produtos.listagem import (
    _aplicar_filtro_fornecedor_produto,
    _aplicar_filtros_basicos_produtos,
    _enriquecer_produto_listagem,
    _expandir_produtos_listagem,
    _load_options_listagem_produtos,
    _mapa_reservas_ativas_multitenant,
    _montar_query_listagem_produtos,
    _montar_query_produtos_vendaveis,
    _normalizar_paginacao_produtos,
    _resolver_fornecedor_ids_filtro_produto,
    _resolver_promocao_erp_produto,
)
from .produtos.lotes import _consumir_lotes_fifo_produto
from .produtos.racao import (
    _normalizar_classificacao_racao,
    _normalizar_payload_racao,
)
from .produtos.catalogos_routes import router as catalogos_router
from .produtos.fornecedores_routes import router as fornecedores_router
from .produtos.historico_precos_routes import router as historico_precos_router
from .produtos.imagens_routes import router as imagens_router
from .produtos.racao_routes import router as racao_router
from .produtos.relatorios_routes import router as relatorios_router
from .produtos.validade import (
    _mapa_validade_proxima_produtos,
)
from .produtos.validators import (
    _obter_produto_ou_404,
    _validar_pode_inativar_produto,
    _validar_sku_unico,
    _validar_tenant_e_obter_usuario,
)
from .produtos.fornecedores import (
    OPERACOES_FORNECEDOR_LOTE,
    _aplicar_fornecedor_produto_lote,
    _validar_fornecedor_produto_lote,
)

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/produtos", tags=["produtos"])
router.include_router(catalogos_router)
router.include_router(fornecedores_router)
router.include_router(historico_precos_router)
router.include_router(imagens_router)
router.include_router(racao_router)
router.include_router(relatorios_router)

PRODUTO_SKU_COLUMN = getattr(Produto, "sku", None)


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
    termo_busca = (busca or "").strip()

    # QUERY BASE - Produtos vendÃ¡veis (incluindo KIT)
    query = _montar_query_produtos_vendaveis(
        db,
        tenant_id=tenant_id,
        termo_busca=termo_busca,
        contar_total=contar_total,
    )

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
    query = _montar_query_listagem_produtos(
        db,
        tenant_ids=access_ids,
        termo_busca=termo_busca,
        ativo=ativo,
        tipo_produto=tipo_produto,
        produto_predecessor_id=produto_predecessor_id,
        include_variations=include_variations,
        busca_completa=busca_completa,
    )

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
    produtos_expandidos = _expandir_produtos_listagem(
        db,
        produtos,
        tenant_id=tenant_id,
        access_ids=access_ids,
        reservas_por_produto=reservas_por_produto,
        incluir_detalhes_composto=incluir_detalhes_composto,
        include_variations=include_variations,
        termo_busca=termo_busca,
        load_options=load_options,
        validade_por_produto=validade_por_produto,
    )
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
