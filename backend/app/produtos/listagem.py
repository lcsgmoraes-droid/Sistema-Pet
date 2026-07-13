from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload, noload

from app.models import Cliente, FornecedorGrupo
from app.partner_utils import is_partner_owned
from app.produtos_models import Produto, ProdutoFornecedor
from app.produtos.search import (
    _build_produto_search_order_clause,
    _produto_search_conditions,
    _produto_search_conditions_fast,
)
from app.produtos.validade import _mapa_validade_proxima_produtos
from app.services.kit_estoque_service import KitEstoqueService


logger = logging.getLogger(__name__)


def _palavras_busca_produto(termo: Optional[str]) -> list[str]:
    if not termo:
        return []
    return [palavra.strip() for palavra in termo.split() if palavra.strip()]


def _tipos_base_listagem(
    include_variations: bool, termo_busca: Optional[str]
) -> list[str]:
    if not include_variations:
        return ["SIMPLES"]
    if (termo_busca or "").strip():
        return ["SIMPLES", "PAI", "KIT", "VARIACAO"]
    return ["SIMPLES", "PAI", "KIT"]


def _normalizar_paginacao_produtos(
    page: int,
    page_size: int,
    *,
    max_page_size: int,
) -> tuple[int, int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), max_page_size)
    offset = (page - 1) * page_size
    return page, page_size, offset


def _montar_query_produtos_vendaveis(
    db: Session,
    *,
    tenant_id: Any,
    termo_busca: Optional[str],
    contar_total: bool,
) -> Any:
    query = db.query(Produto).filter(
        Produto.tenant_id == tenant_id,
        Produto.ativo.is_(True),
        Produto.tipo_produto.in_(["SIMPLES", "VARIACAO", "KIT"]),
    )

    if termo_busca:
        search_conditions = (
            _produto_search_conditions
            if contar_total
            else _produto_search_conditions_fast
        )
        for palavra in _palavras_busca_produto(termo_busca):
            query = query.filter(search_conditions(palavra))

    return query


def _montar_query_listagem_produtos(
    db: Session,
    *,
    tenant_ids: list[Any],
    termo_busca: Optional[str],
    ativo: Optional[bool],
    tipo_produto: Optional[str],
    produto_predecessor_id: Optional[int],
    include_variations: bool,
    busca_completa: bool,
) -> Any:
    if produto_predecessor_id:
        query = db.query(Produto).filter(
            Produto.tenant_id.in_(tenant_ids),
            Produto.produto_predecessor_id == produto_predecessor_id,
        )
    elif tipo_produto:
        query = db.query(Produto).filter(
            Produto.tenant_id.in_(tenant_ids),
            Produto.tipo_produto == tipo_produto,
        )
    else:
        query = db.query(Produto).filter(
            Produto.tenant_id.in_(tenant_ids),
            Produto.tipo_produto.in_(
                _tipos_base_listagem(include_variations, termo_busca)
            ),
        )

    if ativo is not None:
        if ativo:
            query = query.filter(or_(Produto.ativo.is_(True), Produto.ativo.is_(None)))
        else:
            query = query.filter(Produto.ativo.is_(False))

    if termo_busca:
        search_conditions = (
            _produto_search_conditions
            if busca_completa
            else _produto_search_conditions_fast
        )
        for palavra in _palavras_busca_produto(termo_busca):
            query = query.filter(search_conditions(palavra))

    return query


def _load_options_listagem_produtos(
    *,
    incluir_imagens: bool,
    incluir_lotes: bool,
    incluir_bling_sync: bool = False,
) -> list[Any]:
    return [
        joinedload(Produto.categoria),
        joinedload(Produto.marca),
        joinedload(Produto.imagens) if incluir_imagens else noload(Produto.imagens),
        joinedload(Produto.lotes) if incluir_lotes else noload(Produto.lotes),
        joinedload(Produto.bling_sync)
        if incluir_bling_sync
        else noload(Produto.bling_sync),
    ]


def _buscar_pagina_produtos_listagem(
    query: Any,
    *,
    termo_busca: Optional[str],
    offset: int,
    page_size: int,
    incluir_imagens: bool,
    incluir_lotes: bool,
    incluir_bling_sync: bool = False,
    contar_total: bool = True,
) -> tuple[list[Produto], Optional[int], list[Any]]:
    total = query.count() if contar_total else None
    order_clause = _build_produto_search_order_clause(termo_busca)
    load_options = _load_options_listagem_produtos(
        incluir_imagens=incluir_imagens,
        incluir_lotes=incluir_lotes,
        incluir_bling_sync=incluir_bling_sync,
    )

    produtos = (
        query.options(*load_options)
        .order_by(*order_clause)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return [produto for produto in produtos if produto is not None], total, load_options


def _mapa_total_variacoes_por_pai(
    db: Session, produtos: list[Produto]
) -> dict[int, int]:
    pai_ids = [
        int(produto.id)
        for produto in produtos
        if produto and produto.id and produto.tipo_produto == "PAI"
    ]
    if not pai_ids:
        return {}

    rows = (
        db.query(Produto.produto_pai_id, func.count(Produto.id))
        .filter(
            Produto.produto_pai_id.in_(pai_ids),
            Produto.tipo_produto == "VARIACAO",
            Produto.ativo.is_(True),
        )
        .group_by(Produto.produto_pai_id)
        .all()
    )
    return {int(produto_pai_id): int(total or 0) for produto_pai_id, total in rows}


def _mapa_variacoes_por_pai(
    db: Session,
    produtos: list[Produto],
    load_options: list[Any],
) -> dict[int, list[Produto]]:
    pai_ids = [
        int(produto.id)
        for produto in produtos
        if produto and produto.id and produto.tipo_produto == "PAI"
    ]
    if not pai_ids:
        return {}

    variacoes = (
        db.query(Produto)
        .filter(
            Produto.produto_pai_id.in_(pai_ids),
            Produto.tipo_produto == "VARIACAO",
            Produto.ativo.is_(True),
        )
        .options(*load_options)
        .order_by(Produto.produto_pai_id, Produto.nome)
        .all()
    )
    variacoes_por_pai: dict[int, list[Produto]] = {}
    for variacao in variacoes:
        if not variacao.produto_pai_id:
            continue
        variacoes_por_pai.setdefault(int(variacao.produto_pai_id), []).append(variacao)
    return variacoes_por_pai


def _montar_resposta_produtos_paginados(
    items: list[Any],
    *,
    total: Optional[int],
    page: int,
    page_size: int,
    offset: int,
) -> dict[str, Any]:
    total_resolvido = total if total is not None else offset + len(items)
    pages = (total_resolvido + page_size - 1) // page_size
    return {
        "items": items,
        "total": total_resolvido,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


def _expandir_produtos_listagem(
    db: Session,
    produtos: list[Produto],
    *,
    tenant_id: Any,
    access_ids: list[Any],
    reservas_por_produto: dict[int, float],
    incluir_detalhes_composto: bool,
    include_variations: bool,
    termo_busca: Optional[str],
    load_options: list[Any],
    validade_por_produto: dict[int, dict[str, Any]],
    incluir_bling_sync: bool = False,
) -> list[Produto]:
    produtos_expandidos = []
    total_variacoes_por_pai = _mapa_total_variacoes_por_pai(db, produtos)
    variacoes_por_pai = (
        _mapa_variacoes_por_pai(db, produtos, load_options)
        if include_variations and not termo_busca
        else {}
    )
    todas_variacoes = [
        variacao for variacoes in variacoes_por_pai.values() for variacao in variacoes
    ]
    validade_por_variacao = (
        _mapa_validade_proxima_produtos(db, todas_variacoes, access_ids)
        if todas_variacoes
        else {}
    )

    for produto in produtos:
        if produto.tipo_produto == "PAI":
            produto.total_variacoes = total_variacoes_por_pai.get(int(produto.id), 0)

        _enriquecer_produto_listagem(
            db,
            produto,
            tenant_id,
            reservas_por_produto,
            incluir_detalhes_composto=incluir_detalhes_composto,
            validade_por_produto=validade_por_produto,
            incluir_bling_sync=incluir_bling_sync,
        )
        produtos_expandidos.append(produto)

        if include_variations and not termo_busca and produto.tipo_produto == "PAI":
            variacoes = variacoes_por_pai.get(int(produto.id), [])

            for variacao in variacoes:
                _enriquecer_produto_listagem(
                    db,
                    variacao,
                    tenant_id,
                    reservas_por_produto,
                    incluir_detalhes_composto=incluir_detalhes_composto,
                    validade_por_produto=validade_por_variacao,
                    incluir_bling_sync=incluir_bling_sync,
                )
                produtos_expandidos.append(variacao)

    return produtos_expandidos


def _resolver_fornecedor_ids_filtro_produto(
    db: Session,
    *,
    tenant_id: str,
    fornecedor_id: Optional[int],
    fornecedor_grupo_id: Optional[int],
    tenant_ids_fornecedores: Optional[List[str]] = None,
) -> tuple[list[int], bool]:
    if fornecedor_grupo_id:
        grupo = (
            db.query(FornecedorGrupo)
            .filter(
                FornecedorGrupo.id == fornecedor_grupo_id,
                FornecedorGrupo.tenant_id == tenant_id,
                FornecedorGrupo.ativo.is_(True),
            )
            .first()
        )
        if not grupo:
            raise HTTPException(
                status_code=404, detail="Grupo de fornecedor nao encontrado"
            )

        tenant_refs = [
            str(tenant_ref)
            for tenant_ref in (tenant_ids_fornecedores or [tenant_id])
            if tenant_ref is not None
        ] or [tenant_id]

        fornecedor_ids = [
            fornecedor_id_grupo
            for (fornecedor_id_grupo,) in db.query(Cliente.id)
            .filter(
                Cliente.tenant_id.in_(tenant_refs),
                Cliente.tipo_cadastro == "fornecedor",
                Cliente.fornecedor_grupo_id == grupo.id,
                Cliente.ativo.is_(True),
            )
            .all()
        ]
        return fornecedor_ids, True

    if fornecedor_id:
        return [fornecedor_id], False

    return [], False


def _aplicar_filtro_fornecedor_produto(
    query: Any,
    *,
    fornecedor_ids: list[int],
    filtro_por_grupo: bool,
) -> Any:
    if filtro_por_grupo and not fornecedor_ids:
        return query.filter(Produto.id == -1)

    if not fornecedor_ids:
        return query

    return query.filter(
        or_(
            Produto.fornecedor_id.in_(fornecedor_ids),
            Produto.fornecedores_alternativos.any(
                and_(
                    ProdutoFornecedor.fornecedor_id.in_(fornecedor_ids),
                    ProdutoFornecedor.ativo.is_(True),
                )
            ),
        )
    )


def _aplicar_filtros_basicos_produtos(
    query: Any,
    *,
    categoria_id: Optional[int],
    marca_id: Optional[int],
    departamento_id: Optional[int],
    estoque_baixo: Optional[bool],
    em_promocao: Optional[bool],
    referencia: Optional[datetime] = None,
) -> Any:
    if categoria_id:
        query = query.filter(Produto.categoria_id == categoria_id)

    if marca_id:
        query = query.filter(Produto.marca_id == marca_id)

    if departamento_id:
        query = query.filter(Produto.departamento_id == departamento_id)

    if estoque_baixo:
        query = query.filter(Produto.estoque_atual <= Produto.estoque_minimo)

    if em_promocao:
        agora = referencia or datetime.now()
        query = query.filter(
            Produto.preco_promocional.isnot(None),
            or_(Produto.promocao_inicio.is_(None), Produto.promocao_inicio <= agora),
            or_(Produto.promocao_fim.is_(None), Produto.promocao_fim >= agora),
        )

    return query


def _as_float_optional(valor: Any) -> Optional[float]:
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _datetime_naive(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None) if valor.tzinfo else valor
    return None


def _janela_promocao_ativa(
    inicio: Any,
    fim: Any,
    referencia: Optional[datetime] = None,
) -> bool:
    agora = _datetime_naive(referencia) or datetime.now()
    inicio_dt = _datetime_naive(inicio)
    fim_dt = _datetime_naive(fim)

    if inicio_dt and agora < inicio_dt:
        return False
    if fim_dt and agora > fim_dt:
        return False
    return True


def _resolver_promocao_erp_produto(
    produto: Produto,
    referencia: Optional[datetime] = None,
) -> dict[str, Any]:
    preco_regular = _as_float_optional(getattr(produto, "preco_venda", None)) or 0.0
    preco_promocional = _as_float_optional(getattr(produto, "preco_promocional", None))

    promocao_ativa = (
        preco_promocional is not None
        and preco_promocional > 0
        and (preco_regular <= 0 or preco_promocional < preco_regular)
        and _janela_promocao_ativa(
            getattr(produto, "promocao_inicio", None),
            getattr(produto, "promocao_fim", None),
            referencia,
        )
    )

    preco_pdv = preco_promocional if promocao_ativa else preco_regular
    desconto = (
        max(preco_regular - (preco_promocional or preco_regular), 0.0)
        if promocao_ativa
        else 0.0
    )

    return {
        "promocao_ativa": bool(promocao_ativa),
        "preco_pdv": round(float(preco_pdv or 0), 2),
        "preco_regular": round(float(preco_regular or 0), 2),
        "preco_promocional": round(float(preco_promocional), 2)
        if preco_promocional is not None
        else None,
        "desconto": round(float(desconto or 0), 2),
    }


def _enriquecer_preco_pdv(
    produto: Produto, referencia: Optional[datetime] = None
) -> Produto:
    promocao = _resolver_promocao_erp_produto(produto, referencia)
    produto.preco_venda_original = promocao["preco_regular"]
    produto.preco_venda_pdv = promocao["preco_pdv"]
    produto.preco_venda_efetivo = promocao["preco_pdv"]
    produto.promocao_pdv_ativa = promocao["promocao_ativa"]
    produto.promocao_origem_pdv = "Promocao ERP" if promocao["promocao_ativa"] else None
    produto.desconto_promocional_pdv = promocao["desconto"]
    return produto


def _mapa_reservas_ativas_multitenant(
    db: Session, tenant_ids: List[str]
) -> dict[int, float]:
    """Consolida reservas ativas por produto para os tenants acessiveis."""
    try:
        from app.estoque_reserva_service import EstoqueReservaService

        reservas_consolidadas: dict[int, float] = {}
        for tenant_ref in {str(tenant) for tenant in tenant_ids if tenant is not None}:
            reservas_tenant = EstoqueReservaService.mapa_reservas_ativas_por_produto(
                db,
                tenant_ref,
            )
            for produto_id, quantidade in (reservas_tenant or {}).items():
                reservas_consolidadas[int(produto_id)] = float(
                    reservas_consolidadas.get(int(produto_id), 0.0) or 0.0
                ) + float(quantidade or 0.0)
        return reservas_consolidadas
    except Exception as exc:
        logger.warning("Nao foi possivel consolidar reservas ativas: %s", exc)
        db.rollback()
        return {}


def _enriquecer_produto_listagem(
    db: Session,
    produto: Produto,
    tenant_id,
    reservas_por_produto: dict[int, float] | None = None,
    incluir_detalhes_composto: bool = True,
    validade_por_produto: dict[int, dict[str, Any]] | None = None,
    incluir_bling_sync: bool = False,
):
    """Padroniza dados de listagem para produtos simples, kits e variacoes-kit."""
    reservas_por_produto = reservas_por_produto or {}
    validade_por_produto = validade_por_produto or {}
    tenant_produto = getattr(produto, "tenant_id", tenant_id)
    reservas_mesmo_tenant = str(tenant_produto) == str(tenant_id)
    estoque_reservado = (
        float(reservas_por_produto.get(produto.id, 0.0) or 0.0)
        if reservas_mesmo_tenant
        else 0.0
    )

    if produto.categoria:
        produto.categoria_nome = produto.categoria.nome

    produto_composto = produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit

    if produto_composto and incluir_detalhes_composto:
        try:
            from app.services.kit_custo_service import KitCustoService

            composicao = KitEstoqueService.obter_detalhes_composicao(
                db,
                produto.id,
                tenant_id=tenant_produto,
                reservas_por_produto=reservas_por_produto
                if reservas_mesmo_tenant
                else None,
            )
            produto.composicao_kit = [
                {
                    "id": comp["id"],
                    "produto_id": comp["produto_id"],
                    "produto_nome": comp["produto_nome"],
                    "produto_sku": comp["produto_sku"],
                    "produto_tipo": comp["produto_tipo"],
                    "quantidade": comp["quantidade"],
                    "estoque_componente": comp["estoque_componente"],
                    "estoque_reservado": comp.get("estoque_reservado", 0),
                    "estoque_disponivel": comp.get("estoque_disponivel", 0),
                    "kits_possiveis": comp["kits_possiveis"],
                    "ordem": comp["ordem"],
                    "opcional": comp["opcional"],
                }
                for comp in composicao
            ]
            produto.preco_custo = float(
                KitCustoService.calcular_custo_kit(produto.id, db)
            )

            if produto.tipo_kit == "VIRTUAL":
                produto.estoque_virtual = int(
                    KitEstoqueService.calcular_estoque_virtual_kit(
                        db,
                        produto.id,
                        tenant_id=tenant_produto,
                        reservas_por_produto=reservas_por_produto
                        if reservas_mesmo_tenant
                        else None,
                    )
                )
            else:
                produto.estoque_virtual = int(produto.estoque_atual or 0)
        except Exception as e:
            logger.warning(f"Erro ao processar produto composto {produto.id}: {e}")
            produto.composicao_kit = []
            produto.estoque_virtual = int(produto.estoque_atual or 0)
    elif produto_composto and produto.tipo_kit == "VIRTUAL":
        produto.composicao_kit = []
        try:
            produto.estoque_virtual = int(
                KitEstoqueService.calcular_estoque_virtual_kit(
                    db,
                    produto.id,
                    tenant_id=tenant_produto,
                    reservas_por_produto=reservas_por_produto
                    if reservas_mesmo_tenant
                    else None,
                )
            )
        except Exception as e:
            logger.warning(
                f"Erro ao calcular estoque virtual do produto composto {produto.id}: {e}"
            )
            produto.estoque_virtual = int(produto.estoque_atual or 0)
    elif produto_composto:
        produto.composicao_kit = []
        produto.estoque_virtual = int(produto.estoque_atual or 0)
    else:
        produto.composicao_kit = []
        produto.estoque_virtual = int(produto.estoque_atual or 0)

    validade_info = validade_por_produto.get(produto.id, {})
    produto.validade_proxima_listagem = validade_info.get("validade_proxima_listagem")
    produto.lote_validade_proxima = validade_info.get("lote_validade_proxima")
    produto.lotes_validade_resumo = validade_info.get("lotes_validade_resumo", [])
    produto.estoque_reservado = estoque_reservado
    if produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit == "VIRTUAL":
        produto.estoque_disponivel = float(produto.estoque_virtual or 0)
    else:
        produto.estoque_disponivel = max(
            float(produto.estoque_atual or 0) - produto.estoque_reservado,
            0.0,
        )
    produto.de_parceiro = is_partner_owned(tenant_id, produto.tenant_id)
    if incluir_bling_sync:
        sync = getattr(produto, "bling_sync", None)
        produto.bling_produto_id = (
            getattr(sync, "bling_produto_id", None) if sync else None
        )
        produto.bling_sync_status = getattr(sync, "status", None) if sync else None
        produto.bling_sincronizar = (
            bool(getattr(sync, "sincronizar", False)) if sync else False
        )
        produto.bling_ultima_sincronizacao = (
            getattr(sync, "ultima_sincronizacao", None) if sync else None
        )
        produto.bling_ultimo_erro = (
            getattr(sync, "erro_mensagem", None) if sync else None
        )
    _enriquecer_preco_pdv(produto)
    return produto


def _nome_area_produto(produto: Produto) -> str:
    if getattr(produto, "departamento", None):
        return produto.departamento.nome
    if getattr(produto, "categoria", None) and getattr(
        produto.categoria, "departamento", None
    ):
        return produto.categoria.departamento.nome
    return "Sem setor"


def _departamento_id_produto(produto: Produto) -> Optional[int]:
    if getattr(produto, "departamento_id", None):
        return produto.departamento_id
    if getattr(produto, "categoria", None):
        return getattr(produto.categoria, "departamento_id", None)
    return None


def _fornecedor_nome_produto(produto: Produto) -> Optional[str]:
    fornecedor = produto.fornecedor
    if not fornecedor and getattr(produto, "fornecedores_alternativos", None):
        vinculo_principal = next(
            (
                vinculo
                for vinculo in produto.fornecedores_alternativos
                if vinculo.ativo and vinculo.e_principal and vinculo.fornecedor
            ),
            None,
        )
        vinculo_secundario = next(
            (
                vinculo
                for vinculo in produto.fornecedores_alternativos
                if vinculo.ativo and vinculo.fornecedor
            ),
            None,
        )
        fornecedor = (
            vinculo_principal.fornecedor
            if vinculo_principal
            else vinculo_secundario.fornecedor
            if vinculo_secundario
            else None
        )
    return fornecedor.nome if fornecedor else None


def _resolver_metricas_valorizacao_produto(
    db: Session,
    produto: Produto,
    reservas_por_produto: dict[int, float] | None = None,
) -> dict:
    reservas_por_produto = reservas_por_produto or {}
    estoque_reservado = float(reservas_por_produto.get(produto.id, 0.0) or 0.0)
    estoque_atual = float(produto.estoque_atual or 0)
    preco_custo = float(produto.preco_custo or 0)

    if produto.tipo_produto in ("KIT", "VARIACAO") and produto.tipo_kit == "VIRTUAL":
        try:
            from app.services.kit_custo_service import KitCustoService

            estoque_atual = float(
                KitEstoqueService.calcular_estoque_virtual_kit(
                    db,
                    produto.id,
                    tenant_id=getattr(produto, "tenant_id", None),
                    reservas_por_produto=reservas_por_produto,
                )
            )
            preco_custo = float(KitCustoService.calcular_custo_kit(produto.id, db))
            estoque_reservado = 0.0
        except Exception as exc:
            logger.warning(
                "Erro ao calcular valorizacao do kit virtual %s: %s",
                produto.id,
                exc,
            )

    estoque_disponivel = max(estoque_atual - estoque_reservado, 0.0)
    preco_venda = float(produto.preco_venda or 0)

    return {
        "estoque_atual": estoque_atual,
        "estoque_reservado": estoque_reservado,
        "estoque_disponivel": estoque_disponivel,
        "preco_custo": preco_custo,
        "preco_venda": preco_venda,
        "valor_custo_total": estoque_atual * preco_custo,
        "valor_venda_total": estoque_atual * preco_venda,
    }
