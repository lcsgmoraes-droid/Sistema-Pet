"""Rotas de listagem e busca de produtos."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.partner_utils import get_all_accessible_tenant_ids
from app.produtos.core import _normalizar_filtro_ativo_produtos
from app.produtos.listagem import (
    _aplicar_filtro_fornecedor_produto,
    _aplicar_filtros_basicos_produtos,
    _buscar_pagina_produtos_listagem,
    _enriquecer_produto_listagem,
    _expandir_produtos_listagem,
    _mapa_reservas_ativas_multitenant,
    _montar_query_listagem_produtos,
    _montar_query_produtos_vendaveis,
    _montar_resposta_produtos_paginados,
    _normalizar_paginacao_produtos,
    _resolver_fornecedor_ids_filtro_produto,
)
from app.produtos.schemas import ProdutosPaginadosResponse
from app.produtos.validade import _mapa_validade_proxima_produtos
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.security.permissions_decorator import require_permission

router = APIRouter()
logger = logging.getLogger(__name__)


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

    produtos, total, _load_options = _buscar_pagina_produtos_listagem(
        query,
        termo_busca=termo_busca,
        offset=offset,
        page_size=page_size,
        incluir_imagens=incluir_imagens,
        incluir_lotes=False,
        contar_total=contar_total,
    )

    # OrdenaÃ§Ã£o inteligente: prioriza match exato no cÃ³digo

    # QUERY FINAL

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

    return _montar_resposta_produtos_paginados(
        produtos,
        total=total,
        page=page,
        page_size=page_size,
        offset=offset,
    )


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
    incluir_bling_sync: bool = False,
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
    offset = (page - 1) * page_size
    produtos, total, load_options = _buscar_pagina_produtos_listagem(
        query,
        termo_busca=termo_busca,
        offset=offset,
        page_size=page_size,
        incluir_imagens=incluir_imagens,
        incluir_lotes=incluir_lotes,
        incluir_bling_sync=incluir_bling_sync,
    )

    logger.info("GET /produtos/ - total encontrado: %s", total)

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
        incluir_bling_sync=incluir_bling_sync,
    )
    return _montar_resposta_produtos_paginados(
        produtos_expandidos,
        total=total,
        page=page,
        page_size=page_size,
        offset=offset,
    )
