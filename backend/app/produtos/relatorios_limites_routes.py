"""Consulta de limites do estoque, com filtros e totais antes da paginacao."""

from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.partner_utils import get_all_accessible_tenant_ids
from app.produtos.core import _produto_sku_value
from app.produtos.listagem import _palavras_busca_produto
from app.produtos.search import _produto_search_conditions
from app.produtos.validators import _validar_tenant_e_obter_usuario
from app.produtos_models import Produto, ProdutoFornecedor
from app.security.permissions_decorator import require_permission

router = APIRouter()

SituacaoLimite = Literal[
    "abaixo_minimo",
    "no_minimo",
    "dentro_limites",
    "acima_maximo",
    "sem_limites",
    "limites_invalidos",
]
FiltroSituacao = Literal[
    "todos",
    "abaixo_minimo",
    "no_minimo",
    "dentro_limites",
    "acima_maximo",
    "sem_limites",
    "limites_invalidos",
]


class LimiteEstoqueItem(BaseModel):
    id: int
    nome: str
    codigo: str
    categoria: Optional[str] = None
    marca: Optional[str] = None
    fornecedor: Optional[str] = None
    unidade: str
    estoque_atual: float
    estoque_minimo: Optional[float] = None
    estoque_maximo: Optional[float] = None
    situacao: SituacaoLimite
    falta_minimo: Optional[float] = None
    excesso_maximo: Optional[float] = None


class LimitesEstoqueResponse(BaseModel):
    itens: list[LimiteEstoqueItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    resumo: dict[str, int]


def _expressoes_limites_estoque():
    atual = func.coalesce(Produto.estoque_atual, 0)
    minimo = func.coalesce(Produto.estoque_minimo, 0)
    maximo = func.coalesce(Produto.estoque_maximo, 0)
    invalidos = or_(minimo < 0, maximo < 0, and_(maximo > 0, maximo < minimo))
    situacao = case(
        (invalidos, "limites_invalidos"),
        (and_(minimo > 0, atual < minimo), "abaixo_minimo"),
        (and_(maximo > 0, atual > maximo), "acima_maximo"),
        (and_(minimo > 0, atual == minimo), "no_minimo"),
        (and_(minimo == 0, maximo == 0), "sem_limites"),
        else_="dentro_limites",
    )
    return atual, situacao


def _serializar_limite(produto, situacao):
    atual = float(produto.estoque_atual or 0)
    minimo = float(produto.estoque_minimo or 0)
    maximo = float(produto.estoque_maximo or 0)
    valido = situacao != "limites_invalidos"
    return {
        "id": produto.id,
        "nome": produto.nome,
        "codigo": _produto_sku_value(produto) or produto.codigo or "",
        "categoria": produto.categoria.nome if produto.categoria else None,
        "marca": produto.marca.nome if produto.marca else None,
        "fornecedor": produto.fornecedor.nome if produto.fornecedor else None,
        "unidade": produto.unidade or "UN",
        "estoque_atual": atual,
        "estoque_minimo": minimo if minimo != 0 else None,
        "estoque_maximo": maximo if maximo != 0 else None,
        "situacao": situacao,
        "falta_minimo": round(max(minimo - atual, 0), 6)
        if minimo > 0 and valido
        else None,
        "excesso_maximo": round(max(atual - maximo, 0), 6)
        if maximo > 0 and valido
        else None,
    }


@router.get("/relatorio/limites-estoque", response_model=LimitesEstoqueResponse)
@require_permission("produtos.visualizar")
def relatorio_limites_estoque(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    busca: Optional[str] = None,
    categoria_id: Optional[int] = None,
    marca_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    situacao: FiltroSituacao = "todos",
    saldo: Literal["todos", "zerado", "negativo", "sem_estoque"] = "todos",
    ativo: Literal["ativos", "inativos", "todos"] = "ativos",
    export_all: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    access_ids = [
        UUID(str(value)) for value in get_all_accessible_tenant_ids(db, tenant_id)
    ]
    atual, status = _expressoes_limites_estoque()
    query = db.query(Produto).filter(
        Produto.tenant_id.in_(access_ids),
        func.lower(func.trim(func.coalesce(Produto.tipo, "produto"))) != "servico",
        func.coalesce(Produto.tipo_produto, "SIMPLES").in_(
            ["SIMPLES", "VARIACAO", "KIT"]
        ),
        or_(Produto.tipo_kit.is_(None), Produto.tipo_kit != "VIRTUAL"),
    )
    if ativo != "todos":
        query = query.filter(func.coalesce(Produto.ativo, True) == (ativo == "ativos"))
    for palavra in _palavras_busca_produto(busca):
        query = query.filter(_produto_search_conditions(palavra))
    if categoria_id:
        query = query.filter(Produto.categoria_id == categoria_id)
    if marca_id:
        query = query.filter(Produto.marca_id == marca_id)
    if fornecedor_id:
        query = query.filter(
            or_(
                Produto.fornecedor_id == fornecedor_id,
                Produto.fornecedores_alternativos.any(
                    and_(
                        ProdutoFornecedor.fornecedor_id == fornecedor_id,
                        ProdutoFornecedor.ativo.is_(True),
                    )
                ),
            )
        )
    if saldo == "zerado":
        query = query.filter(atual == 0)
    elif saldo == "negativo":
        query = query.filter(atual < 0)
    elif saldo == "sem_estoque":
        query = query.filter(atual <= 0)

    # Os cards abrangem a selecao inteira, antes do filtro por situacao/pagina.
    contagens = (
        query.with_entities(status, func.count(Produto.id)).group_by(status).all()
    )
    resumo = {chave: int(total) for chave, total in contagens}
    resumo["todos"] = sum(resumo.values())
    total = resumo.get(situacao, 0)
    if situacao != "todos":
        query = query.filter(status == situacao)

    query = (
        query.options(
            joinedload(Produto.categoria),
            joinedload(Produto.marca),
            joinedload(Produto.fornecedor),
        )
        .add_columns(status)
        .order_by(Produto.nome, Produto.id)
    )
    if not export_all:
        query = query.offset((page - 1) * page_size).limit(page_size)
    itens = [
        _serializar_limite(produto, item_status) for produto, item_status in query.all()
    ]
    return {
        "itens": itens,
        "total": total,
        "page": 1 if export_all else page,
        "page_size": total if export_all else page_size,
        "total_pages": (1 if total else 0)
        if export_all
        else (total + page_size - 1) // page_size,
        "resumo": resumo,
    }
